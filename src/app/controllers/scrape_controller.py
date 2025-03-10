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

from src.app.usecases.embed_usecase.embed_usecase import EmbedUsecase

# from src.app.usecases.scrape_usecase import ScrapeUseCase


class ScrapeController:
    def __init__(
        self,
        # scrape_usecase: ScrapeUseCase = Depends(),
        embed_usecase: EmbedUsecase = Depends(),
    ) -> None:
        # self.scrape_usecase = scrape_usecase
        self.embed_usecase = embed_usecase

    # async def scrape(self, user_id: str, urls: List):
    #     return await self.scrape_usecase.crawler_usecase(user_id, urls)

    async def process_embeddings(
        self, user_id: str, max_concurrent_tasks: Optional[int] = 40
    ):
        return await self.embed_usecase.process_embeddings(
            user_id=user_id, max_concurrent_tasks=max_concurrent_tasks
        )
