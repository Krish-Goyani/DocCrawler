import json
import os

from fastapi import Depends

from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.utils.embedding_utils import EmbeddingUtils


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

    async def process_file(
        self,
        source_file: str,
        max_concurrent_tasks: int,
        user_id: str,
    ) -> None:
        """Process a file to generate embeddings and save them."""
        try:
            print(f"Processing file: {source_file}")
            # Load the data
            with open(source_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.total_chunks = len(data)
            self.embedded_count = 0

            # Extract the chunked texts
            chunk_texts = [item["chunked_data"] for item in data]

            # Generate embeddings concurrently using the utility
            embeddings = await self.embedding_utils.process_batch_embeddings(
                texts=chunk_texts,
                user_id=user_id,
                embedding_func=self.embedding_utils.get_embedding,
                max_concurrent=max_concurrent_tasks,
            )

            # Add embeddings and sparse values to data
            for item, embedding in zip(data, embeddings):
                if embedding is not None:
                    item["embedding"] = embedding
                    item["sparse_values"] = (
                        self.embedding_utils.get_sparse_embedding(
                            item["chunked_data"], user_id
                        )
                    )
                    self.embedded_count += 1
                    print(
                        f"Embedded {self.embedded_count}/{self.total_chunks} chunks"
                    )

            # Save the enriched data
            embeddings_dir = os.path.join(settings.USER_DATA, user_id)
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
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to process file {source_file}: {e}",
                )
            )
