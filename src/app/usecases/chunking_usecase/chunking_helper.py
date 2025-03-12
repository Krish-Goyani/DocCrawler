import asyncio
import json
import re
import time

import aiofiles
import openai
from fastapi import Depends

from src.app.models.domain.error import Error
from src.app.models.domain.log_data import LogData
from src.app.models.schemas.llm_response import (
    ChunkedData,
    SummaryData,
    SummaryLinksResponse,
)
from src.app.repositories.error_repository import ErrorRepo
from src.app.repositories.llm_usage_repository import LLMUsageRepository
from src.app.services.openai_service import OpenAIService
from src.app.utils.prompts import (
    chunk_prompt,
    summary_links_prompt,
    summary_prompt,
)
from src.app.utils.batch_api_utils import BatchAPIUtils


class ChunkingUtils:
    def __init__(
        self,
        error_repo: ErrorRepo = Depends(),
        llm_usage_repo: LLMUsageRepository = Depends(),
        openai_service: OpenAIService = Depends(),
        batch_api_utils: BatchAPIUtils = Depends()
    ) -> None:
        self.error_repo = error_repo
        self.llm_usage_repo = llm_usage_repo
        self.chunk_llm_request_count = 0
        self.chunk_total_input_tokens = 0
        self.chunk_total_output_tokens = 0
        self.request_type = "chunking"
        self.openai_service = openai_service
        self.chunk_prompt = chunk_prompt
        self.summary_prompt = summary_prompt
        self.batch_api_utils = batch_api_utils
        
    async def call_batches_api(self, json_files ,user_id):
        
        # 1. Create jsonl file
        processed_files = set()

        for file in json_files:
            jsonl_file = await self.batch_api_utils.create_jsonl_file(
                file, user_id, chunk_prompt
            )
            processed_files.add(jsonl_file)  # Mark file as processed

        processed_files = list(processed_files)
        
        # 2. Upload jsonl file
        upload_tasks = [
            self.openai_service.upload_jsonl_file(jsonl_file, purpose="batch")
            for jsonl_file in processed_files
        ]
        file_ids = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
        # 3. Create batch requests asynchronously
        tasks = [
            self.openai_service.create_batch_request(file_id)
            for file_id in file_ids
        ]
        batch_request_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. Check status of batch + retrieve file content
        content = await self._check_batch_status(batch_request_ids,user_id)
        
        return content
        
    async def _check_batch_status(self, batch_request_ids, user_id):
        responses = []
        pending_batches = set(batch_request_ids)
        
        for _ in range(24):  # 24 iterations (24 hours)
            print("Checking status...")
            for batch_id in list(pending_batches):
                result = await self.openai_service.get_batch_status(batch_id)
                print(result["status"])
                if result["status"] == "completed":
                    print(f"Batch {batch_id} completed! Downloading results...")
                    content = await self.openai_service.retrieve_file_content(result["output_file_id"])
                    
                    parsed_data = []

                    # Ensure content is a string
                    if isinstance(content, str):
                        for line in content.strip().split("\n"): 
                            if line.strip():
                                parsed_data.append(json.loads(line))
                    else:
                        parsed_data = [content] if isinstance(content, dict) else content  # Use directly if already parsed
                    
                    extracted_responses = []

                    # Extract choices from parsed data
                    for entry in parsed_data:  
                        if isinstance(entry, dict) and "response" in entry:
                            response = entry["response"]
                            if "body" in response:
                                body = response["body"]
                                choices = body.get("choices", [])  
                                if choices:
                                    content_text = choices[0]["message"]["content"]
                                    
                                    # Call extract_json_list to format JSON response if applicable
                                    formatted_response = await self.extract_json_list(user_id, content_text)
                                    
                                    if formatted_response:
                                        extracted_responses.append(formatted_response)  # Store formatted JSON
                                        
                                usage = body["usage"]
                                if not usage:
                                    return
                                self.chunk_llm_request_count += 1
                                input_tokens = usage["prompt_tokens"]
                                output_tokens = usage["completion_tokens"]
                                self.chunk_total_input_tokens += input_tokens
                                self.chunk_total_output_tokens += output_tokens

                                log_data = LogData(
                                    timestamp=time.time(),
                                    request_count=self.chunk_llm_request_count,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_input_tokens=self.chunk_total_input_tokens,
                                    total_output_tokens=self.chunk_total_output_tokens,
                                    time_taken=time.time(),
                                    request_type=self.request_type,
                                )

                                await self.llm_usage_repo.save_usage(log_data)

                    responses.extend(extracted_responses)
                    pending_batches.remove(batch_id) 

                elif result["status"] == "failed":
                    print(f"Batch {batch_id} failed")
                    pending_batches.remove(batch_id)

            await asyncio.sleep(3600)  # Sleep for 1 hour

        return responses
        
    async def process_file(self, user_id: str, file_path, semaphore):
        """
        Process the file and chunk the data.

        :param user_id: str: User ID
        :param file_path: str: File path
        :param semaphore: Semaphore
        :return: list: List of chunks
        """

        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())
        tasks = [
            self._chunk_with_gpt(
                user_id,
                f"{self.chunk_prompt}\n**INPUT:**\n{item}\n**OUTPUT:**",
                semaphore,
            )
            for item in data
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        final_chunks = []
        for response in responses:
            if isinstance(response, Exception):
                await self.error_repo.insert_error(
                    Error(user_id=user_id, error_message=str(response))
                )
            elif response is not None:
                final_chunks.extend(response)
        return final_chunks

    async def _chunk_with_gpt(self, user_id, text, chunk_semaphore):
        """
        This method is responsible for chunking the data using GPT-4o-mini.
        :param user_id: The user ID.
        :param text: The text to be chunked.
        :param chunk_semaphore: The semaphore to limit the number of concurrent requests.
        :return: The chunks.
        """
        async with chunk_semaphore:
            try:
                start_time = time.time()
                try:
                    response = await self.openai_service.completions(
                        prompt=text, temperature=0
                    )
                except asyncio.TimeoutError:
                    return None
                except Exception as e:
                    error = Error(user_id=user_id, error_message=str(e))
                    await self.error_repo.insert_error(error)
                    return None
                end_time = time.time()
            except openai.OpenAIError as e:
                error = Error(user_id=user_id, error_message=str(e))
                await self.error_repo.insert_error(error)
                return None
            self.chunk_llm_request_count += 1
            usage = response.get("usage", None)
            if not usage:
                return None
            input_tokens = usage["prompt_tokens"]
            output_tokens = usage["completion_tokens"]
            self.chunk_total_input_tokens += input_tokens
            self.chunk_total_output_tokens += output_tokens

            log_data = LogData(
                timestamp=time.time(),
                request_count=self.chunk_llm_request_count,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_input_tokens=self.chunk_total_input_tokens,
                total_output_tokens=self.chunk_total_output_tokens,
                time_taken=end_time - start_time,
                request_type=self.request_type,
            )

            await self.llm_usage_repo.save_usage(log_data)

            output_text = response["choices"][0]["message"]["content"].strip()
            chunks = await self.extract_json_list(user_id, output_text)

            if chunks:
                try:
                    for chunk in chunks:
                        ChunkedData(**chunk)
                    return chunks
                except Exception as e:
                    error = Error(user_id=user_id, error_message=str(e))
                    await self.error_repo.insert_error(error)
                    return None
            return None

    async def process_summary_file(self, user_id, file_path):
        """
        This method is responsible for summarizing the data from the results folder.
        :param user_id: The user ID.
        :param file_path: The file path.
        :return: The summary chunks.
        """
        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())
        links = await self._extract_hrefs(user_id, data)
        if len(links) > 180:
            links = links[:180]
        filtered_links = await self._filter_summary_links(
            user_id, f"{summary_links_prompt}\n**INPUT:**\n{links}\n**OUTPUT:**"
        )
        content_data = await self._fetch_content(user_id, data, filtered_links)
        responses = await self._generate_summary_chunk(
            user_id,
            f"{self.summary_prompt}\n**INPUT:**\n{content_data}\n**OUTPUT:**",
        )

        return responses

    async def _extract_hrefs(self, user_id, json_data):
        """
        This method is responsible for extracting the hrefs from the JSON data.
        :param user_id: The user ID.
        :param json_data: The JSON data.
        :return: The hrefs.
        """
        try:
            hrefs = []
            for entry in json_data:
                href = entry.get("href", "")
                hrefs.append(href)
            return hrefs
        except Exception as e:
            error = Error(user_id=user_id, error_message=str(e))
            await self.error_repo.insert_error(error)
            return None

    async def _fetch_content(self, user_id, json_data, hrefs):
        try:
            content_dict = {}
            for entry in json_data:
                href = entry.get("href", "")
                if href in hrefs:
                    content = entry.get("content", "")
                    content_dict[href] = content
            return content_dict
        except Exception as e:
            error = Error(user_id=user_id, error_message=str(e))
            await self.error_repo.insert_error(error)
            return None

    async def _filter_summary_links(self, user_id, text):
        """
        This method is responsible for filtering the summary links.
        :param user_id: The user ID.
        :param text: The text.
        :return: The filtered links.
        """
        try:
            start_time = time.time()
            try:
                response = await self.openai_service.completions(
                    prompt=text, temperature=0
                )
            except asyncio.TimeoutError:
                return None
            end_time = time.time()
        except openai.OpenAIError as e:
            error = Error(user_id=user_id, error_message=str(e))
            await self.error_repo.insert_error(error)
            return None

        self.chunk_llm_request_count += 1
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        self.chunk_total_input_tokens += input_tokens
        self.chunk_total_output_tokens += output_tokens

        log_data = LogData(
            timestamp=time.time(),
            request_count=self.chunk_llm_request_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_input_tokens=self.chunk_total_input_tokens,
            total_output_tokens=self.chunk_total_output_tokens,
            time_taken=end_time - start_time,
            request_type=self.request_type,
        )

        await self.llm_usage_repo.save_usage(log_data)

        output_text = response.choices[0].message.content.strip()
        filtered_links = await self.extract_json_list(user_id, output_text)

        if filtered_links:
            try:
                SummaryLinksResponse(urls=filtered_links)
                return filtered_links
            except Exception as e:
                error = Error(user_id=user_id, error_message=str(e))
                await self.error_repo.insert_error(error)
                return None
        return None

    async def _generate_summary_chunk(self, user_id, text):
        """
        This method is responsible for generating the summary chunk.
        :param user_id: The user ID.
        :param text: The text.
        :return: The summary chunk.
        """
        try:
            start_time = time.time()
            try:
                response = await self.openai_service.completions(
                    prompt=text, temperature=0
                )
            except asyncio.TimeoutError:
                return None
            end_time = time.time()
        except openai.OpenAIError as e:
            error = Error(user_id=user_id, error_message=str(e))
            await self.error_repo.insert_error(error)
            return None

        self.chunk_llm_request_count += 1
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        self.chunk_total_input_tokens += input_tokens
        self.chunk_total_output_tokens += output_tokens

        log_data = LogData(
            timestamp=time.time(),
            request_count=self.chunk_llm_request_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_input_tokens=self.chunk_total_input_tokens,
            total_output_tokens=self.chunk_total_output_tokens,
            time_taken=end_time - start_time,
            request_type=self.request_type,
        )

        await self.llm_usage_repo.save_usage(log_data)
        output_text = response.choices[0].message.content.strip()
        chunks = await self.extract_json_list(user_id, output_text)
        if chunks:
            try:
                for chunk in chunks:
                    SummaryData(**chunk)
                return chunks
            except Exception as e:
                error = Error(user_id=user_id, error_message=str(e))
                await self.error_repo.insert_error(error)
                return None
        return None

    async def extract_json_list(self, user_id, text):
        """
        This method is responsible for extracting the JSON list from the text.
        :param user_id: The user ID.
        :param text: The text.
        :return: The JSON list.
        """
        match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                error = Error(
                    user_id=user_id, error_message=f"JSONDecodeError: {str(e)}"
                )
                await self.error_repo.insert_error(error)
                return None
        return None
