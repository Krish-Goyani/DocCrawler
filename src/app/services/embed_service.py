from fastapi import Depends
from typing import List, Dict, Any
import asyncio
import concurrent.futures
import json
import os
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.utils.embedding_utils import EmbeddingUtils
from src.app.config.settings import settings  

class EmbedService:
    def __init__(
        self, 
        error_repo: ErrorRepo = Depends(ErrorRepo),
        embedding_utils: EmbeddingUtils = Depends(EmbeddingUtils)
    ) -> None:
        self.error_repo = error_repo
        self.embedding_utils = embedding_utils
        self.total_chunks = 0  
        self.embedded_count = 0

    async def get_embedding_concurrently(
        self, 
        text: str, 
        pool: concurrent.futures.ThreadPoolExecutor, 
        semaphore: asyncio.Semaphore,
        user_id: str 
    ) -> List[float]:
        """Get embeddings for a given text concurrently."""
        try:
            async with semaphore:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    pool, 
                    self.embedding_utils.get_embedding, 
                    text, 
                    user_id 
                )
                return result
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id, 
                    error_message=f"[ERROR] Failed to get embedding for text: {e}"
                )
            )
            raise  

    async def embed_process_file(
        self, 
        source_file: str, 
        pool: concurrent.futures.ThreadPoolExecutor, 
        semaphore: asyncio.Semaphore,
        user_id: str 
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
                            chunk_text, 
                            pool, 
                            semaphore,
                            user_id 
                        )
                    )
                )

            embeddings = await asyncio.gather(*tasks)

            for item, embedding in zip(data, embeddings):
                item["embedding"] = embedding
                item["sparse_values"] = self.embedding_utils.get_sparse_embedding(
                    item["chunked_data"],
                    user_id 
                )
                self.embedded_count += 1
                print(
                    f"Embedded {self.embedded_count}/{self.total_chunks} chunks in {source_file}"
                )

            # Save embeddings to user-specific embeddings directory
            embeddings_dir = os.path.join(
                settings.USER_DATA, 
                user_id, 
                "embeddings"
            )
            os.makedirs(embeddings_dir, exist_ok=True)
            
            output_file = os.path.join(
                embeddings_dir, 
                os.path.basename(source_file)
            )
            
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            print(f"Embeddings saved to {output_file}")
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id, 
                    error_message=f"[ERROR] Failed to process file {source_file}: {e}"
                )
            )
            raise 

    async def process_files(
        self, 
        user_id: str, 
        max_concurrent_tasks: int = 40
    ) -> None:
        """
        Process the all_chunks.json file for a user to generate embeddings.

        Args:
            user_id (str): The ID of the user whose data needs to be processed.
            max_concurrent_tasks (int): Maximum number of concurrent tasks for embedding.
        """
        try:
            # Get the path to the all_chunks.json file for this user
            chunk_file = os.path.join(
                settings.USER_DATA, 
                user_id, 
                "all_chunks.json"
            )
            
            if not os.path.exists(chunk_file):
                raise FileNotFoundError(f"No chunked data found for user {user_id}")

            # Process the file to generate embeddings
            semaphore = asyncio.Semaphore(max_concurrent_tasks)
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await self.embed_process_file(
                    source_file=chunk_file,
                    pool=pool,
                    semaphore=semaphore,
                    user_id=user_id
                )

            print(f"Embedding process completed for user {user_id}")
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id, 
                    error_message=f"[ERROR] Failed to process files for user {user_id}: {e}"
                )
            )
            raise 