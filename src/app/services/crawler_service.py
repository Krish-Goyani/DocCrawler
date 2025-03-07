import asyncio
import re
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig
from fastapi import Depends

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class CrawlerService:
    def __init__(self, error_repo=Depends(ErrorRepo)) -> None:
        total_input_tokens = 0
        total_output_tokens = 0
        log_lock = asyncio.Lock()
        self.error_repo = error_repo

    async def get_file_name(self, base_url, user_id):
        try:
            browser_conf = BrowserConfig(
                text_mode=True, light_mode=True, verbose=False
            )
            async with AsyncWebCrawler(config=browser_conf) as crawler:
                result = await crawler.arun(url=base_url)
                title = result.metadata["title"]
                clean_title = re.sub(
                    r"[^\w\s]", "", title
                )  # Remove special characters
                clean_title = re.sub(
                    r"\s+", "_", clean_title
                )  # Replace spaces with underscores
                return clean_title
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=user_id,
                    error_message=f"[ERROR] Failed to get title for {base_url} and the user id is : {e}",
                )
            )
            return urlparse(base_url).netloc.replace(".", "_")
