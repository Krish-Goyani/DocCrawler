import asyncio
import json
import os

import aiofiles
from fastapi import Depends

from src.app.config.settings import settings
from src.app.utils.chuking_utils import ChunkingUtils
from src.app.utils.prompts import (
    chunk_prompt,
    summary_links_prompt,
    summary_prompt,
)


class ChunkingService:

    def __init__(self, chunk_utils=Depends(ChunkingUtils)) -> None:
        self.chunk_llm_request_count = 0
        self.chunk_total_input_tokens = 0
        self.chunk_total_output_tokens = 0
        self.chunk_prompt = chunk_prompt
        self.summary_links_prompt = summary_links_prompt
        self.summary_prompt = summary_prompt
        self.chunk_utils = chunk_utils

    async def process_file(self, user_id, file_path, semaphore):

        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())

        tasks = [
            self.chunk_utils.chunk_with_gpt(
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
                print(f"Task failed with exception: {response}")
            elif response is not None:
                final_chunks.extend(response)

        return final_chunks

    async def process_summary_file(self, user_id, file_path):

        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())

        links = await self.chunk_utils.extract_hrefs(user_id, data)
        if len(links) > 180:
            links = links[:180]
        filtered_links = await self.chunk_utils.filter_summary_links(
            user_id, f"{summary_links_prompt}\n**INPUT:**\n{links}\n**OUTPUT:**"
        )

        content_data = await self.chunk_utils.fetch_content(
            user_id, data, filtered_links
        )
        responses = await self.chunk_utils.generate_summary_chunk(
            user_id,
            f"{self.summary_prompt}\n**INPUT:**\n{content_data}\n**OUTPUT:**",
        )

        return responses

    async def start_chunking_service(self, user_id):

        dir_path = os.path.join(settings.USER_DATA,user_id, "results")

        json_files = [
            os.path.join(dir_path, file)
            for file in os.listdir(dir_path)
            if file.endswith(".json")
        ]
        all_chunks = []
        semaphore = asyncio.Semaphore(settings.CHUNK_SEMAPHORE)

        for file in json_files:
            chunks = await self.process_file(user_id, file, semaphore)
            all_chunks.extend(chunks)
            summary_chunks = await self.process_summary_file(user_id, file)
            all_chunks.extend(summary_chunks)

        chunk_file = os.path.join(dir_path, "all_chunks.json")
        async with aiofiles.open(chunk_file, mode="w") as chunk_f:
            await chunk_f.write(json.dumps(all_chunks, indent=2))
        return user_id
