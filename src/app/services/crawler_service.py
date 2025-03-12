from crawl4ai import AsyncWebCrawler
from fastapi import Depends

from src.app.config.crawler_config import (
    PROGRAMMING_LANGUAGES,
    SELECTOR_HIERARCHY,
    browser_conf,
    crawler_cfg,
)
from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.state.crawler_state import crawler_state
from src.app.usecases.crawler_usecase.helper import CrawlerUtils


class CrawlerService:
    def __init__(
        self, error_repo=Depends(ErrorRepo), crawler_utils=Depends(CrawlerUtils)
    ) -> None:
        self.error_repo = error_repo
        self.max_depth = settings.MAX_DEPTH
        self.user_id = None
        self.SELECTOR_HIERARCHY = SELECTOR_HIERARCHY
        self.PROGRAMMING_LANGUAGES = PROGRAMMING_LANGUAGES
        self.MAX_CONCURRENT_CLICKS = settings.MAX_CONCURRENT_CLICKS
        self.state = crawler_state
        self.crawler_utils = crawler_utils

    async def should_process_url(self, file_name):
        lock = await self.state.get_lock(file_name)
        async with lock:
            return (
                self.state.llm_request_counts.get(file_name, 0)
                < self.state.max_llm_request_count
            )

    async def crawl_page(
        self,
        url: str,
        depth: int,
        file_name,
        home_url,
        sitemap_mode: bool = False,
    ):
        if depth >= self.max_depth:
            return

        print(f"[CRAWL] Processing {url} at depth {depth}")

        try:
            async with AsyncWebCrawler(config=browser_conf) as crawler:
                result = await crawler.arun(url=url, config=crawler_cfg)
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[ERROR] Failed to scrape {url}: {e} \n error while scraping from crawler_service in crawl_page()",
                )
            )
            return

        if not result.success:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[FAILED] Crawling unsuccessful for {url} \n error while crawling (from crawler_service in crawl_page())",
                )
            )
            return

        if file_name not in self.state.results:
            self.state.results[file_name] = []
        self.state.results[file_name].append(
            {
                "href": url,
                "content": result.markdown.fit_markdown,
                "base_url": home_url,
            }
        )

        if sitemap_mode:
            return

        if not await self.should_process_url(file_name):
            return

        if (depth + 1) >= self.max_depth:
            return

        internal_links = list(
            set(
                [
                    self.crawler_utils.remove_fragment(x["href"])
                    for x in result.links.get("internal", [])
                ]
            )
        )
        internal_links = self.crawler_utils.filter_urls_by_domain(
            url, internal_links
        )

        batch_size = 180
        all_filtered_links = []
        for i in range(0, len(internal_links), batch_size):
            batch = internal_links[i : i + batch_size]
            filtered_batch = await self.crawler_utils.filter_links_gpt(
                batch, file_name, self.user_id
            )
            all_filtered_links.extend(filtered_batch)

        filtered_links = list(set(all_filtered_links))

        new_links = []
        for link in filtered_links:
            if link not in self.state.processed_urls:
                self.state.processed_urls.add(link)
                new_links.append((link, depth + 1, file_name, home_url, False))

        for link_info in new_links:
            await self.state.queue.put(link_info)
