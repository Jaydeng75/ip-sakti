import os
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
