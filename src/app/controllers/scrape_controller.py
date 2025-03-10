from typing import List

from fastapi import Depends

from src.app.usecases.chunking_usecase.chunking_usecase import ChunkingUseCase
from src.app.usecases.crawler_usecase.crawler_usecase import CrawlerUsecase
from src.app.usecases.embed_usecase.embed_usecase import EmbedUsecase
from src.app.usecases.upsert_usecase.upsert_usercase import UpsertUseCase


class ScrapeController:
    def __init__(
        self,
        chunking_usecase: ChunkingUseCase = Depends(),
        crawler_usecase: CrawlerUsecase = Depends(),
        upsert_usecase: UpsertUseCase = Depends(),
        embed_usecase: EmbedUsecase = Depends(),
    ) -> None:

        self.chunking_usecase = chunking_usecase
        self.crawler_usecase = crawler_usecase
        self.embed_usecase = embed_usecase
        self.upsert_usecase = upsert_usecase

    async def scrape(self, user_id: str, urls: List[str]):

        user_id = await self.crawler_usecase.main(
            user_id=user_id, start_urls=urls
        )
        user_id = await self.chunking_usecase.execute_chunking(user_id)
        user_id = await self.embed_usecase.process_embeddings(user_id)
        return await self.upsert_usecase.upload_vectors(user_id)
