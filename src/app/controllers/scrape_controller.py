from typing import List

from fastapi import Depends

from src.app.usecases.scrape_usecase import ScrapeUseCase


class ScrapeController:
    def __init__(self, scrape_usecase=Depends(ScrapeUseCase)) -> None:
        self.scrape_usecase = scrape_usecase

    async def scrape(self, user_id: str, urls: List):
        return await self.scrape_usecase.crawler_usecase(user_id, urls)
