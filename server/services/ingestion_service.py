import time
from typing import List, Dict, Any
from fastapi import HTTPException
from pymilvus import DataType
from server.config import MODEL_NAME
from server.services.extractor_service import get_extracted_cache, extract_pdf_document
from server.services.milvus_service import get_milvus_client, get_embedding_model, BM25_CACHE, COLLECTION_CENTROIDS
from server.services.registry_service import log_pipeline_job

def chunk_extracted_pages(pages: List[Dict[str, Any]], doc_title: str, chunk_size: int = 500, chunk_overlap: int = 60) -> List[Dict[str, Any]]:
    chunks = []
    global_chunk_idx = 1
    for p in pages:
        text = p["content"]
        page_num = p["pageNumber"]
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_str = text[start:end].strip()
            if len(chunk_str) >= 25:
                chunks.append({
                    "id": global_chunk_idx,
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx,
                    "text": chunk_str,
                    "char_count": len(chunk_str),
                    "doc_name": doc_title
                })
                global_chunk_idx += 1
            if end >= len(text):
                break
            start += (chunk_size - chunk_overlap)
    return chunks

def ingest_document_chunks_to_milvus(
    filename: str,
    target_milvus_collection: str = "all_knowledge_base",
    chunk_size: int = 500,
    chunk_overlap: int = 60
) -> Dict[str, Any]:
    """
    Independent Ingestion Service.
    Loads extracted representation (or runs extractor if missing),
    tokenizes/chunks text, generates 384d BAAI/bge-small embeddings,
    and indexes them into Milvus global collection.
    """
    start_time = time.time()
    extracted = get_extracted_cache(filename)
    if not extracted:
        extracted = extract_pdf_document(filename)

    doc_title = extracted.get("title", filename)
    chunks = chunk_extracted_pages(
        pages=extracted["pages"],
        doc_title=doc_title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    if not chunks:
        raise HTTPException(status_code=400, detail=f"No viable text chunks found in '{filename}' to ingest.")

    # Vectorize with FastEmbed
    model = get_embedding_model()
    texts = [c["text"] for c in chunks]
    vectors = list(model.embed(texts))
    embedding_dim = len(vectors[0])

    for c, vec in zip(chunks, vectors):
        c["vector"] = vec.tolist()
        c["filename"] = filename

    # Milvus Upsert (Always use global collection)
    client = get_milvus_client()
    clean_col_name = "all_knowledge_base"

    if not client.has_collection(collection_name=clean_col_name):
        schema = client.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
            description=f"Global collection for knowledge base"
        )
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="page_number", datatype=DataType.INT64)
        schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
        schema.add_field(field_name="char_count", datatype=DataType.INT64)
        schema.add_field(field_name="doc_name", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="filename", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=8192)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200}
        )
        client.create_collection(
            collection_name=clean_col_name,
            schema=schema,
            index_params=index_params
        )

    # Insert data
    client.insert(collection_name=clean_col_name, data=chunks)
    client.flush(collection_name=clean_col_name)

    # Invalidate BM25 and centroid caches for this collection
    BM25_CACHE.pop(clean_col_name, None)
    COLLECTION_CENTROIDS.pop(clean_col_name, None)

    elapsed_ms = int((time.time() - start_time) * 1000)
    log_pipeline_job(
        job_type="ingest",
        target=f"{filename} -> {clean_col_name}",
        status="completed",
        duration_ms=elapsed_ms,
        details=f"Embedded and indexed {len(chunks)} passages into Milvus collection '{clean_col_name}'."
    )

    return {
        "status": "ingested",
        "filename": filename,
        "collection_name": clean_col_name,
        "chunks_count": len(chunks),
        "embedding_model": MODEL_NAME,
        "embedding_dim": embedding_dim,
        "duration_ms": elapsed_ms
    }
