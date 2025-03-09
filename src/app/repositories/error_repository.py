from fastapi import Depends

from src.app.config.database import mongodb_database
from src.app.core.error_handler import JsonResponseError
from src.app.models.domain.error import Error


class ErrorRepo:
    def __init__(
        self, collection=Depends(mongodb_database.get_error_collection)
    ) -> None:
        self.collection = collection

    async def insert_error(self, error: Error):
        insert_result = await self.collection.insert_one(error.to_dict())
        if not insert_result.inserted_id:
            raise JsonResponseError(
                status_code=500, detail="Failed to insert complaint"
            )
        return insert_result
