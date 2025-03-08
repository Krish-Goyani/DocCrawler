import asyncio
import concurrent.futures
import types
from typing import Any, Callable, Dict, List, Optional, TypeVar

from fastapi import Depends
from fastembed import TextEmbedding
from pinecone_text.sparse import BM25Encoder

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo

T = TypeVar("T")


class EmbeddingUtils:
    def __init__(self, error_repo: ErrorRepo = Depends(ErrorRepo)) -> None:
        self.error_repo = error_repo
        self.model = TextEmbedding("BAAI/bge-base-en-v1.5")
        self.bm25 = BM25Encoder().default()
        self.request_count = 0

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
                    user_id=user_id,  # Use user_id in error logging
                    error_message=f"[ERROR] Failed to generate dense embedding: {e}",
                )
            )
            return None

    def get_sparse_embedding(self, text: str, user_id: str) -> Dict[str, Any]:
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
                    user_id=user_id,  # Use user_id in error logging
                    error_message=f"[ERROR] Failed to generate sparse embedding: {e}",
                )
            )
            return {"indices": [], "values": []}

    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize the embedding vector."""
        # Vector normalization logic

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate similarity between two embeddings."""
        # Similarity calculation (cosine, dot product, etc.)

    @staticmethod
    async def run_with_concurrency(
        text: str,
        user_id: str,
        embedding_func: Callable[[str, str], List[float]],
        semaphore: asyncio.Semaphore,
        pool: concurrent.futures.ThreadPoolExecutor,
    ) -> Optional[List[float]]:
        """Get embeddings for a given text concurrently using semaphore for rate limiting.

        Args:
            text: The text to embed
            user_id: User identifier
            embedding_func: The embedding function to call
            semaphore: Semaphore for rate limiting
            pool: Thread pool for concurrent execution

        Returns:
            The embedding vector or None if embedding failed
        """
        try:
            async with semaphore:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    pool, lambda: embedding_func(text, user_id)
                )
                return result
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    @staticmethod
    async def process_batch_embeddings(
        texts: List[str],
        user_id: str,
        embedding_func: Callable[[str, str], List[float]],
        max_concurrent: int = 40,
    ) -> List[Optional[List[float]]]:
        """Process a batch of texts to generate embeddings concurrently.

        Args:
            texts: List of texts to embed
            user_id: User identifier
            embedding_func: The embedding function to call
            max_concurrent: Maximum number of concurrent embedding operations

        Returns:
            List of embedding vectors
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        with concurrent.futures.ThreadPoolExecutor() as pool:
            for text in texts:
                tasks.append(
                    asyncio.create_task(
                        EmbeddingUtils.run_with_concurrency(
                            text=text,
                            user_id=user_id,
                            embedding_func=embedding_func,
                            semaphore=semaphore,
                            pool=pool,
                        )
                    )
                )

            return await asyncio.gather(*tasks)
