import asyncio
import json
import os
import aiofiles
from config.settings import settings

from utils.chuking_utils import chunk_with_gpt, extract_hrefs, fetch_content, filter_summary_links, generate_summary_chunk
from utils.prompts import chunk_prompt, summary_links_prompt, summary_prompt
from utils.error_handler import JsonResponseError


class ChunkingService:

    def __init__(self):
        self.chunk_llm_request_count = 0
        self.chunk_total_input_tokens = 0
        self.chunk_total_output_tokens = 0
        self.chunk_prompt = chunk_prompt
        self.summary_links_prompt = summary_links_prompt
        self.summary_prompt = summary_prompt

    async def process_file(self, file_path, semaphore):
        

        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())

        tasks = [
            chunk_with_gpt(
                f"{self.chunk_prompt}\n**INPUT:**\n{item}\n**OUTPUT:**",
                semaphore,
            )
            for item in data
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        final_chunks = []
        for response in responses:
            if isinstance(response, Exception):
                print(f"Task failed with exception: {response}")
            elif response is not None:
                final_chunks.extend(response)

        return final_chunks

    async def process_summary_file(self,file_path):

        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())

        links = extract_hrefs(data)
        if len(links) > 180:
            links = links[:180]
        filtered_links = await filter_summary_links(
            f"{summary_links_prompt}\n**INPUT:**\n{links}\n**OUTPUT:**"
        )

        content_data = fetch_content(data, filtered_links)
        responses = await generate_summary_chunk(
            f"{self.summary_prompt}\n**INPUT:**\n{content_data}\n**OUTPUT:**"
        )

        return responses

    async def start_chunking_service(self,dir_path):

        json_files = [
            os.path.join(dir_path, file)
            for file in os.listdir(dir_path)
            if file.endswith(".json")
        ]
        all_chunks = []
        semaphore = asyncio.Semaphore(settings.CHUNK_SEMAPHORE)

        for file in json_files:
            chunks = await self.process_file(file, semaphore)
            all_chunks.extend(chunks)
            summary_chunks = await self.process_summary_file(file)
            all_chunks.extend(summary_chunks)


        chunk_file = os.path.join(dir_path, "all_chunks.json")
        async with aiofiles.open(chunk_file, mode="w") as chunk_f:
            await chunk_f.write(json.dumps(all_chunks, indent=2))
