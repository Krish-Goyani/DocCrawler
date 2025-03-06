from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PINECONE_API_KEY: str
    OPENAI_KEY: str
    GEMINI_API_KEY: str
    INDEX_NAME: str
    INDEX_HOST: str
    JINA_API_KEY: str
    CHUNK_SEMAPHORE: int = 30
    ERROR_COLLECTION_NAME: str
    MONGO_URI: str
    MONGODB_DB_NAME: str


    class Config:
        env_file = "src/.env"


settings = Settings()