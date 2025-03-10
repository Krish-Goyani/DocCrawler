from fastapi import Depends
from typing import Dict, Any
from src.app.usecases.query_usecase.query_usecase import QueryUsecase

class QueryController:
    def __init__(self, usecase: QueryUsecase = Depends()):
        self.usecase = usecase

    async def handle_query(self, query: str ,filters: Dict[str, Any], alpha: float, top_k: int, top_n: int, user_id: str):
        return await self.usecase.execute(query, filters, alpha, top_k, top_n, user_id)
