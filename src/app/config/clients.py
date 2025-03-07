from config.settings import settings
from openai import AsyncOpenAI
from pinecone.grpc import PineconeGRPC as Pinecone


class Clients:
    def get_openai_client(self):
        return AsyncOpenAI(api_key=settings.OPENAI_KEY)

    def get_pinecone_client(self):
        return Pinecone(api_key=settings.PINECONE_API_KEY, pool_threads=30)
