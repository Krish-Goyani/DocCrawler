import os

from fastapi import Depends

from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.embed_service import EmbedService
from src.app.utils.error_handler import JsonResponseError


class EmbedUsecase:
    def __init__(
        self,
        embed_service: EmbedService = Depends(EmbedService),
        error_repo: ErrorRepo = Depends(ErrorRepo),
    ) -> None:
        self.embed_service = embed_service
        self.error_repo = error_repo

    async def process_user_chunks(
        self, user_id: str, max_concurrent_tasks: int = 40
    ) -> None:
        """
        Process the all_chunks.json file for a user to generate embeddings.

        Args:
            user_id (str): The ID of the user whose data needs to be processed.
            max_concurrent_tasks (int): Maximum number of concurrent tasks for embedding.
        """
        try:
            # Get the path to the all_chunks.json file for this user
            chunk_file = os.path.join(
                settings.USER_DATA, user_id, "all_chunks.json"
            )

            if not os.path.exists(chunk_file):
                raise JsonResponseError(
                    status_code=404,
                    detail=f"No chunked data found for user {user_id}",
                )

            # Use the service to process the file
            await self.embed_service.process_file(
                source_file=chunk_file,
                max_concurrent_tasks=max_concurrent_tasks,
                user_id=user_id,
            )

            print(f"Embedding process completed for user {user_id}")
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to process files for user {user_id}: {e}",
                )
            )
