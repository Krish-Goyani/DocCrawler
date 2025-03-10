from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class QueryRequest(BaseModel):
    query: str
    alpha: float = Field(0.5, ge=0, le=1, description="Alpha value must be between 0 and 1")
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 20
    top_n: int = 10
