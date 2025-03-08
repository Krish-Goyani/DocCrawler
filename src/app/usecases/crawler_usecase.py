import asyncio
from typing import List

from fastapi import Depends
from playwright.async_api import async_playwright

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.crawler_service import CrawlerService
from src.app.services.hidden_code_snippets_service import (
    HiddenCodeSnippetsService,
)
from src.app.state.crawler_state import crawler_state
from src.app.utils.crawler_utils import CrawlerUtils


class CrawlerUsecase:
    def __init__(
        self,
        crawler_service=Depends(CrawlerService),
        crawler_utils=Depends(CrawlerUtils),
        error_repo=Depends(ErrorRepo),
        hidden_code_snippets_service=Depends(HiddenCodeSnippetsService),
    ) -> None:
        self.crawler_service = crawler_service
        self.user_id = None
        self.crawler_utils = crawler_utils
        self.state = crawler_state
        self.num_workers = 60
        self.error_repo = error_repo
        self.hidden_code_snippets_service = hidden_code_snippets_service

    async def worker_for_code_snippets(self, browser):
        while not self.state.mini_queue.empty():
            try:
                file_name, url, md_content = await self.state.mini_queue.get()
                hidden_snippets = await self.hidden_code_snippets_service.extract_hidden_snippets(
                    url=url, browser=browser, user_id=self.user_id
                )
                final_md_content = self.crawler_utils.merge_content(
                    md_content, hidden_snippets
                )
                [x for x in self.state.results[file_name] if x["href"] == url][
                    0
                ]["content"] = final_md_content
            except asyncio.QueueEmpty:
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_repo.insert_error(
                    Error(
                        user_id=self.user_id,
                        error_message=f"[WORKER ERROR] In Code snippets Worker : {e}",
                    )
                )
            finally:
                self.state.mini_queue.task_done()

    async def code_snippets_crawler(self, num_workers, browser):
        for file_name, items in self.state.results.items():
            for item in items:
                url = item["href"]
                md_content = item["content"]
                await self.state.mini_queue.put((file_name, url, md_content))

        tasks = [
            asyncio.create_task(self.worker_for_code_snippets(browser))
            for _ in range(num_workers)
        ]

        await self.state.mini_queue.join()

        for task in tasks:
            task.cancel()

        return True

    async def worker_for_full_page(self, worker_id: int):
        while True:
            try:
                (
                    url,
                    depth,
                    file_name,
                    home_url,
                    sitemap_mode,
                ) = await self.state.queue.get()
                await self.crawler_service.crawl_page(
                    url, depth, file_name, home_url, sitemap_mode
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_repo.insert_error(
                    Error(
                        user_id=self.user_id,
                        error_message=f"[WORKER ERROR] Worker {worker_id}: {e}",
                    )
                )
            finally:
                self.state.queue.task_done()

    async def main(self, user_id: str, start_urls: List[str]):
        self.user_id = user_id

        file_name_tasks = [
            self.crawler_utils.get_file_name(url, self.user_id)
            for url in start_urls
        ]
        self.state.file_names = await asyncio.gather(*file_name_tasks)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            for i, url in enumerate(start_urls):
                file_name = self.state.file_names[i]
                self.state.count_locks[file_name] = asyncio.Lock()
                self.state.results[file_name] = []
                self.state.llm_request_counts[file_name] = 0

                sitemap_urls = await self.crawler_utils.fetch_sitemap(
                    url, self.user_id
                )
                if sitemap_urls:
                    for sitemap_url in sitemap_urls:
                        await self.state.queue.put(
                            (sitemap_url, 1, file_name, url, True)
                        )
                    print(f"Using sitemap for base URL: {url} -> {file_name}")
                else:
                    self.state.processed_urls.add(url)
                    await self.state.queue.put((url, 1, file_name, url, False))
                    print(f"Starting with base URL: {url} -> {file_name}")

            tasks = [
                asyncio.create_task(self.worker_for_full_page(i))
                for i in range(self.num_workers)
            ]
            await self.state.queue.join()
            for task in tasks:
                task.cancel()

            await self.code_snippets_crawler(num_workers=20, browser=browser)
            await self.crawler_utils.save_results(
                self.state.results, self.user_id
            )
            await asyncio.gather(*tasks, return_exceptions=True)
            await browser.close()

            print("\n--- CRAWL SUMMARY ---")
            for file_name, count in self.state.llm_request_counts.items():
                print(
                    f"{file_name}: {count}/{self.state.max_llm_request_count} LLM calls, {len(self.state.results.get(file_name, []))} pages crawled"
                )

            return self.user_id
