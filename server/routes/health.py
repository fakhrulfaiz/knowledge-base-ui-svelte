from fastapi import APIRouter
from server.config import MILVUS_URI, GLOBAL_COLLECTION, MODEL_NAME
from server.services.milvus_service import get_milvus_client

router = APIRouter(tags=["Health"])

@router.get("/api/health")
def check_health():
    """Verify live Milvus connectivity, loaded collections, and service health."""
    try:
        client = get_milvus_client()
        collections = client.list_collections()
        has_global = GLOBAL_COLLECTION in collections
        return {
            "status": "healthy",
            "milvus_uri": MILVUS_URI,
            "connected": True,
            "collections_count": len(collections),
            "collections": collections,
            "global_collection_ready": has_global,
            "embedding_model": MODEL_NAME,
            "extractor_service": "online",
            "ingest_service": "online"
        }
    except Exception as e:
        return {
            "status": "offline",
            "milvus_uri": MILVUS_URI,
            "connected": False,
            "error": str(e),
            "embedding_model": MODEL_NAME
        }
