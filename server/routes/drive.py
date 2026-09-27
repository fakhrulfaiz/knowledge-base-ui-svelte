import os
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from server.config import DATA_DIR, GLOBAL_COLLECTION
from server.services.registry_service import load_registry
from server.services.extractor_service import get_extracted_cache
from server.services.milvus_service import get_milvus_client

router = APIRouter(tags=["Drive"])

@router.get("/api/pdf/{filename}")
def stream_pdf(filename: str):
    """Directly stream PDF file from /data for browser preview."""
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"PDF '{filename}' not found in Drive directory")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)

@router.get("/api/drive/files")
def list_drive_files():
    """
    Returns live inventory of physical files stored in /data (Corporate Drive).
    Each file reflects its real status in the Extractor Service and Ingest Service.
    """
    files = []
    reg = load_registry()
    registered_docs = reg.get("documents", [])

    for fname in os.listdir(DATA_DIR):
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.isfile(fpath) or fname.startswith(".") or fname.endswith(".json"):
            continue

        stat = os.stat(fpath)
        is_pdf = fname.lower().endswith(".pdf")
        
        extracted_cache = get_extracted_cache(fname)
        extractor_status = "extracted" if extracted_cache is not None else "not_extracted"
        extracted_at = extracted_cache.get("extractedAt") if extracted_cache else None
        page_count = extracted_cache.get("pageCount") if extracted_cache else 1
        summary = extracted_cache.get("summary") if extracted_cache else f"Raw file '{fname}' awaiting extraction."

        linked_docs = [d for d in registered_docs if d.get("filename") == fname]
        ingest_status = "ingested" if linked_docs else "not_ingested"

        files.append({
            "id": f"drive-{fname}",
            "filename": fname,
            "title": os.path.splitext(fname)[0].replace("_", " ").title(),
            "fileType": "pdf" if is_pdf else "docx" if fname.endswith(".docx") else "md",
            "sizeBytes": stat.st_size,
            "lastModified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "author": "Drive Storage Service",
            "previewSummary": summary,
            "scope": "org",
            "extractorStatus": extractor_status,
            "ingestStatus": ingest_status,
            "extractedAt": extracted_at,
            "pageCount": page_count,
            "linkedCollections": [d.get("collectionId") for d in linked_docs]
        })

    return {"files": files, "count": len(files)}

@router.post("/api/drive/upload")
async def upload_drive_file(file: UploadFile = File(...)):
    """Uploads a raw file directly into /data (Drive)."""
    dest_path = os.path.join(DATA_DIR, file.filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "sizeBytes": os.path.getsize(dest_path),
        "url": f"http://localhost:8080/data/{file.filename}"
    }
