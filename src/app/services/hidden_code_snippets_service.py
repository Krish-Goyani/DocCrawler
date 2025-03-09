import asyncio

from fastapi import Depends

from src.app.config.crawler_config import (
    PROGRAMMING_LANGUAGES,
    SELECTOR_HIERARCHY,
)
from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class HiddenCodeSnippetsService:
    def __init__(self, error_repo=Depends(ErrorRepo)):
        self.error_repo = error_repo
        self.PROGRAMMING_LANGUAGES = PROGRAMMING_LANGUAGES
        self.SELECTOR_HIERARCHY = SELECTOR_HIERARCHY
        self.used_id = None
        self.MAX_CONCURRENT_CLICKS = settings.MAX_CONCURRENT_CLICKS

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

    async def extract_hidden_snippets(self, url, browser, user_id):
        """Extracts hidden code snippets by clicking on tabs and handling non-interactive content."""
        code_snippets = {}  # Store extracted snippets by language
        seen_code_blocks = set()
        self.user_id = user_id

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
