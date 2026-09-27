import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from server.config import DATA_DIR, GLOBAL_COLLECTION
from server.services.registry_service import load_registry, save_registry, get_distinct_color
from server.services.extractor_service import get_extracted_cache, extract_pdf_document
from server.services.ingestion_service import ingest_document_chunks_to_milvus
from server.services.milvus_service import get_milvus_client
from server.services.document_service import purge_document_data

router = APIRouter(tags=["Collections"])

class CreateCollectionRequest(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    scope: str = "org"  # 'org', 'team', or 'project'
    teamName: Optional[str] = None
    projectName: Optional[str] = None
    allocatedGb: Optional[int] = 10
    colorTheme: Optional[str] = None

class UpdateCollectionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    teamName: Optional[str] = None
    projectName: Optional[str] = None
    allocatedGb: Optional[int] = None
    colorTheme: Optional[str] = None

@router.get("/api/collections")
def list_collections():
    """Returns all registered collections with live row counts from Milvus."""
    client = get_milvus_client()
    reg = load_registry()
    collections = reg.get("collections", [])
    registered_docs = reg.get("documents", [])
    milvus_cols = set(client.list_collections())

    # Precompute vector chunk counts per filename from all_knowledge_base
    file_chunk_counts = {}
    total_system_chunks = 0
    if "all_knowledge_base" in milvus_cols:
        try:
            stats = client.get_collection_stats(collection_name="all_knowledge_base")
            total_system_chunks = stats.get("row_count", 0)
            all_chunks = client.query(
                collection_name="all_knowledge_base",
                filter="",
                limit=5000,
                output_fields=["filename"]
            )
            from collections import Counter
            file_chunk_counts = dict(Counter(x.get("filename") for x in all_chunks if x.get("filename")))
        except Exception as e:
            print(f"[Milvus] Warning querying chunk stats: {e}")

    result = []

    for col in collections:
        c_id = col["id"]
        c_name = col.get("collection_name") or c_id.replace("col-", "").replace("-", "_")

        col_docs = [
            d for d in registered_docs
            if d.get("collectionId") == c_id or c_id in d.get("collections", []) or d.get("collectionId") == c_name
        ]
        doc_count = len(col_docs)

        # Check if this collection has its own physical Milvus collection
        row_count = 0
        if c_name in milvus_cols and c_name != "all_knowledge_base":
            try:
                stats = client.get_collection_stats(collection_name=c_name)
                row_count = stats.get("row_count", 0)
            except Exception:
                row_count = 0
        else:
            # Sum up vector counts from its documents indexed in all_knowledge_base
            seen_files = set()
            for d in col_docs:
                fname = d.get("filename")
                if fname and fname not in seen_files:
                    seen_files.add(fname)
                    row_count += file_chunk_counts.get(fname, 0)

        col_color = col.get("colorTheme") or get_distinct_color(c_name)

        result.append({
            "id": c_id,
            "name": col["name"],
            "collection_name": c_name,
            "display_name": col["name"],
            "description": col.get("description", ""),
            "scope": col.get("scope", "org"),
            "teamName": col.get("teamName"),
            "projectName": col.get("projectName"),
            "allocatedGb": col.get("allocatedGb", 10),
            "createdBy": col.get("createdBy", {"name": "Elena Rostova", "email": "elena.rostova@enterprise.corp"}),
            "createdAt": col.get("createdAt", "2026-09-26T00:00:00Z"),
            "updatedAt": col.get("updatedAt", "2026-09-26T00:00:00Z"),
            "documentCount": doc_count,
            "chunk_count": row_count,
            "totalChunks": row_count,
            "tags": col.get("tags", ["Milvus Live", col.get("scope", "org").upper()]),
            "colorTheme": col_color,
            "color": col_color
        })

    # Global Corpus Virtual Collection
    result.append({
        "id": "all_knowledge_base",
        "name": "Global Enterprise Corpus",
        "collection_name": "all_knowledge_base",
        "display_name": "Global Enterprise Corpus",
        "description": "Unified enterprise collection accessing all documents via metadata tagging (Zero vector duplication in RAM).",
        "scope": "org",
        "allocatedGb": 50,
        "createdBy": {"name": "Architecture Council", "email": "council@enterprise.corp"},
        "createdAt": "2026-09-26T00:00:00Z",
        "updatedAt": "2026-09-26T00:00:00Z",
        "documentCount": len(registered_docs),
        "chunk_count": total_system_chunks,
        "totalChunks": total_system_chunks,
        "tags": ["Global", "Single Vector in RAM", "Multi-Collection Shared"],
        "colorTheme": "#38bdf8",
        "color": "#38bdf8"
    })

    return {"collections": result}

@router.post("/api/collections")
def create_collection(req: CreateCollectionRequest):
    """Creates a new collection record."""
    reg = load_registry()
    col_id = req.id or f"col-{uuid.uuid4().hex[:8]}"
    clean_name = req.name.strip()
    c_name = clean_name.lower().replace(" ", "_").replace("-", "_")

    new_col = {
        "id": col_id,
        "name": clean_name,
        "collection_name": c_name,
        "description": req.description or "",
        "scope": req.scope if req.scope in ["org", "team", "project"] else "org",
        "teamName": req.teamName,
        "projectName": req.projectName,
        "allocatedGb": req.allocatedGb or 10,
        "colorTheme": req.colorTheme or get_distinct_color(clean_name),
        "createdBy": {"name": "Elena Rostova", "email": "elena.rostova@enterprise.corp"},
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "tags": [req.scope.upper(), req.teamName or req.projectName or "General"]
    }

    reg.setdefault("collections", []).append(new_col)
    save_registry(reg)
    return new_col

@router.get("/api/collections/{col_id}")
def get_collection(col_id: str):
    reg = load_registry()
    col = next((c for c in reg.get("collections", []) if c["id"] == col_id), None)
    if not col and col_id != "all_knowledge_base":
        raise HTTPException(status_code=404, detail="Collection not found")
    return col

@router.put("/api/collections/{col_id}")
def update_collection(col_id: str, req: UpdateCollectionRequest):
    reg = load_registry()
    col = next((c for c in reg.get("collections", []) if c["id"] == col_id), None)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    if req.name: col["name"] = req.name
    if req.description is not None: col["description"] = req.description
    if req.scope: col["scope"] = req.scope
    if req.teamName is not None: col["teamName"] = req.teamName
    if req.projectName is not None: col["projectName"] = req.projectName
    if req.allocatedGb is not None: col["allocatedGb"] = req.allocatedGb
    if req.colorTheme: col["colorTheme"] = req.colorTheme
    col["updatedAt"] = datetime.now(timezone.utc).isoformat()

    save_registry(reg)
    return col

@router.delete("/api/collections/{col_id}")
def delete_collection(col_id: str, purge_vectors: bool = Query(False)):
    if col_id in ["all_knowledge_base", "global"]:
        raise HTTPException(status_code=400, detail="Cannot delete the global enterprise corpus.")

    reg = load_registry()
    collections = reg.get("collections", [])
    target_col = next((c for c in collections if c["id"] == col_id), None)
    if not target_col:
        raise HTTPException(status_code=404, detail="Collection not found")

    client = get_milvus_client()
    c_name = target_col.get("collection_name") or col_id.replace("col-", "").replace("-", "_")

    # If purge_vectors is requested, drop any dedicated Milvus vector collection
    if purge_vectors:
        try:
            if client.has_collection(c_name) and c_name != "all_knowledge_base":
                client.drop_collection(c_name)
        except Exception as e:
            print(f"[Milvus] Warning dropping collection {c_name}: {e}")

    # Remove collection from registry
    reg["collections"] = [c for c in collections if c["id"] != col_id]

    # Handle registered documents
    registered_docs = reg.get("documents", [])
    remaining_docs = []
    purged_doc_count = 0

    for d in registered_docs:
        if d.get("collectionId") == col_id:
            if purge_vectors:
                # Also delete vectors from all_knowledge_base for these docs
                filename = d.get("filename")
                try:
                    if client.has_collection("all_knowledge_base"):
                        client.delete(
                            collection_name="all_knowledge_base",
                            filter=f'doc_name == "{filename}" or filename == "{filename}"'
                        )
                except Exception as e:
                    print(f"[Milvus] Warning deleting doc vectors: {e}")
                purged_doc_count += 1
            else:
                # Reassign to all_knowledge_base
                d["collectionId"] = "all_knowledge_base"
                remaining_docs.append(d)
        else:
            remaining_docs.append(d)

    reg["documents"] = remaining_docs
    save_registry(reg)

    return {
        "status": "deleted",
        "id": col_id,
        "name": target_col.get("name"),
        "purged_vectors": purge_vectors,
        "purged_docs": purged_doc_count
    }

class AddDocumentToCollectionRequest(BaseModel):
    filename: str
    title: Optional[str] = None
    visibility: Optional[str] = "shared"  # 'private' or 'shared'
    source: Optional[str] = "drive"
    uploadedBy: Optional[str] = "Elena Rostova"

@router.post("/api/collections/{col_id}/documents")
def add_document_to_collection(col_id: str, req: AddDocumentToCollectionRequest):
    reg = load_registry()
    col = next((c for c in reg.get("collections", []) if c["id"] == col_id), None)
    if not col and col_id != "all_knowledge_base":
        raise HTTPException(status_code=404, detail="Target collection not found")

    pdf_path = os.path.join(DATA_DIR, req.filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"File '{req.filename}' not found in Drive directory")

    client = get_milvus_client()
    already_indexed = False
    if client.has_collection("all_knowledge_base"):
        try:
            check_hits = client.query(
                collection_name="all_knowledge_base",
                filter=f'filename == "{req.filename}" or doc_name == "{req.filename}"',
                limit=1,
                output_fields=["id"]
            )
            already_indexed = len(check_hits) > 0
        except Exception:
            already_indexed = False

    if not already_indexed:
        ingest_document_chunks_to_milvus(
            filename=req.filename,
            target_milvus_collection="all_knowledge_base"
        )

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    doc_title = req.title or extracted.get("title") or req.filename

    new_doc_entry = {
        "id": doc_id,
        "collectionId": col_id,
        "collections": [col_id, "all_knowledge_base"],
        "title": doc_title,
        "filename": req.filename,
        "pdfUrl": f"http://localhost:8080/data/{req.filename}",
        "fileType": "pdf",
        "source": req.source or "drive",
        "visibility": req.visibility if req.visibility in ["private", "shared"] else "shared",
        "uploadedBy": req.uploadedBy or "Elena Rostova",
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
        "status": "indexed"
    }

    reg.setdefault("documents", []).append(new_doc_entry)
    save_registry(reg)

    return {
        "status": "added",
        "reused_vector_index": already_indexed,
        "document": new_doc_entry
    }

@router.delete("/api/collections/{col_id}/documents/{doc_id}")
def remove_document_from_collection(col_id: str, doc_id: str, purge_vectors: bool = Query(False)):
    return purge_document_data(doc_id, col_id=col_id, purge_vectors=purge_vectors)
