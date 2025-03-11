import asyncio
import concurrent.futures
import json
import os
from typing import List

from fastapi import Depends

from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.embed_service import EmbedService


class EmbedUsecase:
    def __init__(
        self,
        embed_service: EmbedService = Depends(EmbedService),
        error_repo: ErrorRepo = Depends(ErrorRepo),
    ) -> None:
        self.embed_service = embed_service
        self.error_repo = error_repo
        self.total_chunks = 0
        self.embedded_count = 0
        self.user_id = None

    async def get_embedding_concurrently(
        self,
        text: str,
        pool: concurrent.futures.ThreadPoolExecutor,
        semaphore: asyncio.Semaphore,
    ) -> List[float]:
        """Get embeddings for a given text concurrently."""
        try:
            async with semaphore:
                loop = asyncio.get_event_loop()
                result = await self.embed_service.get_dense_embedding(
                    text, self.user_id
                )
                return result
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[ERROR] Failed to get embedding for text: {e} \n error while generating embedding from text concurrently (from embed_usecase in get_embedding_concurrently())",
                )
            )
            return None

    async def embed_process_file(
        self,
        source_file: str,
        pool: concurrent.futures.ThreadPoolExecutor,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Process a file to generate embeddings and save them."""
        try:
            print(f"Processing file: {source_file}")
            with open(source_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.total_chunks = len(data)
            self.embedded_count = 0

            tasks = []
            for item in data:
                chunk_text = item["chunked_data"]
                tasks.append(
                    asyncio.create_task(
                        self.get_embedding_concurrently(
                            chunk_text, pool, semaphore
                        )
                    )
                )

            embeddings = await asyncio.gather(*tasks)

            # Track total dense and sparse embeddings
            total_dense_embeddings = 0
            total_sparse_embeddings = 0

            for idx, (item, embedding) in enumerate(zip(data, embeddings)):
                item["embedding"] = embedding
                item["sparse_values"] = (
                    await self.embed_service.get_sparse_embedding(
                        item["chunked_data"], self.user_id
                    )
                )
                self.embedded_count += 1

                # Update counts
                if embedding is not None:
                    total_dense_embeddings += 1

                if item["sparse_values"]:
                    total_sparse_embeddings += 1

            # Print final summary
            print(
                f"\nFinished processing {self.total_chunks} chunks. "
                f"\nTotal dense embeddings: {total_dense_embeddings}, "
                f"\nTotal sparse embeddings: {total_sparse_embeddings}"
            )

            # Save embeddings to user-specific embeddings directory
            embeddings_dir = os.path.join(settings.USER_DATA, self.user_id)
            os.makedirs(embeddings_dir, exist_ok=True)

            output_file = os.path.join(
                embeddings_dir, os.path.basename(source_file)
            )

            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            print(f"Embeddings saved to {output_file}")
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[ERROR] Failed to process file {source_file}: {e} \n error while processing a file to generate embeddings (from embed_usecase in embed_process_file()).",
                )
            )

    async def process_files(
        self, user_id: str, max_concurrent_tasks: int = 40
    ) -> None:
        """
        Process the all_chunks.json file for a user to generate embeddings.

        Args:
            user_id (str): The ID of the user whose data needs to be processed.
            max_concurrent_tasks (int): Maximum number of concurrent tasks for embedding.
        """
        self.user_id = user_id

        try:
            # Get the path to the all_chunks.json file for this user
            chunk_file = os.path.join(
                settings.USER_DATA, user_id, "all_chunks.json"
            )

            if not os.path.exists(chunk_file):
                raise JsonResponseError(
                    status_code=404,
                    detail=f"No chunked data found for user {user_id}",
                )

            # Process the file to generate embeddings
            semaphore = asyncio.Semaphore(max_concurrent_tasks)
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await self.embed_process_file(
                    source_file=chunk_file,
                    pool=pool,
                    semaphore=semaphore,
                )

        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to process files for user {user_id}: {e} \n error while processing the all_chunks.json file for a user to generate embeddings (from embed_usecase in process_files())",
                )
            )

    async def process_embeddings(
        self, user_id: str, max_concurrent_tasks: int = 40
    ) -> str:
        """
        Main entry point for processing a user's chunked data to generate embeddings.

        Args:
            user_id (str): The ID of the user whose data needs to be processed.
            max_concurrent_tasks (int): Maximum number of concurrent tasks for embedding.

        Returns:
            str: The user ID of the processed data.
        """
        try:
            print(f"Starting embedding process for user {user_id}")

            # Process the files to generate embeddings
            await self.process_files(
                user_id=user_id, max_concurrent_tasks=max_concurrent_tasks
            )

            print(f"Embedding process completed for user {user_id}")
            return user_id

        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to process embeddings for user {user_id}: {e} \n error from embed_usecase in (process_embeddings)",
                )
            )
            raise JsonResponseError(
                status_code=500,
                detail=f"Error in processing embeddings: {str(e)} \n error from embed_usecase in (process_embeddings)",
            )
