from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query
import numpy as np
from server.services.registry_service import load_registry, get_distinct_color
from server.services.milvus_service import get_milvus_client

router = APIRouter(tags=["Graph"])

def compute_unified_semantic_projection(
    doc_keys: List[str],
    doc_centroids: Dict[str, np.ndarray],
    chunk_items: List[tuple]
) -> tuple[Dict[str, tuple[float, float]], Dict[str, tuple[float, float]], List[Dict[str, Any]]]:
    """Projects document centroids and individual chunk vectors together into 2D semantic space using SVD/PCA."""
    doc_centroid_vecs = [doc_centroids[k] for k in doc_keys]
    chunk_vecs = [item[1]["vector"] for item in chunk_items if "vector" in item[1] and item[1]["vector"]]
    
    total_vecs = doc_centroid_vecs + chunk_vecs
    if len(total_vecs) >= 2:
        all_arr = np.array(total_vecs, dtype=np.float32)
        vecs_centered = all_arr - np.mean(all_arr, axis=0)
        U, S, Vt = np.linalg.svd(vecs_centered, full_matrices=False)
        coords_2d = U[:, :2] * S[:2]
        max_dist = float(np.max(np.abs(coords_2d)))
        if max_dist > 1e-6:
            coords_2d /= max_dist
    else:
        coords_2d = np.zeros((len(total_vecs), 2), dtype=np.float32)

    doc_coords: Dict[str, tuple[float, float]] = {}
    for i, d_key in enumerate(doc_keys):
        doc_coords[d_key] = (round(float(coords_2d[i, 0]), 4), round(float(coords_2d[i, 1]), 4))

    chunk_coords: Dict[str, tuple[float, float]] = {}
    for j, (d_key, c_row) in enumerate(chunk_items):
        c_idx = len(doc_keys) + j
        chunk_coords[c_row["id"]] = (round(float(coords_2d[c_idx, 0]), 4), round(float(coords_2d[c_idx, 1]), 4))

    # Compute inter-document bridges using centroid cosine similarity
    bridges = []
    if len(doc_keys) >= 2:
        cen_arr = np.array(doc_centroid_vecs, dtype=np.float32)
        cen_sim = np.clip(np.dot(cen_arr, cen_arr.T), -1.0, 1.0)
        for i in range(len(doc_keys)):
            for j in range(i + 1, len(doc_keys)):
                sim_val = float(cen_sim[i, j])
                if sim_val >= 0.70:
                    bridges.append({
                        "col_a": doc_keys[i],
                        "col_b": doc_keys[j],
                        "similarity": round(sim_val, 4)
                    })

    return doc_coords, chunk_coords, bridges

@router.get("/api/graph")
def get_graph(
    scope: str = Query("all", description="Scope filter: 'all', 'org', 'team', 'project'"),
    collection_id: str = Query("all", description="Milvus Collection name or 'all'"),
    limit_chunks: int = Query(25, description="Max real chunks to load per document")
):
    """Builds true Attu-style 2D vector semantic graph from live Milvus global collection."""
    client = get_milvus_client()
    reg = load_registry()
    docs = reg.get("documents", [])
    col_meta = {c["id"]: c for c in reg.get("collections", [])}
    for c in reg.get("collections", []):
        if c.get("collection_name"):
            col_meta[c["collection_name"]] = c

    valid_docs = []
    for d in docs:
        c = col_meta.get(d.get("collectionId"), {})
        if scope != "all" and c.get("scope", "org") != scope:
            continue
        if collection_id not in ["all", ""]:
            cid_match = (
                d.get("collectionId") == collection_id
                or c.get("collection_name") == collection_id
                or collection_id in d.get("collections", [])
                or d.get("id") == collection_id
            )
            if not cid_match:
                continue
        valid_docs.append(d)

    if not valid_docs and collection_id == "all" and scope == "all":
        valid_docs = docs

    col_name = "all_knowledge_base"
    if not client.has_collection(col_name):
        return {
            "collection_id": collection_id,
            "scope": scope,
            "nodes": [],
            "edges": [],
            "stats": {"total_nodes": 0, "total_edges": 0, "collections_included": 0, "bridges_count": 0}
        }

    per_doc_limit = limit_chunks if limit_chunks > 0 else 60
    doc_chunks: Dict[str, List[Dict[str, Any]]] = {}

    # Query chunks per document to ensure balanced, authentic representation across all sources
    for d in valid_docs:
        d_name = d.get("title")
        f_name = d.get("filename")
        doc_key = d_name or f_name
        if not doc_key:
            continue
        try:
            f_expr = f'doc_name == "{d_name}" or filename == "{f_name}" or filename == "{d_name}"'
            q_res = client.query(
                collection_name=col_name,
                filter=f_expr,
                limit=per_doc_limit,
                output_fields=["id", "page_number", "chunk_index", "text", "char_count", "doc_name", "filename", "vector"]
            )
            if q_res:
                doc_chunks[doc_key] = q_res
        except Exception as e:
            print(f"[!] Error querying Milvus chunks for doc {doc_key}: {e}")

    # Fallback to general query if specific doc queries found nothing
    if not doc_chunks:
        try:
            res = client.query(
                collection_name=col_name,
                filter="id > 0",
                limit=max(300, per_doc_limit * max(1, len(valid_docs))),
                output_fields=["id", "page_number", "chunk_index", "text", "char_count", "doc_name", "filename", "vector"]
            )
            for row in res:
                doc_key = row.get("doc_name") or "Unknown Document"
                if len(doc_chunks.get(doc_key, [])) < per_doc_limit:
                    doc_chunks.setdefault(doc_key, []).append(row)
        except Exception as e:
            print(f"[!] General query fallback error: {e}")

    # Compute normalized document centroids
    doc_centroids: Dict[str, np.ndarray] = {}
    doc_keys: List[str] = []
    for d_key, chunks in doc_chunks.items():
        vecs = [c["vector"] for c in chunks if "vector" in c and c["vector"] and len(c["vector"]) > 0]
        if vecs:
            arr = np.array(vecs, dtype=np.float32)
            c_mean = np.mean(arr, axis=0)
            norm = np.linalg.norm(c_mean)
            c_norm = c_mean / norm if norm > 0 else c_mean
            doc_centroids[d_key] = c_norm
            doc_keys.append(d_key)

    # Collect chunk items that have vectors
    chunk_items: List[tuple] = []
    chunk_vecs: List[List[float]] = []
    for d_key in doc_keys:
        for c in doc_chunks[d_key]:
            if "vector" in c and c["vector"] and len(c["vector"]) > 0:
                chunk_items.append((d_key, c))
                chunk_vecs.append(c["vector"])

    # Dimensionality reduction: Unified SVD / PCA across document centroids + all chunks
    doc_coords, chunk_coords, semantic_bridges = compute_unified_semantic_projection(
        doc_keys, doc_centroids, chunk_items
    )

    nodes = []
    edges = []

    # 1. Document Hub Nodes (sit at the true semantic centroid of their chunks)
    for d_key in doc_keys:
        chunks = doc_chunks[d_key]
        doc_info = next((d for d in valid_docs if d.get("title") == d_key or d.get("filename") == d_key), {})
        c_info = col_meta.get(doc_info.get("collectionId"), {})
        
        doc_node_id = f"doc-{d_key}"
        col_color = c_info.get("colorTheme") or get_distinct_color(d_key)
        sem_x, sem_y = doc_coords.get(d_key, (0.0, 0.0))
        pdf_file = doc_info.get("filename") or chunks[0].get("filename", f"{d_key}.pdf")

        nodes.append({
            "id": doc_node_id,
            "label": d_key,
            "type": "document",
            "collection_name": col_name,
            "color": col_color,
            "size": 9.0,
            "semantic_x": sem_x,
            "semantic_y": sem_y,
            "meta": {
                "title": d_key,
                "doc_name": d_key,
                "collection_name": col_name,
                "pdf_filename": pdf_file,
                "pdf_url": f"http://localhost:8080/data/{pdf_file}",
                "scope": c_info.get("scope", "org"),
                "teamName": c_info.get("teamName"),
                "projectName": c_info.get("projectName"),
                "file_type": "PDF Document",
                "chunks_count": len(chunks),
                "total_chunks": doc_info.get("chunkCount", len(chunks)),
                "semantic_coords": [sem_x, sem_y]
            }
        })

    # 2. Chunk Nodes (sit at their true individual 2D vector coordinates!)
    for d_key, row in chunk_items:
        doc_node_id = f"doc-{d_key}"
        doc_info = next((d for d in valid_docs if d.get("title") == d_key or d.get("filename") == d_key), {})
        c_info = col_meta.get(doc_info.get("collectionId"), {})
        col_color = c_info.get("colorTheme") or get_distinct_color(d_key)
        pdf_file = doc_info.get("filename") or row.get("filename", f"{d_key}.pdf")

        cid = f"{col_name}-chunk-{row['id']}"
        page_num = row.get("page_number", 1)
        chunk_num = row.get("chunk_index", row["id"] % 100000)
        text = row.get("text", "")
        excerpt = text[:180] + "..." if len(text) > 180 else text
        sem_x, sem_y = chunk_coords.get(row["id"], doc_coords.get(d_key, (0.0, 0.0)))

        nodes.append({
            "id": cid,
            "label": f"Page {page_num} #{chunk_num}",
            "type": "chunk",
            "parent_id": doc_node_id,
            "collection_name": col_name,
            "color": col_color,
            "size": 5.5,
            "semantic_x": sem_x,
            "semantic_y": sem_y,
            "meta": {
                "doc_name": d_key,
                "collection_name": col_name,
                "pdf_filename": pdf_file,
                "pdf_url": f"http://localhost:8080/data/{pdf_file}#page={page_num}",
                "page_number": page_num,
                "chunk_index": chunk_num,
                "char_count": row.get("char_count", len(text)),
                "text": text,
                "excerpt": excerpt,
                "source": "Milvus Vector Store",
                "semantic_coords": [sem_x, sem_y]
            }
        })

        # Subtle hierarchy edge: document centroid -> chunk
        edges.append({
            "source": doc_node_id,
            "target": cid,
            "type": "hierarchy",
            "weight": 0.45,
            "label": f"Page {page_num}"
        })

    # 3. Inter-chunk semantic similarity & sequential edges (Attu nearest-neighbor graph)
    if len(chunk_vecs) >= 2:
        vecs_mat = np.array(chunk_vecs, dtype=np.float32)
        norms = np.linalg.norm(vecs_mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vecs = vecs_mat / norms
        sim_matrix = np.dot(normalized_vecs, normalized_vecs.T)

        existing_pairs = set()
        for i in range(len(chunk_items)):
            sims = sim_matrix[i]
            sorted_indices = np.argsort(sims)[::-1]
            connected = 0
            for j in sorted_indices:
                if i == j:
                    continue
                sim_val = float(sims[j])
                if sim_val < 0.65:
                    break
                pair_key = (min(i, j), max(i, j))
                if pair_key not in existing_pairs:
                    existing_pairs.add(pair_key)
                    c_id_i = f"{col_name}-chunk-{chunk_items[i][1]['id']}"
                    c_id_j = f"{col_name}-chunk-{chunk_items[j][1]['id']}"
                    edges.append({
                        "source": c_id_i,
                        "target": c_id_j,
                        "type": "chunk_similarity",
                        "weight": round(sim_val, 3),
                        "similarity": round(sim_val, 3),
                        "label": f"{int(round(sim_val * 100))}% similarity"
                    })
                    connected += 1
                    if connected >= 2:
                        break

            # Sequential adjacent chunks within same document
            if i > 0 and chunk_items[i][0] == chunk_items[i-1][0]:
                c_curr = chunk_items[i][1].get("chunk_index")
                c_prev = chunk_items[i-1][1].get("chunk_index")
                if c_curr is not None and c_prev is not None and abs(c_curr - c_prev) == 1:
                    pair_key = (min(i-1, i), max(i-1, i))
                    if pair_key not in existing_pairs:
                        existing_pairs.add(pair_key)
                        c_id_prev = f"{col_name}-chunk-{chunk_items[i-1][1]['id']}"
                        c_id_curr = f"{col_name}-chunk-{chunk_items[i][1]['id']}"
                        edges.append({
                            "source": c_id_prev,
                            "target": c_id_curr,
                            "type": "sequential",
                            "weight": 0.6,
                            "label": "adjacent chunk"
                        })

    # 4. Document bridge edges
    for bridge in semantic_bridges:
        doc_a = f"doc-{bridge['col_a']}"
        doc_b = f"doc-{bridge['col_b']}"
        if any(n["id"] == doc_a for n in nodes) and any(n["id"] == doc_b for n in nodes):
            sim_pct = round(bridge["similarity"] * 100, 1)
            edges.append({
                "source": doc_a,
                "target": doc_b,
                "type": "bridge",
                "weight": bridge["similarity"],
                "similarity": bridge["similarity"],
                "label": f"{sim_pct}% semantic similarity"
            })

    return {
        "collection_id": collection_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "collections_included": len(set(d.get("collectionId") for d in valid_docs)),
            "bridges_count": len([e for e in edges if e.get("type") == "bridge"])
        }
    }
