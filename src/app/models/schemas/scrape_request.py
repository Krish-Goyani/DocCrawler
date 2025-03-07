from typing import List
from pydantic import BaseModel

class ScrapeRequest(BaseModel):
    urls: List[str]