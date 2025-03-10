from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PINECONE_API_KEY: str
    OPENAI_KEY: str
    GEMINI_API_KEY: str
    INDEX_NAME: str
    INDEX_HOST: str
    JINA_API_KEY: str
    MONGO_URI: str
    MONGODB_DB_NAME: str
    ERROR_COLLECTION_NAME: str
    MAX_DEPTH: int
    MAX_LLM_REQUEST_COUNT: int
    MAX_CONCURRENT_CLICKS: int
    LLM_USAGE_COLLECTION_NAME: str
    USER_DATA: str
    CHUNK_SEMAPHORE: int
    OPENAI_URL: str
    OPENAI_MODEL: str
    PINECONE_LIST_INDEX_URL: str
    PINECONE_API_VERSION: str
    PINECONE_CREATE_INDEX_URL: str
    PINECONE_UPSERT_URL: str
    PINECONE_QUERY_URL: str
    JINA_RERANKING_MODEL: str
    JINA_RERANKING_URL: str

    class Config:
        env_file = "src/.env"
        env_file_encoding = "utf-8"


settings = Settings()
