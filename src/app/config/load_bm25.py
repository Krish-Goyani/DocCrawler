import os
import pickle

from pinecone_text.sparse import BM25Encoder


class BM25Loader:
    CACHE_DIR = "cache"
    CACHE_FILE = os.path.join(CACHE_DIR, "bm25_model.pkl")

    @classmethod
    def load_or_create_bm25(cls):
        """
        Loads BM25 model from pickle file if it exists, otherwise creates a new one and saves it.
        """
        try:
            os.makedirs(cls.CACHE_DIR, exist_ok=True)

            if os.path.exists(cls.CACHE_FILE):
                print("Loading BM25 model from cache...")
                with open(cls.CACHE_FILE, "rb") as f:
                    return pickle.load(f)

            bm25 = BM25Encoder().default()

            with open(cls.CACHE_FILE, "wb") as f:
                pickle.dump(bm25, f)

            return bm25

        except Exception as e:
            print(f"Error loading BM25 model: {e}")
            return BM25Encoder().default()
