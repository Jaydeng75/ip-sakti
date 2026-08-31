import os
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

EMBEDDING_MODEL = os.getenv("RETRIEVAL_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
EMBEDDING_REVISION = os.getenv(
    "RETRIEVAL_EMBEDDING_REVISION", "614241f622f53c4eeff9890bdc4f31cfecc418b3"
)
RERANKER_MODEL = os.getenv("RETRIEVAL_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
RERANKER_REVISION = os.getenv(
    "RETRIEVAL_RERANKER_REVISION", "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
)
SERVICE_TOKEN = os.getenv("RETRIEVAL_SERVICE_TOKEN")
HF_TOKEN = os.getenv("RETRIEVAL_HF_TOKEN")
CACHE_DIR = os.getenv("HF_HOME", "/models/huggingface")
PRELOAD = os.getenv("RETRIEVAL_PRELOAD_MODELS", "false").lower() == "true"
REQUIRE_PINNED = os.getenv("RETRIEVAL_REQUIRE_PINNED_REVISIONS", "true").lower() == "true"


class EmbeddingRequest(BaseModel):
    model: str | None = None
    input: list[str] | str
    encoding_format: str = "float"


class RerankRequest(BaseModel):
    model: str | None = None
    query: str = Field(min_length=1, max_length=8_000)
    texts: list[str] = Field(min_length=1, max_length=100)


class ModelManager:
    def __init__(self) -> None:
        self._embedding = None
        self._reranker = None
        self._lock = threading.Lock()

    def embedding(self):
        with self._lock:
            if self._embedding is None:
                from sentence_transformers import SentenceTransformer

                self._embedding = SentenceTransformer(
                    EMBEDDING_MODEL,
                    revision=EMBEDDING_REVISION,
                    cache_folder=CACHE_DIR,
                    token=HF_TOKEN,
                )
            return self._embedding

    def reranker(self):
        with self._lock:
            if self._reranker is None:
                from sentence_transformers import CrossEncoder

                self._reranker = CrossEncoder(
                    RERANKER_MODEL,
                    revision=RERANKER_REVISION,
                    cache_folder=CACHE_DIR,
                    token=HF_TOKEN,
                )
            return self._reranker


models = ModelManager()


def authorize(authorization: str | None = Header(default=None)) -> None:
    if SERVICE_TOKEN and authorization != f"Bearer {SERVICE_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid service credential")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if REQUIRE_PINNED and (EMBEDDING_REVISION == "main" or RERANKER_REVISION == "main"):
        raise RuntimeError("Immutable embedding and reranker revisions are required")
    if PRELOAD:
        models.embedding()
        models.reranker()
    yield


app = FastAPI(title="IP-SAKTI Neural Retrieval Service", version="1.0.0", lifespan=lifespan)


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    return {
        "status": "ready",
        "embedding_model": EMBEDDING_MODEL,
        "embedding_revision": EMBEDDING_REVISION,
        "reranker_model": RERANKER_MODEL,
        "reranker_revision": RERANKER_REVISION,
        "preloaded": PRELOAD,
    }


@app.post("/v1/embeddings", dependencies=[Depends(authorize)])
def embeddings(payload: EmbeddingRequest):
    values = [payload.input] if isinstance(payload.input, str) else payload.input
    if not values or len(values) > 128:
        raise HTTPException(status_code=422, detail="Provide between 1 and 128 inputs")
    vectors = models.embedding().encode(
        values,
        batch_size=min(32, len(values)),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return {
        "object": "list",
        "model": EMBEDDING_MODEL,
        "data": [
            {"object": "embedding", "index": index, "embedding": vector.tolist()}
            for index, vector in enumerate(vectors)
        ],
    }


@app.post("/v1/rerank", dependencies=[Depends(authorize)])
def rerank(payload: RerankRequest):
    pairs = [(payload.query, text) for text in payload.texts]
    scores = models.reranker().predict(pairs, show_progress_bar=False)
    results = [
        {"index": index, "relevance_score": float(score)}
        for index, score in enumerate(scores)
    ]
    return {"model": RERANKER_MODEL, "results": sorted(results, key=lambda item: item["relevance_score"], reverse=True)}
