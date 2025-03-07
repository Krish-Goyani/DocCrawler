# Placeholder for database.py
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from src.app.config.settings import settings


class MongoDB:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.mongodb_client = None

    def connect(self):
        try:
            self.mongodb_client = AsyncIOMotorClient(
                self.database_url, maxpoolsize=30, minpoolsize=5
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to connect to MongoDB: {str(e)}",
            )

    def get_mongo_client(self):
        if not self.mongodb_client:
            raise HTTPException(
                status_code=503, detail="MongoDB client is not connected."
            )
        return self.mongodb_client

    def get_error_collection(self):
        try:
            if not self.mongodb_client:
                raise HTTPException(
                    status_code=503, detail="MongoDB client is not connected."
                )
            return self.mongodb_client[settings.MONGODB_DB_NAME][
                settings.ERROR_COLLECTION_NAME
            ]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to access auth collection: {str(e)}",
            )

    def disconnect(self):
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to close MongoDB connection: {str(e)}",
            )


# Instantiate the MongoDB class
mongodb_database = MongoDB(settings.MONGO_URI)
