import asyncio
import concurrent.futures
import json
import os
import types
from typing import Dict, List, Optional

from fastapi import Depends
from fastembed import TextEmbedding

from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.usecases.embed_usecase.helper import EmbeddingUtils
from src.app.utils.error_handler import JsonResponseError


class EmbedService:
    def __init__(
        self,
        error_repo: ErrorRepo = Depends(ErrorRepo),
        embedding_utils: EmbeddingUtils = Depends(EmbeddingUtils),
    ) -> None:
        self.error_repo = error_repo
        self.embedding_utils = embedding_utils
        self.total_chunks = 0
        self.embedded_count = 0
        self.user_id = None
        # Initialize embedding models
        self.model = TextEmbedding("BAAI/bge-base-en-v1.5")
        # Load BM25 from cache or create new one
        self.bm25 = self.embedding_utils.load_or_create_bm25()
        self.request_count = 0

    def get_sparse_embedding(
        self, text: str, user_id: str
    ) -> Dict[str, List[int]]:
        """
        Generate sparse embeddings using BM25 encoding.

        Args:
            text (str): The input text to encode.
            user_id (str): The ID of the user making the request.

        Returns:
            Dict[str, List[int]]: A dictionary containing the indices and values of the sparse vector.
        """
        try:
            doc_sparse_vector = self.bm25.encode_documents(text)
            return {
                "indices": doc_sparse_vector["indices"],
                "values": doc_sparse_vector["values"],
            }
        except Exception as e:
            # Log the error using ErrorRepo
            self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to generate sparse embedding: {e}",
                )
            )
            return {"indices": [], "values": []}

    def get_embedding(self, text: str, user_id: str) -> Optional[List[float]]:
        """
        Generate dense embeddings using the fastembed model.

        Args:
            text (str): The input text to embed.
            user_id (str): The ID of the user making the request.

        Returns:
            Optional[List[float]]: The embedding vector, or None if an error occurs.
        """
        self.request_count += 1
        print(f"Embedding text. Request count: {self.request_count}")

        try:
            # Get the raw embedding output
            raw = self.model.embed(text, batch_size=24, parallel=True)

            # Convert generator to list if necessary
            if isinstance(raw, types.GeneratorType):
                raw = list(raw)

            # Convert numpy arrays to lists
            if hasattr(raw, "tolist"):
                embeddings = raw.tolist()
            elif isinstance(raw, list):
                embeddings = [
                    e.tolist() if hasattr(e, "tolist") else e for e in raw
                ]
            else:
                embeddings = raw

            print("Received response")
            return embeddings[0]
        except Exception as e:
            self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to generate dense embedding: {e}",
                )
            )
            return None

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
                result = await loop.run_in_executor(
                    pool, self.get_embedding, text, self.user_id
                )
                return result
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[ERROR] Failed to get embedding for text: {e}",
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

            for item, embedding in zip(data, embeddings):
                item["embedding"] = embedding
                item["sparse_values"] = self.get_sparse_embedding(
                    item["chunked_data"], self.user_id
                )
                self.embedded_count += 1
                print(
                    f"Embedded {self.embedded_count}/{self.total_chunks} chunks in {source_file}"
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
                    error_message=f"[ERROR] Failed to process file {source_file}: {e}",
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

            print(f"Embedding process completed for user {user_id}")
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to process files for user {user_id}: {e}",
                )
            )
