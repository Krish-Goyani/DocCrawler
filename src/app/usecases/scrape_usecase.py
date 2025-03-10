from typing import List

from fastapi import Depends

from src.app.services.crawler_service import CrawlerService
from src.app.services.embed_service import EmbedService
from src.app.services.upsert_service import UpsertService


class ScrapeUseCase:
    def __init__(
        self,
        crawler_service=Depends(CrawlerService),
        embed_service=Depends(EmbedService),
        upsert_service=Depends(UpsertService),
    ) -> None:
        self.crawler_service = crawler_service
        self.embed_service = embed_service
        self.upsert_service = upsert_service

    async def crawler_usecase(self, user_id: str, urls: List):
        # await self.crawler_service.main(urls, user_id)
        # await self.chunking_service.start_chunking_service(user_id)
        await self.embed_service.process_files(
            user_id="123", max_concurrent_tasks=40
        )
        result = await self.upsert_service.upload_vectors(user_id="123")
        return result
