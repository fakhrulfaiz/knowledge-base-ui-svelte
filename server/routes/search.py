import re
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
from server.config import MODEL_NAME
from server.services.registry_service import load_registry, get_distinct_color
from server.services.milvus_service import get_milvus_client, get_embedding_model, get_collection_bm25

router = APIRouter(tags=["Search"])

class SearchRequest(BaseModel):
    query: str
    collection_name: Optional[str] = "all"
    scope: Optional[str] = "all"
    top_k: int = 15
    search_mode: Optional[str] = "hybrid"

@router.post("/api/search")
def search_vectors(req: SearchRequest):
    """Hybrid Dense Semantic + BM25 Lexical search across Milvus with true semantic clustering."""
    query_str = req.query.strip()
    if not query_str:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    client = get_milvus_client()
    search_mode = (req.search_mode or "hybrid").lower()
    global_col = "all_knowledge_base"

    reg = load_registry()
    docs = reg.get("documents", [])
    raw_collections = reg.get("collections", [])

    # Multi-index collection lookup map (id, name, lowercase name, collection_name slug)
    col_lookup: Dict[str, Any] = {}
    for c in raw_collections:
        cid = c.get("id")
        cname = c.get("name")
        cslug = c.get("collection_name")
        if cid:
            col_lookup[cid] = c
            col_lookup[cid.lower()] = c
        if cname:
            col_lookup[cname] = c
            col_lookup[cname.lower()] = c
        if cslug:
            col_lookup[cslug] = c
            col_lookup[cslug.lower()] = c

    # File to document and collection mapping
    file_to_doc: Dict[str, Any] = {}
    for d in docs:
        fn = d.get("filename")
        if fn:
            file_to_doc[fn] = d

    is_collection_scoped = bool(req.collection_name and req.collection_name not in ["all", "all_knowledge_base", ""])
    is_scope_filtered = bool(req.scope and req.scope != "all")

    filter_docs = []
    target_col = None

    if is_collection_scoped:
        clean_req_col = req.collection_name.strip()
        target_col = col_lookup.get(clean_req_col) or col_lookup.get(clean_req_col.lower())
        if not target_col:
            # Collection name/id does not exist at all -> 0 results
            return {
                "nodes": [],
                "edges": [],
                "results": [],
                "query": query_str,
                "total": 0,
                "stats": {"total_nodes": 0, "total_edges": 0}
            }

        target_col_id = target_col.get("id")
        for d in docs:
            d_col_id = d.get("collectionId")
            d_cols = d.get("collections", [])
            if d_col_id == target_col_id or target_col_id in d_cols:
                if is_scope_filtered and target_col.get("scope", "org") != req.scope:
                    continue
                filter_docs.append(d)

        # If target collection exists but has 0 documents in registry -> 0 results
        if not filter_docs:
            return {
                "nodes": [],
                "edges": [],
                "results": [],
                "query": query_str,
                "total": 0,
                "stats": {"total_nodes": 0, "total_edges": 0}
            }
    elif is_scope_filtered:
        for d in docs:
            c = col_lookup.get(d.get("collectionId"))
            if c and c.get("scope", "org") == req.scope:
                filter_docs.append(d)
        if not filter_docs:
            return {
                "nodes": [],
                "edges": [],
                "results": [],
                "query": query_str,
                "total": 0,
                "stats": {"total_nodes": 0, "total_edges": 0}
            }

    allowed_filenames: Set[str] = set()
    milvus_filter = None
    if is_collection_scoped or is_scope_filtered:
        allowed_filenames = set(d.get("filename") for d in filter_docs if d.get("filename"))
        if not allowed_filenames:
            return {
                "nodes": [],
                "edges": [],
                "results": [],
                "query": query_str,
                "total": 0,
                "stats": {"total_nodes": 0, "total_edges": 0}
            }
        quoted_fns = ", ".join([f'"{fn.replace(chr(34), chr(92)+chr(34))}"' for fn in allowed_filenames])
        milvus_filter = f"filename in [{quoted_fns}]"

    dense_results: Dict[str, Dict[str, Any]] = {}
    query_vec = None
    if search_mode in ["dense", "hybrid"]:
        model = get_embedding_model()
        query_vec = list(model.embed([query_str]))[0].tolist()
        try:
            search_params = {
                "collection_name": global_col,
                "data": [query_vec],
                "limit": max(req.top_k * 4, 40),
                "output_fields": ["id", "page_number", "chunk_index", "text", "char_count", "doc_name", "filename", "vector"]
            }
            if milvus_filter:
                search_params["filter"] = milvus_filter
            search_res = client.search(**search_params)
            if search_res and search_res[0]:
                for hit in search_res[0]:
                    entity = hit.get("entity", {})
                    fn = entity.get("filename")
                    # Strict safety gate against any collection leak
                    if (is_collection_scoped or is_scope_filtered) and fn not in allowed_filenames:
                        continue
                    cid = str(entity.get("id", hit.get("id")))
                    raw_d = float(hit.get("distance", 0.0))
                    d_score = max(0.0, min(1.0, raw_d))
                    key = f"{global_col}_{cid}"
                    dense_results[key] = {
                        "collection_name": global_col,
                        "chunk_id": cid,
                        "dense_score": d_score,
                        "entity": entity,
                        "vector": entity.get("vector")
                    }
        except Exception as e:
            print(f"[!] Error in dense search on {global_col}: {e}")

    bm25_results: Dict[str, Dict[str, Any]] = {}
    q_tokens = re.findall(r"\w+", query_str.lower())
    if search_mode in ["lexical", "hybrid"] and q_tokens:
        bdata = get_collection_bm25(client, global_col)
        if bdata:
            scores = bdata["bm25"].get_scores(q_tokens)
            all_bm25_raw = []
            for idx, raw_s in enumerate(scores):
                if raw_s > 0:
                    chunk = bdata["chunks"][idx]
                    c_fn = chunk.get("filename")
                    # Strict collection gating for lexical BM25
                    if (is_collection_scoped or is_scope_filtered) and c_fn not in allowed_filenames:
                        continue
                    cid = str(chunk.get("id"))
                    key = f"{global_col}_{cid}"
                    raw_val = float(raw_s)
                    all_bm25_raw.append(raw_val)
                    bm25_results[key] = {
                        "collection_name": global_col,
                        "chunk_id": cid,
                        "raw_bm25": raw_val,
                        "entity": chunk,
                        "vector": chunk.get("vector")
                    }

            max_bm25 = max(all_bm25_raw) if all_bm25_raw else 1.0
            for k, v in bm25_results.items():
                v["bm25_score"] = round(min(1.0, v["raw_bm25"] / max_bm25), 4) if max_bm25 > 0 else 0.0

    if search_mode == "dense":
        candidate_keys = set(dense_results.keys())
    elif search_mode == "lexical":
        candidate_keys = set(bm25_results.keys())
    else:
        candidate_keys = set(dense_results.keys()) | set(bm25_results.keys())

    fused_hits = []
    # Relevance Threshold: Filter out false-positive noise when a query is completely out-of-domain
    # for the collection (e.g. searching 'cordis' in collection 'HR' which only has 100G Networking)
    MIN_SCORE_HYBRID = 0.38
    MIN_SCORE_DENSE = 0.40
    MIN_SCORE_LEXICAL = 0.05

    for key in candidate_keys:
        d_item = dense_results.get(key)
        b_item = bm25_results.get(key)

        d_score = d_item["dense_score"] if d_item else 0.0
        b_score = b_item["bm25_score"] if b_item else 0.0

        item_ref = d_item or b_item
        entity = item_ref["entity"]
        fn = entity.get("filename")

        # Post-retrieval verification
        if (is_collection_scoped or is_scope_filtered) and fn not in allowed_filenames:
            continue

        cname = item_ref["collection_name"]
        chunk_id = item_ref["chunk_id"]
        vec = item_ref.get("vector")

        if search_mode == "dense":
            final_score = d_score
            if is_collection_scoped and final_score < MIN_SCORE_DENSE:
                continue
        elif search_mode == "lexical":
            final_score = b_score
            if is_collection_scoped and final_score < MIN_SCORE_LEXICAL:
                continue
        else:
            final_score = 0.6 * d_score + 0.4 * b_score
            # If hybrid search had 0 keyword match and low dense similarity, reject as unrelated noise
            if is_collection_scoped and (final_score < MIN_SCORE_HYBRID or (b_score == 0 and d_score < 0.42)):
                continue

        fused_hits.append({
            "collection_name": cname,
            "chunk_id": chunk_id,
            "score": round(final_score, 4),
            "similarity_pct": int(round(final_score * 100)),
            "dense_score": round(d_score, 4),
            "bm25_score": round(b_score, 4),
            "entity": entity,
            "vector": vec
        })

    fused_hits.sort(key=lambda h: h["score"], reverse=True)
    top_hits = fused_hits[:req.top_k]

    query_node_id = "query-center-node"
    radial_nodes = [
        {
            "id": query_node_id,
            "label": f'"{query_str}"',
            "type": "query",
            "is_center": True,
            "size": 10,
            "color": "#38bdf8",
            "semantic_x": 0.0,
            "semantic_y": 0.0,
            "meta": {
                "title": f"Query: {query_str}",
                "query": query_str,
                "search_mode": search_mode,
                "matches_count": len(top_hits),
                "model": MODEL_NAME,
                "semantic_coords": [0.0, 0.0]
            }
        }
    ]

    radial_edges = []
    formatted_results = []
    hit_vectors = []
    hit_nodes = []

    for rank, hit in enumerate(top_hits, 1):
        entity = hit["entity"]
        doc_name = entity.get("doc_name") or entity.get("filename") or "General"
        doc_color = get_distinct_color(doc_name)
        pdf_file = entity.get("filename") or f"{doc_name}.pdf"

        if target_col:
            actual_col_id = target_col.get("id")
            actual_col_name = target_col.get("name")
        else:
            doc_entry = file_to_doc.get(pdf_file, {})
            actual_col_id = doc_entry.get("collectionId")
            actual_col = col_lookup.get(actual_col_id, {}) if actual_col_id else {}
            actual_col_name = actual_col.get("name") or "General"
            actual_col_id = actual_col.get("id") or actual_col_id or "all_knowledge_base"

        chunk_id = str(entity.get("id", rank))
        page_num = entity.get("page_number", 1)
        chunk_idx = entity.get("chunk_index", rank)
        text = entity.get("text", "")
        char_count = entity.get("char_count", len(text))
        final_score = hit["score"]
        similarity_pct = hit["similarity_pct"]

        vec = hit.get("vector")
        if vec and len(vec) == 384:
            hit_vectors.append(vec)
        elif query_vec:
            hit_vectors.append(query_vec)

        relevance_tier = "High Relevance" if final_score >= 0.70 else "Moderate Relevance" if final_score >= 0.45 else "Related Passage"
        excerpt = text[:220] + "..." if len(text) > 220 else text
        citation = f"{doc_name} — Page {page_num} (Chunk #{chunk_idx})"
        pdf_url = f"http://localhost:8080/data/{pdf_file}#page={page_num}"

        node_id = f"hit-{actual_col_id}-chunk-{chunk_id}"
        node_obj = {
            "id": node_id,
            "label": f"Page {page_num}",
            "type": "chunk",
            "rank": rank,
            "score": final_score,
            "similarity_pct": similarity_pct,
            "collection_id": actual_col_id,
            "collection_name": actual_col_name,
            "doc_name": doc_name,
            "size": 6,
            "color": doc_color,
            "meta": {
                "doc_name": doc_name,
                "collection_id": actual_col_id,
                "collection_name": actual_col_name,
                "page_number": page_num,
                "chunk_index": chunk_idx,
                "char_count": char_count,
                "score": final_score,
                "similarity_pct": similarity_pct,
                "dense_score": hit["dense_score"],
                "bm25_score": hit["bm25_score"],
                "search_mode": search_mode,
                "relevance_tier": relevance_tier,
                "pdf_filename": pdf_file,
                "pdf_url": pdf_url,
                "text": text,
                "excerpt": excerpt,
                "citation": citation
            }
        }
        radial_nodes.append(node_obj)
        hit_nodes.append(node_obj)

        formatted_results.append({
            "rank": rank,
            "chunk_id": chunk_id,
            "collection_id": actual_col_id,
            "collection_name": actual_col_name,
            "doc_name": doc_name,
            "page_number": page_num,
            "chunk_index": chunk_idx,
            "score": final_score,
            "similarity_pct": similarity_pct,
            "dense_score": hit["dense_score"],
            "bm25_score": hit["bm25_score"],
            "search_mode": search_mode,
            "pdf_filename": pdf_file,
            "pdf_url": pdf_url,
            "citation": citation,
            "relevance_tier": relevance_tier,
            "excerpt": excerpt,
            "full_text": text,
            "char_count": char_count
        })

    for rank, h_node in enumerate(hit_nodes):
        if rank < 4 or h_node["score"] >= 0.58:
            radial_edges.append({
                "source": query_node_id,
                "target": h_node["id"],
                "weight": h_node["score"],
                "type": "query_match",
                "label": f"{h_node['similarity_pct']}% Match"
            })

    if len(hit_vectors) >= 2 and len(hit_vectors) == len(hit_nodes):
        vecs_mat = np.array(hit_vectors, dtype=np.float32)
        norms = np.linalg.norm(vecs_mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vecs = vecs_mat / norms
        sim_matrix = np.dot(normalized_vecs, normalized_vecs.T)

        existing_pairs = set()
        for i in range(len(hit_nodes)):
            sims = sim_matrix[i]
            sorted_indices = np.argsort(sims)[::-1]
            connected = 0
            for j in sorted_indices:
                if i == j: continue
                sim_val = float(sims[j])
                if sim_val < 0.65: break
                pair_key = (min(i, j), max(i, j))
                if pair_key not in existing_pairs:
                    existing_pairs.add(pair_key)
                    radial_edges.append({
                        "source": hit_nodes[i]["id"],
                        "target": hit_nodes[j]["id"],
                        "type": "chunk_similarity",
                        "weight": round(sim_val, 3),
                        "similarity": round(sim_val, 3),
                        "label": f"{int(round(sim_val * 100))}% similarity"
                    })
                    connected += 1
                    if connected >= 2: break

            if i > 0 and hit_nodes[i]["doc_name"] == hit_nodes[i-1]["doc_name"]:
                c_curr = hit_nodes[i]["meta"].get("chunk_index")
                c_prev = hit_nodes[i-1]["meta"].get("chunk_index")
                if c_curr and c_prev and abs(c_curr - c_prev) == 1:
                    pair_key = (min(i-1, i), max(i-1, i))
                    if pair_key not in existing_pairs:
                        existing_pairs.add(pair_key)
                        radial_edges.append({
                            "source": hit_nodes[i-1]["id"],
                            "target": hit_nodes[i]["id"],
                            "type": "sequential",
                            "weight": 0.6,
                            "label": "adjacent chunk"
                        })

    if query_vec and len(hit_vectors) >= 2:
        all_vecs = np.array([query_vec] + hit_vectors, dtype=np.float32)
        vecs_centered = all_vecs - np.mean(all_vecs, axis=0)
        U, S, Vt = np.linalg.svd(vecs_centered, full_matrices=False)
        coords_2d = U[:, :2] * S[:2]
        max_dist = float(np.max(np.abs(coords_2d)))
        if max_dist > 1e-6:
            coords_2d /= max_dist

        radial_nodes[0]["semantic_x"] = round(float(coords_2d[0, 0]), 4)
        radial_nodes[0]["semantic_y"] = round(float(coords_2d[0, 1]), 4)
        radial_nodes[0]["meta"]["semantic_coords"] = [radial_nodes[0]["semantic_x"], radial_nodes[0]["semantic_y"]]
        for i, node in enumerate(radial_nodes[1:], start=1):
            node["semantic_x"] = round(float(coords_2d[i, 0]), 4)
            node["semantic_y"] = round(float(coords_2d[i, 1]), 4)
            node["meta"]["semantic_coords"] = [node["semantic_x"], node["semantic_y"]]

    return {
        "query": query_str,
        "collection_name": req.collection_name,
        "search_mode": search_mode,
        "total_hits": len(top_hits),
        "collections_searched": [global_col],
        "graph": {"nodes": radial_nodes, "edges": radial_edges},
        "results": formatted_results
    }
