from typing import List

from fastapi import Depends

from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.services.api_service import ApiService


class JinaRerankingService:
    def __init__(self, api_service: ApiService = Depends()):
        self.api_service = api_service
        self.model_name = settings.JINA_RERANKING_MODEL
        self.api_key = settings.JINA_API_KEY
        self.url = settings.JINA_RERANKING_URL

    async def rerank_documents(
        self, documents: List[str], query: str, top_n: int
    ):
        data = {
            "model": self.model_name,
            "query": query,
            "top_n": top_n,
            "documents": documents,
        }
        url = self.url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            response = await self.api_service.post(
                url, headers=headers, data=data
            )
            return response

        except Exception as e:
            raise JsonResponseError(
                status_code=500,
                detail=f"error while reranking documents {str(e)} \n error from jina_reranker_service in rerank_documents()",
            )
