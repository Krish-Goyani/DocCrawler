from pydantic_settings import BaseSettings
from typing import List, Dict

class Settings(BaseSettings):
    PINECONE_API_KEY: str
    OPENAI_KEY: str
    GEMINI_API_KEY: str
    INDEX_NAME: str
    INDEX_HOST: str
    JINA_API_KEY: str
    MONGO_URI : str
    MONGODB_DB_NAME : str
    ERROR_COLLECTION_NAME : str
    MAX_DEPTH : int
    MAX_LLM_REQUEST_COUNT : int
    SELECTOR_HIERARCHY : List
    PROGRAMMING_LANGUAGES  : Dict
    MAX_CONCURRENT_CLICKS : int
    LLM_USAGE_COLLECTION_NAME :  str

    class Config:
        env_file = "src/.env"


settings = Settings()
