from typing import List, Literal, Optional

from pydantic import BaseModel, HttpUrl


class FilterPromptResponse(BaseModel):
    urls: List[HttpUrl]


class ChunkMetadata(BaseModel):
    sdk_framework_name: str
    base_url: HttpUrl
    href: HttpUrl
    sdk_framework: Literal["SDK", "Framework"]
    has_code_snippet: bool
    version: Optional[str]
    domains: Optional[List[str]]
    subdomains: Optional[List[str]]


class ChunkedData(BaseModel):
    chunked_data: str
    metadata: ChunkMetadata


class SummaryLinksResponse(BaseModel):
    urls: List[HttpUrl]


class SummaryMetadata(BaseModel):
    base_url: HttpUrl
    href_urls: List[HttpUrl]
    sdk_framework: Literal["SDK", "Framework"]
    supported_languages: Optional[List[str]]
    versions: Optional[List[str]]


class SummaryData(BaseModel):
    chunked_data: str
    metadata: SummaryMetadata
