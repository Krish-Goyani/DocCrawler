from typing import List

from fastapi import Depends

from src.app.services.chunking_service import ChunkingService
from src.app.services.crawler_service import CrawlerService
from src.app.services.embed_service import EmbedService



class ScrapeUseCase:
    def __init__(
        self,
        crawler_service=Depends(CrawlerService),
        chunking_service=Depends(ChunkingService),
        embed_service=Depends(EmbedService),
    ) -> None:
        self.chunking_service = chunking_service
        self.crawler_service = crawler_service
        self.embed_service = embed_service

    async def crawler_usecase(self, user_id: str, urls: List):
        user_id = await self.crawler_service.main(urls, user_id)
        user_id = await self.chunking_service.start_chunking_service(
            user_id
        )
        await self.embed_service.main(user_id=user_id, max_concurrent_tasks=40)
        return True
