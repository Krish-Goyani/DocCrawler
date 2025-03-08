from fastapi import Depends

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.embed_service import EmbedService


class EmbedUsecase:
    def __init__(
        self,
        embed_service: EmbedService = Depends(EmbedService),
        error_repo: ErrorRepo = Depends(ErrorRepo),
    ) -> None:
        self.embed_service = embed_service
        self.error_repo = error_repo

    async def process_embeddings(
        self, user_id: str, max_concurrent_tasks: int = 40
    ) -> str:
        """
        Main entry point for processing a user's chunked data to generate embeddings.

        Args:
            user_id (str): The ID of the user whose data needs to be processed.
            max_concurrent_tasks (int): Maximum number of concurrent tasks for embedding.

        Returns:
            str: The user ID of the processed data.
        """
        try:
            print(f"Starting embedding process for user {user_id}")

            # Initialize the embedding service with the user ID
            self.embed_service.user_id = user_id

            # Process the files to generate embeddings
            await self.embed_service.process_files(
                user_id=user_id, max_concurrent_tasks=max_concurrent_tasks
            )

            print(f"Embedding process completed for user {user_id}")
            return user_id

        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to process embeddings for user {user_id}: {e}",
                )
            )
            raise
