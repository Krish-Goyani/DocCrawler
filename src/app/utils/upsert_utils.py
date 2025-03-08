import itertools
import json
import os
import time
import uuid
from typing import Any, Dict, List

from fastapi import Depends
from pinecone import ServerlessSpec

from src.app.core.error_handler import JsonResponseError
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class PineconeUtils:
    def __init__(self, error_repo: ErrorRepo = Depends(ErrorRepo)):
        self.error_repo = error_repo

    async def load_json_files_for_pinecone(
        self, directory_path: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Loads all JSON files from a directory and formats the data for Pinecone insertion.
        Keeps chunked_data as a separate field in the returned records.

        Args:
            directory_path (str): Path to the directory containing JSON files with embeddings data

        Returns:
            List[Dict[str, Any]]: List of records ready for Pinecone insertion
        """
        pinecone_records = []

        # Get all JSON files in the directory
        json_files = [
            f for f in os.listdir(directory_path) if f.endswith(".json")
        ]

        for file_name in json_files:
            file_path = os.path.join(directory_path, file_name)

            try:
                # Load the JSON file
                with open(file_path, "r", encoding="utf-8") as file:
                    chunks = json.load(file)

                # Process each chunk in the file
                for chunk in chunks:
                    # Extract the embedding vector
                    embedding = chunk.get("embedding")
                    # If embedding is missing or empty, skip this chunk
                    if not embedding or (
                        isinstance(embedding, list) and len(embedding) == 0
                    ):
                        await self.error_repo.insert_error(
                            Error(
                                user_id=user_id,
                                error_message=f"Skipping chunk from {file_name} due to missing or empty embedding.",
                            )
                        )
                        continue

                    # Generate a UUID for each chunk if not present
                    chunk_id = str(uuid.uuid4())

                    # Extract the text content
                    text = chunk.get("chunked_data")

                    # Extract metadata (without modifying it to include text)
                    metadata = chunk.get("metadata", {})
                    metadata["chunked_data"] = text
                    if "version" in metadata:
                        metadata["version"] = str(metadata["version"])

                    if "has_code_snippet" in metadata:
                        metadata["has_code_snippet"] = str(
                            metadata["has_code_snippet"]
                        )
                    # Create a record in the format Pinecone expects
                    # Keep chunked_data as a separate field
                    record = {
                        "id": chunk_id,
                        "values": embedding,
                        "metadata": metadata,
                        "sparse_values": chunk["sparse_values"],
                    }

                    pinecone_records.append(record)

            except Exception as e:
                self.error_repo.insert_error(
                    {"error": f"Error in processing {file_name}: {str(e)}"}
                )
                await self.error_repo.insert_error(
                    Error(
                        user_id=user_id,
                        error_message=f"Error in upserting: {str(e)}",
                    )
                )
                raise JsonResponseError(
                    status_code=500,
                    detail=f"Error in processing {file_name}: {str(e)}",
                )

        return pinecone_records

    async def ensure_index_exists(
        self,
        index_name: str,
        pc,
        user_id: str,
        dimension: int,
        metric: str = "dotproduct",
    ) -> bool:
        """
        Check if index exists, and create it if not.

        Args:
            index_name: Name of the index to check/create
            dimension: Dimension of the vectors
            metric: Distance metric to use (default: cosine)

        Returns:
            bool: True if index exists or was created successfully
        """
        try:
            # Check if index already exists
            existing_indexes = [x["name"] for x in pc.list_indexes()]
            if index_name in existing_indexes:
                return True

            # Create with serverless spec (use your preferred settings)
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1",
                ),
            )

            # Wait for index to be ready
            existing_indexes = [x["name"] for x in pc.list_indexes()]
            while not index_name in existing_indexes:
                time.sleep(1)

            return True

        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"Error creating index: {str(e)}",
                )
            )
            raise JsonResponseError(
                status_code=500, detail=f"Error creating index: {str(e)}"
            )

    def pine_chunks(self, iterable, batch_size=200):
        """Helper function to break an iterable into chunks of batch_size."""
        it = iter(iterable)
        chunk = list(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = list(itertools.islice(it, batch_size))
