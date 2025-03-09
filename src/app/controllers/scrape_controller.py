from typing import List

from fastapi import Depends

from src.app.usecases.crawler_usecase.crawler_usecase import CrawlerUsecase
from src.app.usecases.scrape_usecase import ScrapeUseCase
from src.app.usecases.upsert_usecase.upsert_usercase import UpsertUseCase


class ScrapeController:
    def __init__(
        self,
        scrape_usecase: ScrapeUseCase = Depends(),
        crawler_usecase=Depends(CrawlerUsecase),
        upsert_usecase: UpsertUseCase = Depends(),
    ) -> None:
        self.scrape_usecase = scrape_usecase
        self.crawler_usecase = crawler_usecase
        self.upsert_usecase = upsert_usecase

    async def scrape(self, user_id: str, urls: List):
        return await self.upsert_usecase.upload_vectors(user_id)
