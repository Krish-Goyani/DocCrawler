import asyncio

from src.app.config.settings import settings


class CrawlerState:
    def __init__(self):
        # Common shared variables
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.llm_request_counts = {}
        self.count_locks = {}
        self.results = {}
        self.processed_urls = set()
        self.queue = asyncio.Queue()
        self.mini_queue = asyncio.Queue()
        self.max_llm_request_count = settings.MAX_LLM_REQUEST_COUNT
        self.file_names = []

    async def get_lock(self, file_name: str) -> asyncio.Lock:
        if file_name not in self.count_locks:
            self.count_locks[file_name] = asyncio.Lock()
        return self.count_locks[file_name]

    async def increment_llm_request(self, file_name: str):
        lock = await self.get_lock(file_name)
        async with lock:
            current = self.llm_request_counts.get(file_name, 0)
            self.llm_request_counts[file_name] = current + 1


crawler_state = CrawlerState()
