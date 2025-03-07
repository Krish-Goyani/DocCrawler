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
from src.app.models.domain.log_data import LogData



class ChunkingUtils:
    def __init__(self, error_repo = Depends(ErrorRepo), llm_usage_repo = Depends(LLMUsageRepository)) -> None:
        self.error_repo = error_repo
        self.llm_usage_repo = llm_usage_repo
        self.chunk_llm_request_count = 0
        self.chunk_total_input_tokens = 0
        self.chunk_total_output_tokens = 0
        self.request_type = "chunking"

    def extract_hrefs(self,json_data):
        hrefs = []
        for entry in json_data:
            href = entry.get("href", "")
            hrefs.append(href)
        return hrefs


    def fetch_content(self,json_data, hrefs):
        content_dict = {}
        for entry in json_data:
            href = entry.get("href", "")
            if href in hrefs:
                content = entry.get("content", "")
                content_dict[href] = content
        return content_dict


    async def chunk_with_gpt(self, text, chunk_semaphore):

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
                print(f"OpenAI API Error: {e}")
                return None

            self.chunk_llm_request_count += 1
            usage = getattr(response, "usage", None)
            if not usage:
                return None

            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            self.chunk_total_input_tokens += input_tokens
            self.chunk_total_output_tokens += output_tokens

            {
            "timestamp": self.timestamp,
            "request_count": self.request_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "time_taken": self.time_taken,
            "request_type": self.request_type,
        }   
            # Prepare and write log data.
            log_data = {
                "llm_request_count": chunk_llm_request_count,
                "total_input_tokens": chunk_total_input_tokens,
                "total_output_tokens": chunk_total_output_tokens,
                "start_time": start_time,
                "end_time": end_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "time_taken": end_time - start_time,
            }

            output_text = response.choices[0].message.content.strip()
            chunks = self.extract_json_list(output_text)

            return chunks


    def extract_json_list(self,text):
        # Regex to extract the JSON list from the response text.
        match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))  # Convert string to a Python list
            except json.JSONDecodeError:
                return None  # Handle invalid JSON cases
        return None


    async def filter_summary_links(self,text):
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
            print(f"OpenAI API Error: {e}")
            return None

        self.chunk_llm_request_count += 1
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        self.chunk_total_input_tokens += input_tokens
        self.chunk_total_output_tokens += output_tokens

        # Prepare and write log data.
        # log_data = {
        #     "llm_request_count": chunk_llm_request_count,
        #     "total_input_tokens": chunk_total_input_tokens,
        #     "total_output_tokens": chunk_total_output_tokens,
        #     "start_time": start_time,
        #     "end_time": end_time,
        #     "input_tokens": input_tokens,
        #     "output_tokens": output_tokens,
        #     "time_taken": end_time - start_time,
        # }
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

        return filtered_links


    async def generate_summary_chunk(self,text):
        global chunk_llm_request_count, chunk_total_input_tokens, chunk_total_output_tokens
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
            print(f"OpenAI API Error: {e}")
            return None

        chunk_llm_request_count += 1
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        chunk_total_input_tokens += input_tokens
        chunk_total_output_tokens += output_tokens

        # Prepare and write log data.
        # log_data = {
        #     "llm_request_count": chunk_llm_request_count,
        #     "total_input_tokens": chunk_total_input_tokens,
        #     "total_output_tokens": chunk_total_output_tokens,
        #     "start_time": start_time,
        #     "end_time": end_time,
        #     "input_tokens": input_tokens,
        #     "output_tokens": output_tokens,
        #     "time_taken": end_time - start_time,
        # }

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

        return chunks
