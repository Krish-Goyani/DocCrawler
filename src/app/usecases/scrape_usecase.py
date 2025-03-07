from src.app.services.chunking_service import ChunkingService
from src.app.config.settings import settings
from fastapi import Depends
from src.app.services.crawler_service import CrawlerService
from typing import List
class ScrapeUseCase:
    def __init__(self, crawler_service = Depends(CrawlerService), chunking_service: ChunkingService = Depends(ChunkingService)) -> None:
        self.chunking_service = chunking_service
        self.crawler_service = crawler_service
        
        
    async def crawler_usecase(self, user_id: str, urls : List):
        dir_path = await self.crawler_service.main(urls, user_id)
        chunk_path = await self.chunking_service.start_chunking_service(dir_path)
        return