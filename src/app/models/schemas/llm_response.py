from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class FilterPromptResponse(BaseModel):
    urls: List[HttpUrl]


class ChunkMetadata(BaseModel):
    SDK_Framework_name: str
    base_url: HttpUrl
    href: HttpUrl
    sdk_framework: str
    category: str
    has_code_snippet: bool
    version: Optional[str]


class ChunkedData(BaseModel):
    chunked_data: str
    metadata: ChunkMetadata


class SummaryLinksResponse(BaseModel):
    urls: List[HttpUrl]


class SummaryMetadata(BaseModel):
    base_url: HttpUrl
    href_urls: List[HttpUrl]
    sdk_framework: str
    category: str
    supported_languages: Optional[List[str]]
    versions: Optional[List[str]]


class SummaryData(BaseModel):
    chunked_data: str
    metadata: SummaryMetadata
