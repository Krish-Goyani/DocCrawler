import asyncio
import json
import os

import aiofiles
from fastapi import Depends

from src.app.config.settings import settings
from src.app.usecases.chunking_usecase.chunking_helper import ChunkingUtils


class ChunkingUseCase:
    def __init__(self, chunking_utils: ChunkingUtils = Depends()):
        self.chunking_utils = chunking_utils

    async def execute_chunking(self, user_id: str):
        """
        This method is responsible for chunking the data from the results folder
        and saving the chunks in a file called all_chunks.json.
        :param user_id: The user ID.
        :return: The user ID.
        """

        # dir_path = os.path.join(settings.USER_DATA, user_id, "results")
        dir_path = os.path.join(settings.USER_DATA, "0998f5f8-637e-4a72-84aa-8797e1fcb63b", "results")
        json_files = [
            os.path.join(dir_path, file)
            for file in os.listdir(dir_path)
            if file.endswith(".json")
        ]

        all_chunks = []
        semaphore = asyncio.Semaphore(settings.CHUNK_SEMAPHORE)

        for file in json_files:
            chunks = await self.chunking_utils.process_file(
                user_id, file, semaphore
            )
            if chunks:
                all_chunks.extend(chunks)
            all_chunks.extend(chunks)
            summary_chunks = await self.chunking_utils.process_summary_file(
                user_id, file
            )
            if summary_chunks:
                all_chunks.extend(summary_chunks)

        save_path = os.path.join(settings.USER_DATA, "0998f5f8-637e-4a72-84aa-8797e1fcb63b")
        # save_path = os.path.join(settings.USER_DATA, user_id)
        chunk_file = os.path.join(save_path, "all_chunks.json")
        async with aiofiles.open(chunk_file, mode="w") as chunk_f:
            await chunk_f.write(json.dumps(all_chunks, indent=2))

        return user_id
