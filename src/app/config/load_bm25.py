import os
import pickle

from fastapi import Depends
from pinecone_text.sparse import BM25Encoder

from src.app.repositories.error_repository import ErrorRepo
from src.app.core.error_handler import JsonResponseError

class BM25Loader:
    def __init__(self, error_repo: ErrorRepo = Depends(ErrorRepo)) -> None:
        self.error_repo = error_repo

    def load_or_create_bm25(self) -> BM25Encoder:
        """
        Loads BM25 model from pickle file if it exists, otherwise creates new one and saves it

        Returns:
            BM25Encoder: The loaded or newly created BM25 model
        """
        cache_dir = "cache"
        cache_file = os.path.join(cache_dir, "bm25_model.pkl")

        try:
            os.makedirs(cache_dir, exist_ok=True)

            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    return pickle.load(f)

            # Create new model if no cache exists
            bm25 = BM25Encoder().default()

            # Save to cache
            with open(cache_file, "wb") as f:
                pickle.dump(bm25, f)

            return bm25
        except Exception as e:
            raise JsonResponseError(status_code=500, detail=f"Error loading/creating BM25 model: {e}")
