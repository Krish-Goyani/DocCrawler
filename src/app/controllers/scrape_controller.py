# from typing import List, Optional

# from fastapi import Depends


# from src.app.usecases.embed_usecase.embed_usecase import EmbedUsecase
# from src.app.usecases.crawler_usecase import CrawlerUsecase
# from src.app.usecases.scrape_usecase import ScrapeUseCase


# class ScrapeController:
#     def __init__(
#         self,
#         scrape_usecase: ScrapeUseCase = Depends(),
#         embed_usecase: EmbedUsecase = Depends(),
#         crawler_usecase=Depends(CrawlerUsecase),
#     ) -> None:
#         self.scrape_usecase = scrape_usecase
#         self.embed_usecase = embed_usecase
#         self.crawler_usecase = crawler_usecase

#     async def scrape(self, user_id: str, urls: List):
#         return await self.scrape_usecase.crawler_usecase(user_id, urls)

#     async def process_embeddings(
#         self, user_id: str, max_concurrent_tasks: Optional[int] = 40
#     ):
#         return await self.embed_usecase.process_embeddings(
#             user_id="123", max_concurrent_tasks=max_concurrent_tasks
#         )

#     async def scrape(self, user_id: str, urls: List):
#         return await self.crawler_usecase.main(user_id, urls)


from typing import Optional

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
        await self.chunking_usecase.execute_chunking(user_id)
        return await self.scrape_usecase.crawler_usecase(user_id, urls)
