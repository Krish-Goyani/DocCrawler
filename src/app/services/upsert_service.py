import os
import shutil

from fastapi import Depends

# from pinecone.grpc import PineconeGRPC as Pinecone
from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.utils.error_handler import JsonResponseError
from src.app.utils.upsert_utils import PineconeUtils

from src.app.config.clients import Clients


class UpsertService:
    def __init__(
        self,
        pinecone_client=Depends(Clients),
        error_repo: ErrorRepo = Depends(ErrorRepo),
        pinecone_utils: PineconeUtils = Depends(PineconeUtils),
    ):
        self.client = pinecone_client.get_pinecone_client()
        self.index_name = settings.INDEX_NAME
        self.error_repo = error_repo
        self.pinecone_utils = pinecone_utils

    async def upload_vectors(self, user_id: str):

        # all_chunks.json path
        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
        embeddings_folder = os.path.join(base_dir, settings.USER_DATA, user_id)

        if not os.path.exists(embeddings_folder):
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"File not found: {embeddings_folder}",
                )
            )
            raise JsonResponseError(
                status_code=404, detail=f"File not found: {embeddings_folder}"
            )

        # Load JSON file for Pinecone
        vector_data = await self.pinecone_utils.load_json_files_for_pinecone(
            embeddings_folder, user_id
        )

        if not vector_data:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message="No data found to upsert.",
                )
            )
            raise JsonResponseError(
                status_code=400, detail="No data found to upsert."
            )

        DIMENSION = len(vector_data[0]["values"])

        # Ensure index exists
        if not await self.pinecone_utils.ensure_index_exists(
            self.index_name, self.client, user_id, DIMENSION
        ):
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message="Failed to create or validate index. Exiting.",
                )
            )
            raise JsonResponseError(
                status_code=500,
                detail="Failed to create or validate index. Exiting.",
            )

        index = self.client.Index(name=self.index_name)
        before_stats = index.describe_index_stats()

        # Perform batched async upserts

        async_results = [
            index.upsert(vectors=batch, async_req=True, namespace="default")
            for batch in self.pinecone_utils.pine_chunks(
                vector_data, batch_size=100
            )
        ]
        # Wait for completion and handle results
        for i, async_result in enumerate(async_results):
            try:
                result = async_result.result()  # Use result() instead of get()
            except Exception as e:
                await self.error_repo.insert_error(
                    Error(
                        user_id=user_id,
                        error_message=f"Error in upserting: {str(e)}",
                    )
                )
                raise JsonResponseError(
                    status_code=500, detail=f"Error in upserting: {str(e)}"
                )

        # Delete the user_id folder
        try:
            shutil.rmtree(embeddings_folder)
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"Failed to delete folder: {embeddings_folder}. Error: {str(e)}",
                )
            )

        return {
            "mesage": "Upsertion completed successfully!",
            "upsertedCount": len(vector_data),
        }
