from typing import List

from fastapi import Depends

from src.app.usecases.chunking_usecase.chunking_usecase import ChunkingUseCase
from src.app.usecases.crawler_usecase.crawler_usecase import CrawlerUsecase
from src.app.usecases.scrape_usecase import ScrapeUseCase
from src.app.usecases.upsert_usecase.upsert_usercase import UpsertUseCase


class ScrapeController:
    def __init__(
        self,
        scrape_usecase: ScrapeUseCase = Depends(),
        chunking_usecase: ChunkingUseCase = Depends(),
        crawler_usecase: CrawlerUsecase = Depends(),
        upsert_usecase: UpsertUseCase = Depends(),
    ) -> None:
        self.scrape_usecase = scrape_usecase
        self.chunking_usecase = chunking_usecase
        self.crawler_usecase = crawler_usecase

    async def scrape(self, user_id: str, urls: List):
        # await self.chunking_usecase.execute_chunking(user_id)
        # return await self.scrape_usecase.crawler_usecase(user_id, urls)
        return await self.crawler_usecase.main(user_id=user_id, start_urls=urls)
        # return await self.chunking_usecase.execute_chunking(user_id)
