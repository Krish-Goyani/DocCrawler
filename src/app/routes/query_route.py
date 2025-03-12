import uuid

from fastapi import APIRouter, Depends

from src.app.controllers.query_controller import QueryController
from src.app.core.error_handler import error_handler
from src.app.models.schemas.query_schema import QueryRequest

query_router = APIRouter()


@query_router.post("/query")
@error_handler
async def query(request: QueryRequest, controller: QueryController = Depends()):
        return await controller.handle_query(
            request.query,
            request.filters,
            request.alpha,
            request.top_k,
            request.top_n,
            str(uuid.uuid4()),
        )
