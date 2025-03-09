import types
from typing import Dict, List, Optional

from fastapi import Depends
from fastembed import TextEmbedding

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class EmbeddingUtils:
    def __init__(self, error_repo: ErrorRepo = Depends(ErrorRepo)) -> None:
        self.error_repo = error_repo
        self.model = TextEmbedding("BAAI/bge-base-en-v1.5")
        self.bm25 = None
        self.request_count = 0

    def get_sparse_embedding(
        self, text: str, user_id: str  # Add user_id as a parameter
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
                    user_id=user_id,  # Use user_id in error logging
                    error_message=f"[ERROR] Failed to generate sparse embedding: {e}",
                )
            )
            return {"indices": [], "values": []}

    def get_embedding(
        self, text: str, user_id: str  # Add user_id as a parameter
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
