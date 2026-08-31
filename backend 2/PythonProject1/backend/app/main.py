import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import auth, rag
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.PROJECT_NAME)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["RAG Search"])

@app.get("/")
def root():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)