import json
import uuid
from typing import Any, Dict, List

from fastapi import Depends

from src.app.core.error_handler import JsonResponseError
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class PineconeUtils:
    def __init__(self, error_repo: ErrorRepo = Depends(ErrorRepo)):
        self.error_repo = error_repo

    async def load_json_files_for_pinecone(
        self, file_path: str, user_id: str
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
                            error_message=f"Skipping chunk from {file_path} due to missing or empty embedding.",
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
                if "versions" in metadata and metadata["versions"]:
                    value = metadata["versions"]
                    if value in [None, [], "", "none", "null"]:
                        try:
                            del metadata["versions"]
                        except Exception as e:
                            pass
                    else:
                        metadata["versions"] = str(value).lower()
                else:
                    try:
                        del metadata["versions"]
                    except Exception as e:
                        pass

                if "version" in metadata and metadata["version"]:
                    value = metadata["version"]
                    if value in [None, [], "", "none", "null"]:
                        try:
                            del metadata["version"]
                        except Exception as e:
                            pass
                    else:
                        metadata["version"] = str(value).lower()
                else:
                    try:
                        del metadata["version"]
                    except Exception as e:
                        pass

                if "has_code_snippet" in metadata:
                    if metadata["has_code_snippet"]:
                        metadata["has_code_snippet"] = str(
                            metadata["has_code_snippet"]
                        ).lower()
                    else:
                        try:
                            del metadata["has_code_snippet"]
                        except Exception as e:
                            pass

                if (
                    "supported_languages" in metadata
                    and metadata["supported_languages"]
                ):
                    if metadata["supported_languages"] in [None, [], "null"]:
                        try:
                            del metadata["supported_languages"]
                        except Exception as e:
                            pass
                    else:
                        metadata["supported_languages"] = str(
                            metadata["supported_languages"]
                        ).lower()
                else:
                    try:
                        del metadata["supported_languages"]
                    except Exception as e:
                        pass
                try:
                    metadata["SDK_Framework_name"] = str(
                        metadata["SDK_Framework_name"]
                    ).lower()
                    metadata["category"] = str(metadata["category"]).lower()
                    metadata["sdk_framework"] = str(
                        metadata["sdk_framework"]
                    ).lower()
                except Exception as e:
                    pass

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
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"Error in records generation: {str(e)} \n error from upsert_usecase/helper in load_json_files_for_pinecone()",
                )
            )
            raise JsonResponseError(
                status_code=500,
                detail=f"Error in processing {file_path}: {str(e)} \n error from upsert_usecase/helper in load_json_files_for_pinecone()",
            )

        return pinecone_records
