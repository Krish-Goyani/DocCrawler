import asyncio

from fastapi import Depends

from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.services.api_service import ApiService


class PineconeService:
    def __init__(self, api_service: ApiService = Depends()):
        self.api_service = api_service
        self.pinecone_api_key = settings.PINECONE_API_KEY
        self.api_version = settings.PINECONE_API_VERSION
        self.create_index_url = settings.PINECONE_CREATE_INDEX_URL
        self.list_index_url = settings.PINECONE_LIST_INDEX_URL
        self.upsert_url = settings.PINECONE_UPSERT_URL
        self.query_url = settings.PINECONE_QUERY_URL

    async def list_pinecone_indexes(self):
        url = self.list_index_url

        headers = {
            "Api-Key": self.pinecone_api_key,
            "X-Pinecone-API-Version": self.api_version,
        }

        try:
            response = await self.api_service.get(url=url, headers=headers)
            indexes = response.get("indexes", [])
            index_dict = {
                index.get("name"): index.get("host")
                for index in indexes
                if index.get("name") and index.get("host")
            }
            return index_dict
        except Exception as e:
            raise JsonResponseError(
                status_code=500,
                detail=f"Error fetching indexes: {str(e)} \n error from pinecone_service in list_pinecone_indexes()",
            )

    async def create_index(
        self, index_name: str, dimension: int, metric: str
    ) -> str:

        index_data = {
            "name": index_name,
            "dimension": dimension,
            "metric": metric,
            "spec": {"serverless": {"cloud": "aws", "region": "us-east-1"}},
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Api-Key": self.pinecone_api_key,
            "X-Pinecone-API-Version": self.api_version,
        }

        try:
            response = await self.api_service.post(
                url=self.create_index_url, headers=headers, data=index_data
            )

        except Exception as e:
            raise JsonResponseError(
                status_code=500,
                detail=f"Error creating index: {str(e)} \n error from pinecone_service in create_index()",
            )

        # Check the index readiness with at most 3 tries
        check_url = f"{self.create_index_url}/{index_name}"
        ready = False
        for attempt in range(1, 4):
            try:
                get_response = await self.api_service.get(
                    url=check_url, headers=headers
                )
                status = get_response.get("status", {})
                if status.get("ready") and status.get("state") == "Ready":
                    ready = True
                    break
            except Exception:
                # Ignore errors during readiness check and retry
                pass
            await asyncio.sleep(5)

        if not ready:
            raise JsonResponseError(
                status_code=500,
                detail="Index creation timed out after 3 tries \n error from pinecone_service in create_index()",
            )

        return response["host"]

    async def upsert_vectors(self, index_host, input, namespace="default"):
        headers = {
            "Api-Key": self.pinecone_api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": self.api_version,
        }

        url = f"https://{index_host}/{self.upsert_url}"

        data = {"vectors": input, "namespace": namespace}
        try:
            response = await self.api_service.post(
                url=url, headers=headers, data=data
            )
            return response

        except Exception as e:
            raise JsonResponseError(
                status_code=500,
                detail=f"Error while upserting vectors: {str(e)} \n error from pinecone_service in upsert_vectors()",
            )

    def _hybrid_scale(self, dense, sparse, alpha: float):

        if alpha < 0 or alpha > 1:
            raise ValueError("Alpha must be between 0 and 1")
        # scale sparse and dense vectors to create hybrid search vecs
        hsparse = {
            "indices": sparse["indices"],
            "values": [v * (1 - alpha) for v in sparse["values"]],
        }
        hdense = [v * alpha for v in dense]
        return hdense, hsparse

    async def pinecone_hybrid_query(
        self,
        index_host,
        namespace,
        top_k,
        alpha: float,
        query_vector_embeds: list,
        query_sparse_embeds: dict,
        include_metadata: bool,
        filter_dict: dict = None,
    ):
        headers = {
            "Api-Key": self.pinecone_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": self.api_version,
        }

        hdense, hsparse = self._hybrid_scale(
            query_vector_embeds, query_sparse_embeds, alpha
        )

        data = {
            "includeValues": False,
            "includeMetadata": include_metadata,
            "vector": hdense,
            "sparseVector": {
                "indices": hsparse.get("indices"),
                "values": hsparse.get("values"),
            },
            "topK": top_k,
            "namespace": namespace,
        }

        if filter_dict:
            data["filter"] = filter_dict
        url = self.query_url.format(index_host=index_host)
        try:
            response = await self.api_service.post(
                url=url, headers=headers, data=data
            )
            return response

        except Exception as e:
            raise JsonResponseError(
                status_code=500,
                detail=f"error while pinecone query {str(e)} \n error from pinecone_service in pinecone_hybrid_query()",
            )
