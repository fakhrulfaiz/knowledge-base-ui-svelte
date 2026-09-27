import os
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from server.config import DATA_DIR, MODEL_NAME
from server.services.extractor_service import extract_pdf_document, get_extracted_cache
from server.services.ingestion_service import ingest_document_chunks_to_milvus
from server.services.milvus_service import get_milvus_client
from server.services.registry_service import load_registry

router = APIRouter(tags=["Pipeline"])

class ExtractRequest(BaseModel):
    filename: str

@router.post("/api/pipeline/extract")
def trigger_extract_service(req: ExtractRequest):
    """Executes the Extractor Service on a single file in /data."""
    result = extract_pdf_document(req.filename)
    return {
        "status": "extracted",
        "result": result
    }

@router.post("/api/pipeline/extract-all")
def trigger_extract_all_service():
    """Batch-extracts all unextracted files in /data."""
    extracted_count = 0
    errors = []
    for fname in os.listdir(DATA_DIR):
        if fname.lower().endswith(".pdf"):
            if not get_extracted_cache(fname):
                try:
                    extract_pdf_document(fname)
                    extracted_count += 1
                except Exception as e:
                    errors.append({"filename": fname, "error": str(e)})

    return {
        "status": "completed",
        "extracted_count": extracted_count,
        "errors": errors
    }

class IngestRequest(BaseModel):
    filename: str
    collection_id: Optional[str] = None
    collection_name: Optional[str] = None
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 60

@router.post("/api/pipeline/ingest")
def trigger_ingest_service(req: IngestRequest):
    """Executes the Ingestion Service on an extracted file, writing vectors to Milvus."""
    col_name = req.collection_name or req.collection_id or os.path.splitext(req.filename)[0].lower().replace(" ", "_")
    result = ingest_document_chunks_to_milvus(
        filename=req.filename,
        target_milvus_collection=col_name,
        chunk_size=req.chunk_size or 500,
        chunk_overlap=req.chunk_overlap or 60
    )
    return result

@router.get("/api/pipeline/status")
def get_pipeline_telemetry():
    """Returns live telemetry across Extractor and Ingestion services."""
    client = get_milvus_client()
    cols = client.list_collections()
    total_vectors = 0
    for c in cols:
        try:
            st = client.get_collection_stats(collection_name=c)
            total_vectors += st.get("row_count", 0)
        except Exception:
            pass

    drive_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    extracted_files = [f for f in drive_files if get_extracted_cache(f) is not None]

    reg = load_registry()
    recent_jobs = reg.get("pipeline_jobs", [])[:10]

    return {
        "extractor_service": {
            "status": "online",
            "engine": "pypdf-text-cleaner",
            "total_drive_files": len(drive_files),
            "extracted_files_count": len(extracted_files),
            "pending_files_count": len(drive_files) - len(extracted_files)
        },
        "ingest_service": {
            "status": "online",
            "vector_db": "Milvus Standalone (localhost:19530)",
            "embedding_model": MODEL_NAME,
            "dimensions": 384,
            "total_vectors_in_ram": total_vectors,
            "collections_count": len(cols)
        },
        "recent_jobs": recent_jobs
    }

@router.get("/api/pipeline/jobs")
def get_pipeline_jobs():
    reg = load_registry()
    return {"jobs": reg.get("pipeline_jobs", [])}
