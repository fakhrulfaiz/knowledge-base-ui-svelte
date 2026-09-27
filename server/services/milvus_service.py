from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from pymilvus import MilvusClient
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi
import re
from server.config import MILVUS_URI, MODEL_NAME

_milvus_client: Optional[MilvusClient] = None
_embedding_model: Optional[TextEmbedding] = None
BM25_CACHE: Dict[str, Any] = {}
COLLECTION_CENTROIDS: Dict[str, Any] = {}

def get_milvus_client() -> MilvusClient:
    global _milvus_client
    if _milvus_client is None:
        try:
            _milvus_client = MilvusClient(uri=MILVUS_URI)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to Milvus: {str(e)}")
    return _milvus_client

def get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name=MODEL_NAME)
    return _embedding_model

def get_collection_bm25(client: MilvusClient, col_name: str) -> Optional[Dict[str, Any]]:
    if col_name in BM25_CACHE:
        return BM25_CACHE[col_name]
    try:
        res = client.query(
            collection_name=col_name,
            filter="id > 0",
            limit=1500,
            output_fields=["id", "page_number", "chunk_index", "text", "char_count", "doc_name", "filename", "vector"]
        )
        if not res:
            return None
        corpus = [r.get("text", "") for r in res]
        tokenized_corpus = [re.findall(r"\w+", doc.lower()) for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        BM25_CACHE[col_name] = {"bm25": bm25, "chunks": res}
        return BM25_CACHE[col_name]
    except Exception:
        return None
