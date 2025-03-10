import os

from fastapi import Depends

# from pinecone.grpc import PineconeGRPC as Pinecone
from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.upsert_service import UpsertService
from src.app.usecases.upsert_usecase.helper import PineconeUtils


class UpsertUseCase:
    def __init__(
        self,
        error_repo: ErrorRepo = Depends(ErrorRepo),
        pinecone_utils: PineconeUtils = Depends(PineconeUtils),
        upsert_service: UpsertService = Depends(),
    ):
        self.index_name = settings.INDEX_NAME
        self.error_repo = error_repo
        self.pinecone_utils = pinecone_utils
        self.upsert_service = upsert_service

    async def upload_vectors(self, user_id: str):
        file_path = os.path.join(settings.USER_DATA, user_id, "all_chunks.json")

        if not os.path.exists(file_path):
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"File not found: {file_path}",
                )
            )
            raise JsonResponseError(
                status_code=404, detail=f"File not found: {file_path}"
            )
        return await self.upsert_service.upload_vectors(
            user_id=user_id, file_path=file_path
        )
