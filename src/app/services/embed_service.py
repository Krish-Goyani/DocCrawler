import asyncio
import types
from typing import Dict, List, Optional

from fastapi import Depends
from fastembed import TextEmbedding

from src.app.config.load_bm25 import BM25Loader
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class EmbedService:
    def __init__(
        self,
        error_repo: ErrorRepo = Depends(ErrorRepo),
        bm25_loaders: BM25Loader = Depends(BM25Loader),
    ) -> None:
        self.error_repo = error_repo
        self.bm25_loaders = bm25_loaders
        self.model = TextEmbedding("BAAI/bge-base-en-v1.5")
        self.bm25 = self.bm25_loaders.load_or_create_bm25()
        self.request_count = 0

    async def get_sparse_embedding(
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
            doc_sparse_vector = await asyncio.to_thread(
                self.bm25.encode_documents, text
            )
            return {
                "indices": doc_sparse_vector["indices"],
                "values": doc_sparse_vector["values"],
            }
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to generate sparse embedding: {e} \n error from embed_service in get_sparse_embedding()",
                )
            )
            return {"indices": [], "values": []}

    async def get_dense_embedding(
        self, text: str, user_id: str
    ) -> Optional[List[float]]:
        """
        Generate dense embeddings using the fastembed model.

        Args:
            text (str): The input text to embed.
            user_id (str): The ID of the user making the request.

        Returns:
            Optional[List[float]]: The embedding vector, or None if an error occurs.
        """
        self.request_count += 1

        try:
            raw = await asyncio.to_thread(
                self.model.embed, text, batch_size=24, parallel=True
            )
            if isinstance(raw, types.GeneratorType):
                raw = list(raw)
            if hasattr(raw, "tolist"):
                embeddings = raw.tolist()
            elif isinstance(raw, list):
                embeddings = [
                    e.tolist() if hasattr(e, "tolist") else e for e in raw
                ]
            else:
                embeddings = raw

            return embeddings[0]
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to generate dense embedding: {e} \n error from embed_service in get_dense_embedding()",
                )
            )
            return
