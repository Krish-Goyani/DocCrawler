from typing import Any, Dict

from fastapi import Depends

from src.app.config.settings import settings
from src.app.services.embed_service import EmbedService
from src.app.services.jina_reranker_service import JinaRerankingService
from src.app.services.pinecone_service import PineconeService


class QueryUsecase:
    def __init__(
        self,
        pinecone_service: PineconeService = Depends(),
        jina_reranker_service: JinaRerankingService = Depends(),
        embedding_service: EmbedService = Depends(),
    ):
        self.pinecone_service = pinecone_service
        self.reranker_service = jina_reranker_service
        self.embedding_service = embedding_service

    async def execute(
        self,
        query: str,
        filters: Dict[str, Any],
        alpha: float = 0.5,
        top_k: int = 20,
        top_n: int = 10,
        user_id: str = None,
    ):

        dense_vec = await self.embedding_service.get_dense_embedding(
            query, user_id
        )
        sparse_vec = await self.embedding_service.get_sparse_embedding(
            query, user_id
        )

        pinecone_indexes = await self.pinecone_service.list_pinecone_indexes()
        index_host = pinecone_indexes.get(settings.INDEX_NAME)

        transformed_filters = {}

        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    transformed_filters[key] = {"$in": [value]}
                elif isinstance(value, list):
                    transformed_filters[key] = {
                        "$in": value
                    }  # Keep lists as they are
                elif isinstance(value, bool):
                    transformed_filters[key] = {
                        "$eq": value
                    }  # Handle booleans correctly
                elif value is None:
                    transformed_filters[key] = {
                        "$exists": False
                    }  # Handle None values
                else:
                    transformed_filters[key] = (
                        value  # Keep other values as they are
                    )

        retrieved_vectors = await self.pinecone_service.pinecone_hybrid_query(
            index_host,
            "default",
            top_k,
            alpha,
            dense_vec,
            sparse_vec,
            True,
            transformed_filters,
        )

        chunked_data = self._extract_chunked_data(
            retrieved_vectors.get("matches")
        )

        reranked_results = await self.reranker_service.rerank_documents(
            chunked_data, query, top_n
        )

        return {"results": reranked_results["results"]}

    def _extract_chunked_data(self, matches):
        chunked_data_list = []

        for match in matches:
            metadata = match.get("metadata", {})
            chunked_data = metadata.get("chunked_data")

            if chunked_data:
                if isinstance(chunked_data, list):
                    chunked_data_list.extend(chunked_data)
                else:
                    chunked_data_list.append(chunked_data)

        return chunked_data_list
