import asyncio
import time

from crawl4ai import AsyncWebCrawler
from fastapi import Depends
from playwright.async_api import async_playwright

from src.app.config.clients import Clients
from src.app.config.crawler_config import (
    PROGRAMMING_LANGUAGES,
    SELECTOR_HIERARCHY,
    browser_conf,
    crawler_cfg,
)
from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.utils.crawler_utils import CrawlerUtils
from src.app.utils.prompts import filter_prompt


class CrawlerService:
    def __init__(
        self,
        error_repo=Depends(ErrorRepo),
        crawler_utils=Depends(CrawlerUtils),
        openai_client=Depends(Clients),
    ) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.log_lock = asyncio.Lock()
        self.error_repo = error_repo
        self.file_names = []
        self.queue = asyncio.Queue()
        self.results = {}
        self.processed_urls = set()
        self.llm_request_counts = {}
        self.count_locks = {}
        self.max_depth = settings.MAX_DEPTH
        self.user_id = None
        self.max_llm_request_count = settings.MAX_LLM_REQUEST_COUNT
        self.crawler_utils = crawler_utils
        self.openai_client = openai_client.get_openai_client()
        self.mini_queue = asyncio.Queue()
        self.SELECTOR_HIERARCHY = SELECTOR_HIERARCHY
        self.PROGRAMMING_LANGUAGES = PROGRAMMING_LANGUAGES
        self.MAX_CONCURRENT_CLICKS = settings.MAX_CONCURRENT_CLICKS

    async def should_process_url(self, file_name):
        """Check if we should process more URLs for this file_name"""
        async with self.count_locks.get(file_name, asyncio.Lock()):
            return (
                self.llm_request_counts.get(file_name, 0)
                < self.max_llm_request_count
            )

    async def filter_links_gpt(self, links, file_name):
        """Filter links using GPT-4o-mini asynchronously with minimal locking."""

        # If no links to filter, return empty list without making an LLM call
        if not links:
            return []

        # Check if we've already hit the limit - only lock for this short check
        async with self.count_locks.get(file_name, asyncio.Lock()):
            if (
                self.llm_request_counts.get(file_name, 0)
                >= self.max_llm_request_count
            ):
                return []
            # Increment preemptively to avoid race conditions
            self.llm_request_counts[file_name] = (
                self.llm_request_counts.get(file_name, 0) + 1
            )

        input_text = f"{filter_prompt}\n**INPUT:**\n{links}\n**OUTPUT:**"
        start_time = time.time()

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": input_text}],
                temperature=0,
            )

            end_time = time.time()

            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens

            # Log usage asynchronously without blocking
            asyncio.create_task(
                self.crawler_utils.log_usage(
                    start_time,
                    end_time,
                    input_tokens,
                    output_tokens,
                    self.llm_request_counts,
                )
            )

            filtered_links = response.choices[0].message.content.strip()
            return await self.crawler_utils.clean_gpt_output(
                filtered_links, self.user_id
            )

        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[ERROR] LLM call failed: {e}",
                )
            )
            # Release the counter if the call failed
            async with self.count_locks.get(file_name, asyncio.Lock()):
                self.llm_request_counts[file_name] = max(
                    0, self.llm_request_counts.get(file_name, 0) - 1
                )
            return []

    async def crawl_page(
        self,
        url: str,
        depth: int,
        file_name,
        home_url,
        sitemap_mode: bool = False,
    ):
        """
        Scrape a single URL using Crawl4AI, extract internal links (unless in sitemap mode), and process markdown.
        """
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
                    error_message=f"[ERROR] Failed to scrape {url}: {e}",
                )
            )
            return

        if not result.success:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"[FAILED] Crawling unsuccessful for {url}",
                )
            )
            return

        # Store the result
        if file_name not in self.results:
            self.results[file_name] = []
        self.results[file_name].append(
            {
                "href": url,
                "content": result.markdown.fit_markdown,
                "source_url": home_url,
            }
        )

        # When in sitemap mode, do not extract more links.
        if sitemap_mode:
            return

        # Only continue if we haven't reached the LLM limit
        if not await self.should_process_url(file_name):
            return

        if (depth + 1) >= self.max_depth:
            return

        # Extract and filter internal links (only in non-sitemap mode)
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
            filtered_batch = await self.filter_links_gpt(batch, file_name)
            all_filtered_links.extend(filtered_batch)

        filtered_links = list(set(all_filtered_links))

        new_links = []
        for link in filtered_links:
            if link not in self.processed_urls:
                self.processed_urls.add(link)
                new_links.append((link, depth + 1, file_name, home_url, False))

        for link_info in new_links:
            await self.queue.put(link_info)

    async def worker_for_full_page(self, worker_id: int):
        """Worker coroutine that processes URLs from the queue concurrently."""
        while True:
            try:
                url, depth, file_name, home_url, sitemap_mode = (
                    await self.queue.get()
                )
                await self.crawl_page(
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
                self.queue.task_done()

    async def handle_element_and_extract(
        self, page, element, text, seen_code_blocks, should_click=True
    ):
        """
        Handle an element (click if needed) and extract code snippets from the page.

        :param page: The page object.
        :param element: The element to interact with.
        :param text: The text associated with the element (e.g., programming language name).
        :param seen_code_blocks: A set to track already processed code snippets.
        :param should_click: Whether to click the element before extracting code.
        :return: A tuple of (snippets, text).
        """
        snippets = []
        try:
            # Click the element if required
            if should_click:
                print(f"Clicking: {text} in element")
                await element.click()
                await asyncio.sleep(0.5)  # Reduced sleep time

            # Extract code blocks after the action
            code_blocks = await page.locator(
                "pre code, pre, code, div[class*='bg-'] pre code, div[class*='bg-'] pre"
            ).all()
            for code_block in code_blocks:
                try:
                    code_text = await code_block.inner_text(timeout=3000)
                    code_text = code_text.strip()
                    if code_text and code_text not in seen_code_blocks:
                        seen_code_blocks.add(code_text)
                        snippets.append(code_text)
                except Exception as e:
                    continue
            return snippets, text
        except Exception as e:
            await self.error_repo.insert_error(
                Error(
                    user_id=self.user_id,
                    error_message=f"Skipping interactive element due to error: {e}",
                )
            )
            # print(f"Skipping interactive element due to error: {e}")
            return [], text

    async def extract_hidden_snippets(self, url, browser):
        """Extracts hidden code snippets by clicking on tabs and handling non-interactive content."""
        code_snippets = {}  # Store extracted snippets by language
        seen_code_blocks = set()

        context = await browser.new_context(accept_downloads=False)
        page = await context.new_page()
        await page.goto(url=url, timeout=45000)

        # Step 1: Use improved selector hierarchy to find relevant elements
        for selector in self.SELECTOR_HIERARCHY:
            try:
                elements = await page.locator(selector).all()
                if not elements:
                    continue

                # Process elements concurrently
                click_tasks = []
                for element in elements:
                    # Skip if the element is not visible
                    if not await element.is_visible():
                        continue

                    # Handle select elements differently
                    if selector == "select":
                        # Locate the option elements within the select
                        options = await element.locator("option").all()
                        for option in options:
                            option_text = await option.inner_text(timeout=3000)
                            option_text = option_text.strip().lower()
                            if option_text in self.PROGRAMMING_LANGUAGES:
                                # Use select_option instead of clicking
                                value = await option.get_attribute("value")
                                await element.select_option(value=value)
                                # Extract code after selecting the option
                                click_tasks.append(
                                    self.handle_element_and_extract(
                                        page,
                                        element,
                                        option_text,
                                        seen_code_blocks,
                                        should_click=False,
                                    )
                                )
                    else:
                        # For non-select elements, check if the element text is in PROGRAMMING_LANGUAGES
                        element_text = await element.inner_text(timeout=3000)
                        element_text = element_text.strip().lower()
                        if element_text in self.PROGRAMMING_LANGUAGES:
                            # Proceed with the click logic
                            click_tasks.append(
                                self.handle_element_and_extract(
                                    page,
                                    element,
                                    element_text,
                                    seen_code_blocks,
                                    should_click=True,
                                )
                            )

                # Execute click operations concurrently with a limit
                results = []
                for i in range(0, len(click_tasks), self.MAX_CONCURRENT_CLICKS):
                    batch = click_tasks[i : i + self.MAX_CONCURRENT_CLICKS]
                    batch_results = await asyncio.gather(*batch)
                    results.extend(batch_results)

                # Process results
                for snippets, lang in results:
                    if snippets and lang in self.PROGRAMMING_LANGUAGES:
                        code_snippets.setdefault(lang, []).extend(snippets)

            except Exception as e:
                await self.error_repo.insert_error(
                    Error(
                        user_id=self.user_id,
                        error_message=f"Error with selector {selector}: {e}",
                    )
                )
                # print(f"Error with selector {selector}: {e}")

        # Step 2: Extract non-interactive hidden content
        hidden_elements = await page.query_selector_all(
            "[style*='display: none'], [style*='visibility: hidden']"
        )
        for element in hidden_elements:
            try:
                await page.evaluate(
                    "el => el.style.display = 'block'", element
                )  # Force show hidden elements
                # where is this text used?
                #
                #
                #
                #
                text = await element.inner_text()
            except Exception as e:
                await self.error_repo.insert_error(
                    Error(
                        user_id=self.user_id,
                        error_message=f"Skipping hidden element: {e}",
                    )
                )
                # print(f"Skipping hidden element: {e}")

        # Step 3: Dynamically detect programming languages from code blocks
        languages = await page.evaluate(
            """() => {
            return Array.from(document.querySelectorAll('[class*="language-"]')).map(el => {
                const match = el.className.match(/language-(\w+)/);
                return match ? match[1] : null;
            }).filter(Boolean);
        }"""
        )

        if languages:
            for lang in languages:
                if lang not in code_snippets:
                    code_snippets[lang] = []

        await page.close()
        await context.close()
        return code_snippets

    async def worker_for_code_snippets(self, browser):
        """Worker that processes items from the queue and updates the results."""
        while not self.mini_queue.empty():
            try:
                file_name, url, md_content = await self.mini_queue.get()
                # Call the async function to extract hidden snippets
                hidden_snippets = await self.extract_hidden_snippets(
                    url=url, browser=browser
                )
                # Merge the original markdown content with the extracted snippets
                final_md_content = self.crawler_utils.merge_content(
                    md_content, hidden_snippets
                )
                # updated content to the results for that file_name
                [x for x in self.results[file_name] if x["href"] == url][0][
                    "content"
                ] = final_md_content
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
                self.mini_queue.task_done()

    async def code_snippets_crawler(self, num_workers, browser):
        """
        Distributes work among a pool of async workers.

        Parameters:
            num_workers (int): Number of concurrent worker tasks.
            results (dict): Dictionary with keys like "pinecone_doc" or "groq_docs", where
                            each value is a list of dictionaries containing "href" and "content".
            browser: An instance of the playwright browser.
        """

        # Populate the queue with items from the results dictionary
        # Each item is a tuple: (file_name, url, md_content)
        for file_name, items in self.results.items():
            for item in items:
                url = item["href"]
                md_content = item["content"]
                await self.mini_queue.put((file_name, url, md_content))

        # Start a pool of workers
        tasks = [
            asyncio.create_task(self.worker_for_code_snippets(browser))
            for _ in range(num_workers)
        ]

        # Wait until the queue is fully processed
        await self.mini_queue.join()

        # Optionally cancel any lingering tasks (if any)
        for task in tasks:
            task.cancel()

        # Return the updated results if needed
        return True

    async def main(
        self, start_urls: list[str], user_id: str, num_workers: int = 50
    ):
        self.user_id = user_id
        file_name_tasks = [
            self.crawler_utils.get_file_name(url, self.user_id)
            for url in start_urls
        ]
        self.file_names = await asyncio.gather(*file_name_tasks)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            for i, url in enumerate(start_urls):
                file_name = self.file_names[i]
                self.count_locks[file_name] = asyncio.Lock()
                self.results[file_name] = []
                self.llm_request_counts[file_name] = 0

                # Check for sitemap
                sitemap_urls = await self.crawler_utils.fetch_sitemap(
                    url, self.user_id
                )
                if sitemap_urls:
                    for sitemap_url in sitemap_urls:
                        # In sitemap mode, no further link extraction is needed.
                        await self.queue.put(
                            (sitemap_url, 1, file_name, url, True)
                        )
                    print(f"Using sitemap for base URL: {url} -> {file_name}")
                else:
                    self.processed_urls.add(url)
                    await self.queue.put((url, 1, file_name, url, False))
                    print(f"Starting with base URL: {url} -> {file_name}")

            tasks = [
                asyncio.create_task(self.worker_for_full_page(i))
                for i in range(num_workers)
            ]

            await self.queue.join()
            for task in tasks:
                task.cancel()
            await self.code_snippets_crawler(num_workers=20, browser=browser)
            await self.crawler_utils.save_results(self.results, self.user_id)
            await asyncio.gather(*tasks, return_exceptions=True)
            await browser.close()

            print("\n--- CRAWL SUMMARY ---")
            for file_name, count in self.llm_request_counts.items():
                print(
                    f"{file_name}: {count}/{self.max_llm_request_count} LLM calls, {len(self.results.get(file_name, []))} pages crawled"
                )

            return self.user_id
