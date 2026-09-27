import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from server.config import DATA_DIR
from server.services.registry_service import load_registry, save_registry
from server.services.extractor_service import get_extracted_cache, extract_pdf_document
from server.services.milvus_service import get_milvus_client
from server.services.document_service import purge_document_data

router = APIRouter(tags=["Documents"])

@router.get("/api/documents")
def list_documents(
    collection_id: Optional[str] = Query(None),
    scope: Optional[str] = Query("all"),
    visibility: Optional[str] = Query("all")
):
    """
    Returns full documents with pages and chunk structures.
    Supports filtering by collectionId, scope ('org', 'team', 'project'), and visibility ('private', 'shared').
    """
    client = get_milvus_client()
    milvus_cols = set(client.list_collections())
    reg = load_registry()
    registered_docs = reg.get("documents", [])
    collections_map = {c["id"]: c for c in reg.get("collections", [])}

    documents = []

    for d_entry in registered_docs:
        c_id = d_entry.get("collectionId")
        if collection_id and collection_id not in ["all", ""] and c_id != collection_id:
            continue

        doc_visibility = d_entry.get("visibility", "shared")
        if visibility and visibility != "all" and doc_visibility != visibility:
            continue

        col_obj = collections_map.get(c_id, {})
        doc_scope = col_obj.get("scope", "org")
        if scope and scope != "all" and doc_scope != scope:
            continue

        fname = d_entry.get("filename", "")
        extracted = get_extracted_cache(fname)
        if not extracted:
            try:
                extracted = extract_pdf_document(fname)
            except Exception:
                extracted = None

        pages_data = []
        total_chunks = 0
        total_tokens = 0

        milvus_col_name = "all_knowledge_base"
        milvus_chunks = []
        if milvus_col_name in milvus_cols:
            try:
                milvus_chunks = client.query(
                    collection_name=milvus_col_name,
                    filter=f'doc_name == "{fname}" or filename == "{fname}"',
                    limit=500,
                    output_fields=["id", "page_number", "chunk_index", "text", "char_count", "doc_name"]
                )
            except Exception:
                milvus_chunks = []

        if extracted:
            for p in extracted.get("pages", []):
                p_num = p["pageNumber"]
                page_chunks = [ch for ch in milvus_chunks if ch.get("page_number") == p_num]
                if not page_chunks and p["content"].strip():
                    words = p["content"].split()
                    chunk_obj = {
                        "id": f"{d_entry['id']}-p{p_num}-c1",
                        "docId": d_entry["id"],
                        "collectionId": c_id,
                        "pageNumber": p_num,
                        "chunkIndex": 1,
                        "tokenCount": max(1, len(words)),
                        "snippet": p["content"][:300],
                        "startOffset": 0,
                        "endOffset": len(p["content"]),
                        "sectionHeading": f"Page {p_num}",
                        "entities": [],
                        "scope": doc_scope,
                        "keywords": []
                    }
                    p_chunks = [chunk_obj]
                else:
                    p_chunks = []
                    for ch in page_chunks:
                        c_words = ch.get("text", "").split()
                        p_chunks.append({
                            "id": f"{d_entry['id']}-chunk-{ch['id']}",
                            "docId": d_entry["id"],
                            "collectionId": c_id,
                            "pageNumber": p_num,
                            "chunkIndex": ch.get("chunk_index", ch["id"]),
                            "tokenCount": max(1, len(c_words)),
                            "snippet": ch.get("text", ""),
                            "startOffset": 0,
                            "endOffset": ch.get("char_count", len(ch.get("text", ""))),
                            "sectionHeading": f"Section {ch.get('chunk_index', ch['id'])}",
                            "entities": [],
                            "scope": doc_scope,
                            "keywords": []
                        })

                pages_data.append({
                    "pageNumber": p_num,
                    "header": p.get("header", f"Page {p_num}"),
                    "content": p.get("content", ""),
                    "chunks": p_chunks
                })
                total_chunks += len(p_chunks)
                total_tokens += sum(c["tokenCount"] for c in p_chunks)

        pdf_path = os.path.join(DATA_DIR, fname)
        file_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 1024 * 1024

        documents.append({
            "id": d_entry["id"],
            "collectionId": c_id,
            "collections": d_entry.get("collections", [c_id, "all_knowledge_base"]),
            "title": d_entry.get("title", fname),
            "filename": fname,
            "fileType": "pdf",
            "source": d_entry.get("source", "drive"),
            "visibility": doc_visibility,
            "pdfUrl": d_entry.get("pdfUrl") or f"http://localhost:8080/data/{fname}",
            "uploadedBy": d_entry.get("uploadedBy", "Elena Rostova"),
            "uploadedAt": d_entry.get("uploadedAt", "2026-09-26T00:00:00Z"),
            "sizeBytes": file_size,
            "pageCount": len(pages_data) or 1,
            "chunkCount": total_chunks,
            "totalChunks": total_chunks,
            "totalTokens": total_tokens,
            "summary": extracted.get("summary", "") if extracted else d_entry.get("title", fname),
            "entities": [],
            "crossReferences": [],
            "semanticTopics": [col_obj.get("name", "Enterprise Knowledge")],
            "scope": doc_scope,
            "status": "indexed",
            "pages": pages_data
        })

    return {"documents": documents}

@router.patch("/api/documents/{doc_id}")
def update_document(doc_id: str, updates: Dict[str, Any] = Body(...)):
    reg = load_registry()
    doc = next((d for d in reg.get("documents", []) if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if "title" in updates:
        doc["title"] = updates["title"]
    if "visibility" in updates:
        if updates["visibility"] in ["private", "shared"]:
            doc["visibility"] = updates["visibility"]
    save_registry(reg)
    return doc

@router.get("/api/documents/{doc_id}/references")
def get_document_references(doc_id: str):
    """Checks whether a document's physical file is referenced by other collections."""
    reg = load_registry()
    docs = reg.get("documents", [])
    target = next((d for d in docs if d["id"] == doc_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Document not found")

    fname = target.get("filename")
    cols_map = {c["id"]: c for c in reg.get("collections", [])}

    other_refs = []
    for d in docs:
        if d.get("filename") == fname and d["id"] != doc_id:
            c = cols_map.get(d.get("collectionId"), {})
            other_refs.append({
                "docId": d["id"],
                "collectionId": d.get("collectionId"),
                "collectionName": c.get("name", d.get("collectionId")),
                "scope": c.get("scope", "org"),
                "visibility": d.get("visibility", "shared")
            })

    return {
        "docId": doc_id,
        "title": target.get("title"),
        "filename": fname,
        "collectionId": target.get("collectionId"),
        "otherReferences": other_refs,
        "hasOtherReferences": len(other_refs) > 0,
        "canPurgeVectors": len(other_refs) == 0
    }

@router.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, purge_vectors: bool = Query(False)):
    return purge_document_data(doc_id, purge_vectors=purge_vectors)

@router.delete("/api/chunks/{chunk_id}")
def delete_chunk(chunk_id: str):
    """Deletes a specific chunk from Milvus and purges its citation from top passages."""
    reg = load_registry()
    
    original_passages = reg.get("top_passages", [])
    purged_passage = next((p for p in original_passages if p.get("id") == chunk_id or str(p.get("chunk_id")) == chunk_id), None)
    reg["top_passages"] = [
        p for p in original_passages
        if p.get("id") != chunk_id and str(p.get("chunk_id")) != chunk_id
    ]

    numeric_id = None
    if "-chunk-" in chunk_id:
        try:
            numeric_id = int(chunk_id.split("-chunk-")[-1])
        except ValueError:
            numeric_id = None
    elif chunk_id.isdigit():
        numeric_id = int(chunk_id)

    client = get_milvus_client()
    milvus_deleted = False
    if numeric_id is not None:
        for cname in client.list_collections():
            try:
                client.delete(collection_name=cname, filter=f"id == {numeric_id}")
                milvus_deleted = True
            except Exception:
                pass

    reg.setdefault("pipeline_jobs", []).insert(0, {
        "id": f"job-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "delete_chunk",
        "target": f"Chunk #{chunk_id}",
        "status": "completed",
        "durationMs": 24,
        "details": f"Deleted chunk vector #{chunk_id} from Milvus and purged citation telemetry."
    })

    save_registry(reg)
    return {
        "status": "deleted",
        "chunk_id": chunk_id,
        "milvus_deleted": milvus_deleted,
        "purged_passage": purged_passage
    }
