from typing import List

from fastapi import Depends

from src.app.usecases.chunking_usecase import ChunkingUseCase
from src.app.usecases.scrape_usecase import ScrapeUseCase


class ScrapeController:
    def __init__(
        self,
        scrape_usecase: ScrapeUseCase = Depends(),
        chunking_usecase: ChunkingUseCase = Depends(),
    ) -> None:
        self.scrape_usecase = scrape_usecase
        self.chunking_usecase = chunking_usecase

    async def scrape(self, user_id: str, urls: List):
        await self.chunking_usecase.execute_chunking(user_id)
