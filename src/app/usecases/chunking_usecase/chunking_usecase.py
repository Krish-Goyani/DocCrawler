import asyncio
import json
import os

import aiofiles
from fastapi import Depends

from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.usecases.chunking_usecase.chunking_helper import ChunkingUtils


class ChunkingUseCase:
    def __init__(
        self,
        chunking_utils: ChunkingUtils = Depends(),
        error_repo=Depends(ErrorRepo),
    ):
        self.chunking_utils = chunking_utils
        self.error_repo = error_repo

    async def execute_chunking(self, user_id: str):
        """
        This method is responsible for chunking the data from the results folder
        and saving the chunks in a file called all_chunks.json.
        :param user_id: The user ID.
        :return: The user ID.
        """
        try:
            dir_path = os.path.join(settings.USER_DATA, user_id, "results")
            json_files = [
                os.path.join(dir_path, file)
                for file in os.listdir(dir_path)
                if file.endswith(".json")
            ]

            all_chunks = []
            semaphore = asyncio.Semaphore(settings.CHUNK_SEMAPHORE)

            for file in json_files:
                try:
                    chunks = await self.chunking_utils.process_file(
                        user_id, file, semaphore
                    )
                    if chunks:
                        all_chunks.extend(chunks)
                    all_chunks.extend(chunks)
                    summary_chunks = (
                        await self.chunking_utils.process_summary_file(
                            user_id, file
                        )
                    )
                    if summary_chunks:
                        all_chunks.extend(summary_chunks)
                except Exception as e:
                    await self.error_repo.insert_error(
                        Error(
                            user_id=self.user_id,
                            error_message=f"[ERROR] occured while processing file in chunking  : {e} \n error from chunking_usecase in executing_chunking()",
                        )
                    )

            save_path = os.path.join(settings.USER_DATA, user_id)
            chunk_file = os.path.join(save_path, "all_chunks.json")
            try:
                async with aiofiles.open(chunk_file, mode="w") as chunk_f:
                    await chunk_f.write(json.dumps(all_chunks, indent=2))
            except Exception as e:
                await self.error_repo.insert_error(
                    Error(
                        user_id=self.user_id,
                        error_message=f"[ERROR] occured while saving chunks to file : {e} \n error from chunking_usecase in executing_chunking()",
                    )
                )
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[ERROR] occured while executing chunks : {e} \n error from chunking_usecase in executing_chunking()",
                )
            )
        finally:
            return user_id
