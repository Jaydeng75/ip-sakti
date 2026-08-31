import os

# Define folder structure
folders = [
    "backend/app/core",
    "backend/app/services",
    "backend/app/api/v1",
]

# Create directories
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# Define file contents
files = {
    "backend/.env": """PROJECT_NAME="Patents Act RAG Backend"
SECRET_KEY="e83920c78a2f1b4c9e3d8f7a1b0c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL="sqlite:///./patents_act_1970.db"
QDRANT_HOST="localhost"
QDRANT_PORT=6333
""",
    "backend/.env.example": """PROJECT_NAME="Patents Act RAG Backend"
SECRET_KEY="your-super-secret-key-here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL="sqlite:///./patents_act_1970.db"
QDRANT_HOST="localhost"
QDRANT_PORT=6333
""",
    "backend/requirements.txt": """fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
passlib[bcrypt]
python-jose[cryptography]
python-multipart
slowapi
qdrant-client
sentence-transformers
fastembed
pdfplumber
""",
    "backend/app/__init__.py": "",
    "backend/app/core/__init__.py": "",
    "backend/app/services/__init__.py": "",
    "backend/app/api/__init__.py": "",
    "backend/app/api/v1/__init__.py": "",
    "backend/app/core/config.py": """from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Patents Act RAG Backend"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
""",
    "backend/app/core/security.py": """from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
""",
    "backend/app/services/rag_service.py": """import os
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

class RAGService:
    def __init__(self, storage_path: str = "./qdrant_storage"):
        self.client = QdrantClient(path=storage_path)
        self.dense_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        self.collection_name = "patents_act_hybrid"

    def query(self, user_query: str, top_k: int = 3):
        dense_vec = self.dense_model.encode(user_query).tolist()
        sparse_res = list(self.sparse_model.embed([user_query]))[0]

        sparse_vec = models.SparseVector(
            indices=sparse_res.indices.tolist(),
            values=sparse_res.values.tolist(),
        )

        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(query=dense_vec, using="dense", limit=20),
                models.Prefetch(query=sparse_vec, using="sparse", limit=20),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        )

        return [pt.payload for pt in results.points]
""",
    "backend/app/api/v1/auth.py": """from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.core.security import create_access_token, verify_password, get_password_hash

router = APIRouter()

MOCK_USERS_DB = {
    "lawyer@example.com": {
        "id": 1,
        "email": "lawyer@example.com",
        "hashed_password": get_password_hash("password123"),
        "role": "user",
    },
    "admin@example.com": {
        "id": 2,
        "email": "admin@example.com",
        "hashed_password": get_password_hash("admin123"),
        "role": "admin",
    },
}

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = MOCK_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]}
    )

    return {"access_token": access_token, "token_type": "bearer"}
""",
    "backend/app/main.py": """from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import auth
from app.core.config import settings

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.PROJECT_NAME)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

@app.get("/")
def root():
    return {"status": "ok", "project": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
""",
}

# Write files
for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Backend project structure generated successfully!")