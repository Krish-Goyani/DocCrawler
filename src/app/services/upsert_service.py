import asyncio
import os
import shutil
import time

from fastapi import Depends

# from pinecone.grpc import PineconeGRPC as Pinecone
from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.pinecone_service import PineconeService
from src.app.usecases.upsert_usecase.helper import PineconeUtils


class UpsertService:
    def __init__(
        self,
        error_repo: ErrorRepo = Depends(ErrorRepo),
        pinecone_utils: PineconeUtils = Depends(PineconeUtils),
        pinecone_service: PineconeService = Depends(),
    ):
        self.index_name = settings.INDEX_NAME
        self.error_repo = error_repo
        self.pinecone_utils = pinecone_utils
        self.pinecone_service = pinecone_service
        self.upsert_batch_size = 100

    async def upload_vectors(self, user_id: str, file_path):

        # Load JSON file for Pinecone
        vector_data = await self.pinecone_utils.load_json_files_for_pinecone(
            file_path, user_id
        )

        if not vector_data:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message="No data found to upsert. \n error while uploading vectors (from upsert_service in upload_vectors.)",
                )
            )
            raise JsonResponseError(
                status_code=400,
                detail="No data found to upsert. \n error while uploading vectors (from upsert_service in upload_vectors.)",
            )

        DIMENSION = len(vector_data[0]["values"])

        # Ensure index exists
        available_indexes = await self.pinecone_service.list_pinecone_indexes()
        if self.index_name not in available_indexes.keys():
            index_host = await self.pinecone_service.create_index(
                index_name=settings.INDEX_NAME,
                dimension=DIMENSION,
                metric="dotproduct",
            )
        else:
            index_host = available_indexes[self.index_name]

        try:
            batches = [
                vector_data[i : i + self.upsert_batch_size]
                for i in range(0, len(vector_data), self.upsert_batch_size)
            ]

            upsert_tasks = [
                self.pinecone_service.upsert_vectors(index_host, batch)
                for batch in batches
            ]

            # Gather results from all batches
            batch_results = await asyncio.gather(*upsert_tasks)

            # Combine results
            total_upserted = sum(
                result.get("upsertedCount", 0) for result in batch_results
            )
            time.sleep(15)

        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"Error in upserting: {str(e)} \n error while uploading vectors (from upsert_service in upload_vectors)",
                )
            )
            raise JsonResponseError(
                status_code=500,
                detail=f"Error in upserting: {str(e)} \n error while uploading vectors (from upsert_service in upload_vectors)",
            )

        # Delete the user_id folder
        try:
            shutil.rmtree(os.path.join(settings.USER_DATA, user_id))
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"Failed to delete folder: {user_id}. Error: {str(e)} \n error from upsert_service in upload_vectors)",
                )
            )

        return {
            "mesage": "Upsertion completed successfully!",
            "upsertedCount": total_upserted,
        }
