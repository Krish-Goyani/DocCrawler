import re
import asyncio
import json
import os
import re
import time
from urllib.parse import urlparse
from fastapi import Depends
from typing import List
import asyncio
import json
import os
import re
import time
from urllib.parse import urlparse
from src.app.models.domain.error import Error
import aiofiles
from crawl4ai import AsyncWebCrawler, BrowserConfig
from src.app.utils.error_handler import JsonResponseError
from src.app.repositories.error_repository import ErrorRepo
from playwright.async_api import async_playwright
import asyncio
import time
from src.app.config.settings import settings
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import aiofiles
from src.app.models.domain.log_data import LogData
from src.app.repositories.llm_usage_repository import LLMUsageRepository
from src.app.models.schemas.llm_response import FilterPromptResponse

class CrawlerUtils:
    def __init__(self , error_repo = Depends(ErrorRepo), llm_usage_repo = Depends(LLMUsageRepository)) -> None:
        self.error_repo = error_repo   
        self.total_input_tokens = 0
        self.total_outpt_tokens = 0
        self.log_lock = asyncio.Lock()
        self.llm_usage_repo = llm_usage_repo
    
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
            await self.error_repo.insert_error(Error(user_id= user_id, error_message = f"[ERROR] Failed to get title for {base_url} and the user id is : {e}" ))
            return urlparse(base_url).netloc.replace(".", "_")
            
            
    def remove_fragment(self, url):
        """Removes fragment identifiers (#) from URLs."""
        match = re.match(r"(https?://[^\s#]+)", url)
        return match.group(1) if match else url

    def filter_urls_by_domain(self,base_url, url_list):
        """Filters URLs that belong to the same domain as the base URL."""
        base_domain = urlparse(base_url).netloc
        return [url for url in url_list if urlparse(url).netloc == base_domain]
    
    
    
    async def clean_gpt_output(self, response_text, user_id):
        """Cleans GPT output by removing code block markers and ensuring a valid list format."""
        response_text = (
            re.sub(r"```[a-zA-Z]*", "", response_text).strip("`").strip()
        )
        try:
            response_text =  FilterPromptResponse(urls=eval(response_text))
            url_list: List[str] = [str(url) for url in response_text.urls]
            return url_list
        except Exception as e:
            await self.error_repo.insert_error(Error(user_id= user_id, error_message = f"[ERROR] Failed to clean GPT output for {response_text} and the user id is : {user_id}" ))
            return []
        
    def merge_content(self,markdown_content, hidden_snippets):
        """Merges extracted markdown content with hidden code snippets."""
        # Regular expression to identify code blocks (```language ... ```)
        code_block_pattern = re.compile(r"```(\w+)\n(.*?)```", re.DOTALL)

        merged_content = ""
        last_end = 0
        inserted_languages = set()

        for match in code_block_pattern.finditer(markdown_content):
            language = match.group(1).lower()
            code = match.group(2)

            # Append the markdown content before the current code block
            merged_content += markdown_content[last_end : match.start()]

            # Append the default extracted code
            merged_content += f"```{language}\n{code}\n```\n"

            # Append hidden snippets for other languages after the default language snippet
            if language in hidden_snippets:
                for alt_code in hidden_snippets.pop(language, []):
                    merged_content += f"\n```{language}\n{alt_code}\n```\n"
                inserted_languages.add(language)

            last_end = match.end()

        # Append any remaining content
        merged_content += markdown_content[last_end:]

        # If there are remaining hidden snippets, append them at the end
        if hidden_snippets:
            merged_content += "\n\n# Additional Code Snippets\n"
            for lang, snippets in hidden_snippets.items():
                if lang not in inserted_languages:
                    for snippet in snippets:
                        merged_content += f"\n```{lang}\n{snippet}\n```\n"

        return merged_content
    
    
    
    async def save_results(self, results: dict, user_id: str):
        """
        Saves the given results in separate JSON files inside the specified directory.
        Each key in the results dictionary becomes a JSON filename.
        """
        os.makedirs(os.path.join(settings.USER_DATA, user_id,"results"), exist_ok=True)

        # Create tasks for all file saves to run in parallel
        save_tasks = []
        for filename, data in results.items():
            file_path = os.path.join(os.path.join(settings.USER_DATA, user_id,"results"), f"{filename}.json")

            async def save_file(path, content):
                async with aiofiles.open(path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(content, ensure_ascii=False, indent=2))
                print(f"Saved: {path}")

            save_tasks.append(save_file(file_path, data))

        # Run all save tasks concurrently
        await asyncio.gather(*save_tasks)
        
        
        
    async def log_usage(self,
        start_time, end_time, input_tokens, output_tokens, llm_request_counts
    ):
        """Log token usage asynchronously but with minimal locking"""

        # Update counters atomically
        async with self.log_lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            combined_llm_request_count = sum(llm_request_counts.values())

            # Prepare log data
            log_data = LogData(
                timestamp=time.time(),
                request_count=combined_llm_request_count,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens,
                time_taken=end_time - start_time,
                request_type= "url filtering"
            )
            
            await self.llm_usage_repo.save_usage(log_data)
            