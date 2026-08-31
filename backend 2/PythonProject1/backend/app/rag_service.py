import os
from typing import Optional
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


class RAGService:

    def __init__(self, storage_path: str = "../qdrant_storage"):
        self.storage_path = storage_path
        self._client: Optional[QdrantClient] = None
        self._dense_model: Optional[SentenceTransformer] = None
        self._sparse_model: Optional[SparseTextEmbedding] = None
        self.collection_name = "patents_act_hybrid"

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(path=self.storage_path)
        return self._client

    @property
    def dense_model(self) -> SentenceTransformer:
        if self._dense_model is None:
            self._dense_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._dense_model

    @property
    def sparse_model(self) -> SparseTextEmbedding:
        if self._sparse_model is None:
            self._sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        return self._sparse_model

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


rag_service = RAGService()