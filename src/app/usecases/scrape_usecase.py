from fastapi import Depends

from src.app.services.chunking_service import ChunkingService


class ScrapeUseCase:
    def __init__(
        self, chunking_service: ChunkingService = Depends(ChunkingService)
    ) -> None:
        self.chunking_service = chunking_service

    async def crawler_usecase(self, user_id: str, urls: list):

        chunk_path = await self.chunking_service.start_chunking_service(user_id)
        return
