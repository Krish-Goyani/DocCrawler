from openai import AsyncOpenAI
from pinecone.grpc import PineconeGRPC as Pinecone

from src.app.config.settings import settings


class Clients:
    @staticmethod
    def get_openai_client():
        return AsyncOpenAI(api_key=settings.OPENAI_KEY)

    @staticmethod
    def get_pinecone_client():
        return Pinecone(api_key=settings.PINECONE_API_KEY, pool_threads=30)
