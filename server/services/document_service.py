import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from server.services.registry_service import load_registry, save_registry
from server.services.milvus_service import get_milvus_client, BM25_CACHE, COLLECTION_CENTROIDS

def purge_document_data(doc_id: str, col_id: Optional[str] = None, purge_vectors: bool = False) -> Dict[str, Any]:
    reg = load_registry()
    docs = reg.get("documents", [])
    doc_to_delete = next((d for d in docs if d["id"] == doc_id and (not col_id or d.get("collectionId") == col_id)), None)
    if not doc_to_delete:
        return {"status": "not_found", "id": doc_id}

    fname = doc_to_delete.get("filename")
    
    # 1. Check if other documents reference this file
    other_references = [
        d for d in docs 
        if d.get("filename") == fname and d["id"] != doc_id
    ]
    has_other_references = len(other_references) > 0

    # 2. Remove document ownership record from registry for this collection
    reg["documents"] = [d for d in docs if not (d["id"] == doc_id and (not col_id or d.get("collectionId") == col_id))]

    deleted_vectors = 0
    # 3. Only delete vectors if NO other collection references it AND purge_vectors requested
    if not has_other_references and purge_vectors:
        if "top_passages" in reg:
            reg["top_passages"] = [
                p for p in reg["top_passages"]
                if p.get("docId") != doc_id and p.get("docTitle") != doc_to_delete.get("title")
            ]

        c_id = doc_to_delete.get("collectionId")
        milvus_col_name = "all_knowledge_base"
        
        if milvus_col_name:
            try:
                client = get_milvus_client()
                if milvus_col_name in client.list_collections():
                    remaining_docs_in_col = [d for d in reg["documents"] if d.get("collectionId") == c_id]
                    if not remaining_docs_in_col:
                        stats = client.get_collection_stats(collection_name=milvus_col_name)
                        deleted_vectors = stats.get("row_count", 0)
                        client.delete(collection_name=milvus_col_name, filter="id >= 0")
                    else:
                        d_title = doc_to_delete.get("title", "")
                        del_filter = f'doc_name == "{d_title}"'
                        if fname:
                            del_filter += f' or doc_name == "{fname}"'
                        client.delete(collection_name=milvus_col_name, filter=del_filter)
                    BM25_CACHE.pop(milvus_col_name, None)
                    COLLECTION_CENTROIDS.pop(milvus_col_name, None)
            except Exception as e:
                print(f"[!] Warning during Milvus vector deletion: {e}")

    audit_detail = (
        f"Removed document '{doc_to_delete.get('title')}' from collection '{col_id or doc_to_delete.get('collectionId')}'. "
        f"{'Retained in other collections.' if has_other_references else ('Purged vector embeddings from Milvus.' if purge_vectors else 'Preserved vectors in Milvus.')}"
    )

    reg.setdefault("pipeline_jobs", []).insert(0, {
        "id": f"job-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "delete_document",
        "target": doc_to_delete.get("title", doc_id),
        "status": "completed",
        "durationMs": 25,
        "details": audit_detail
    })

    save_registry(reg)
    return {
        "status": "deleted",
        "id": doc_id,
        "title": doc_to_delete.get("title"),
        "has_other_references": has_other_references,
        "purged_vectors": purge_vectors and not has_other_references,
        "deleted_vectors_count": deleted_vectors
    }
