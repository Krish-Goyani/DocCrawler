from typing import List

from fastapi import Depends

from src.app.usecases.crawler_usecase.crawler_usecase import CrawlerUsecase
from src.app.usecases.scrape_usecase import ScrapeUseCase


class ScrapeController:
    def __init__(
        self,
        scrape_usecase: ScrapeUseCase = Depends(),
        crawler_usecase=Depends(CrawlerUsecase),
    ) -> None:
        self.scrape_usecase = scrape_usecase
        self.crawler_usecase = crawler_usecase

    async def scrape(self, user_id: str, urls: List):
        return await self.crawler_usecase.main(user_id, urls)
