import asyncio
import json
import re
import time
import openai
from config.clients import Clients
from src.app.models.domain.log_data import LogData
from src.app.repositories.llm_usage_repository import LLMUsageRepository
from src.app.utils.error_handler import JsonResponseError
from src.app.repositories.error_repository import ErrorRepo
from fastapi import Depends
from src.app.models.schemas.llm_response import ChunkMetadata, ChunkedData, SummaryLinksResponse, SummaryMetadata, SummaryData
from src.app.models.domain.error import Error


class ChunkingUtils:
    def __init__(self, error_repo = Depends(ErrorRepo), llm_usage_repo = Depends(LLMUsageRepository)) -> None:
        self.error_repo = error_repo
        self.llm_usage_repo = llm_usage_repo
        self.chunk_llm_request_count = 0
        self.chunk_total_input_tokens = 0
        self.chunk_total_output_tokens = 0
        self.request_type = "chunking"

    async def extract_hrefs(self, user_id, json_data):
        try:
            hrefs = []
            for entry in json_data:
                href = entry.get("href", "")
                hrefs.append(href)
            return hrefs
        except Exception as e:
            error = Error(
                user_id=user_id,
                error_message=str(e)
            )
            await self.error_repo.insert_error(error)
            return None


    async def fetch_content(self, user_id, json_data, hrefs):
        try:
            content_dict = {}
            for entry in json_data:
                href = entry.get("href", "")
                if href in hrefs:
                    content = entry.get("content", "")
                    content_dict[href] = content
            return content_dict
        except Exception as e:
            error = Error(
                user_id=user_id,
                error_message=str(e)
            )
            await self.error_repo.insert_error(error)
            return None


    async def chunk_with_gpt(self, user_id, text, chunk_semaphore):

        async with chunk_semaphore:
            try:
                start_time = time.time()
                try:
                    client = Clients.get_openai_client()
                    response = await asyncio.wait_for(
                        client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": text}],
                            temperature=0,
                        ),
                        timeout=90,
                    )
                except asyncio.TimeoutError:
                    return None
                end_time = time.time()
            except openai.OpenAIError as e:
                error = Error(
                    user_id=user_id,
                    error_message=str(e)
                )
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
                timestamp = time.time(),
                request_count = self.chunk_llm_request_count,
                input_tokens = input_tokens,
                output_tokens = output_tokens,
                total_input_tokens = self.chunk_total_input_tokens,
                total_output_tokens = self.chunk_total_output_tokens,
                time_taken = end_time - start_time,
                request_type = self.request_type
            )

            await self.llm_usage_repo.save_usage(log_data)

            output_text = response.choices[0].message.content.strip()
            chunks = self.extract_json_list(output_text)

            if chunks:
                try:
                    validated_chunks = [ChunkedData(**chunk) for chunk in chunks]
                    return validated_chunks
                except Exception as e:
                    error = Error(
                        user_id=user_id,
                        error_message=str(e)
                    )
                    await self.error_repo.insert_error(error)
                    return None
            return None


    async def extract_json_list(self, user_id, text):
        match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                error = Error(
                    user_id=user_id,
                    error_message=f"JSONDecodeError: {str(e)}"
                )
                await self.error_repo.insert_error(error)
                return None  
        return None


    async def filter_summary_links(self, user_id, text):
        try:
            start_time = time.time()
            try:
                client = Clients.get_openai_client()
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": text}],
                        temperature=0,
                    ),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                return None
            end_time = time.time()
        except openai.OpenAIError as e:
            error = Error(
                user_id=user_id,
                error_message=str(e)
            )
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
            timestamp = time.time(),
            request_count = self.chunk_llm_request_count,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_input_tokens = self.chunk_total_input_tokens,
            total_output_tokens = self.chunk_total_output_tokens,
            time_taken = end_time - start_time,
            request_type = self.request_type
        )

        await self.llm_usage_repo.save_usage(log_data)

        output_text = response.choices[0].message.content.strip()
        filtered_links = self.extract_json_list(output_text)

        if filtered_links:
            try:
                validated_links = SummaryLinksResponse(urls=filtered_links)
                return validated_links
            except Exception as e:
                error = Error(
                    user_id=user_id,
                    error_message=str(e)
                )
                await self.error_repo.insert_error(error)
                return None
        return None


    async def generate_summary_chunk(self, user_id, text):
        try:
            start_time = time.time()
            try:
                client = Clients.get_openai_client()
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": text}],
                        temperature=0,
                    ),
                    timeout=900,
                )
            except asyncio.TimeoutError:
                return None
            end_time = time.time()
        except openai.OpenAIError as e:
            error = Error(
                user_id=user_id,
                error_message=str(e)
            )
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
            timestamp = time.time(),
            request_count = self.chunk_llm_request_count,
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_input_tokens = self.chunk_total_input_tokens,
            total_output_tokens = self.chunk_total_output_tokens,
            time_taken = end_time - start_time,
            request_type = self.request_type
        )

        await self.llm_usage_repo.save_usage(log_data)
        output_text = response.choices[0].message.content.strip()
        chunks = self.extract_json_list(output_text)

        if chunks:
            try:
                validated_chunks = [SummaryData(**chunk) for chunk in chunks]
                return validated_chunks
            except Exception as e:
                error = Error(
                    user_id=user_id,
                    error_message=str(e)
                )
                await self.error_repo.insert_error(error)
                return None
        return None
