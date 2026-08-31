from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.rag_service import rag_service

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3


@router.post("/query")
async def query_patents_act(
    request: QueryRequest, current_user: dict = Depends(get_current_user)
):
    try:
        results = rag_service.query(
            user_query=request.query, top_k=request.top_k
        )
        return {
            "status": "success",
            "user_id": current_user["user_id"],
            "query": request.query,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing hybrid retrieval: {str(e)}",
        )