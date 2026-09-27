#!/usr/bin/env python3
"""
Ingest except89.pdf into Milvus Standalone.
Title: Exception Handling for C++ (Andrew Koenig & Bjarne Stroustrup, AT&T Bell Labs 1989)
"""

import os
import pypdf
from fastembed import TextEmbedding
from pymilvus import MilvusClient, DataType

MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
MODEL_NAME = "BAAI/bge-small-en-v1.5"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 60

TARGET = {
    "pdf_path": r"e:\Projects\knowledge-base-ui\except89.pdf",
    "collection_name": "cpp_exception_handling_1989",
    "doc_name": "Exception Handling for C++ (Koenig & Stroustrup 1989)",
    "description": "Andrew Koenig and Bjarne Stroustrup AT&T Bell Labs paper on C++ exception handling design and implementation (1989)."
}

def extract_pages(pdf_path: str):
    print(f"[*] Reading PDF: {os.path.basename(pdf_path)}")
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"[*] Found {total_pages} total pages.")

    pages_data = []
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"    [!] Warning: Failed to extract page {idx + 1}: {e}")
            text = ""
            
        text = text.replace('\x00', '')
        text = " ".join(text.split())
        if text.strip():
            pages_data.append({
                "page_number": idx + 1,
                "text": text
            })
    print(f"[*] Extracted clean text from {len(pages_data)} non-empty pages.")
    return pages_data

def chunk_text(pages_data, doc_name: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    global_chunk_idx = 1

    for p in pages_data:
        text = p["text"]
        page_num = p["page_number"]
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
                    "doc_name": doc_name
                })
                global_chunk_idx += 1

            if end >= len(text):
                break
            start += (chunk_size - overlap)

    return chunks

def main():
    print(f"[*] Connecting to Milvus at {MILVUS_URI}...")
    client = MilvusClient(uri=MILVUS_URI)

    print(f"[*] Loading FastEmbed model ({MODEL_NAME})...")
    embedding_model = TextEmbedding(model_name=MODEL_NAME)

    pdf_path = TARGET["pdf_path"]
    collection_name = TARGET["collection_name"]
    doc_name = TARGET["doc_name"]

    pages = extract_pages(pdf_path)
    chunks = chunk_text(pages, doc_name)
    print(f"[*] Total chunks created: {len(chunks)}")

    print(f"[*] Generating {len(chunks)} embeddings with {MODEL_NAME}...")
    texts = [c["text"] for c in chunks]
    vectors = list(embedding_model.embed(texts))
    embedding_dim = len(vectors[0])

    for c, vec in zip(chunks, vectors):
        c["vector"] = vec.tolist()

    if client.has_collection(collection_name=collection_name):
        print(f"[*] Dropping existing collection '{collection_name}'...")
        client.drop_collection(collection_name=collection_name)

    schema = client.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
        description=TARGET["description"]
    )
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="char_count", datatype=DataType.INT64)
    schema.add_field(field_name="doc_name", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=8192)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 64}
    )

    print(f"[*] Creating Milvus collection '{collection_name}'...")
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        client.insert(collection_name=collection_name, data=batch)

    print(f"[*] Flushing and loading collection '{collection_name}'...")
    client.flush(collection_name=collection_name)
    client.load_collection(collection_name=collection_name)

    sample_q = "exception handling in C++ catch throw"
    sample_vec = list(embedding_model.embed([sample_q]))[0].tolist()
    hits = client.search(
        collection_name=collection_name,
        data=[sample_vec],
        limit=2,
        output_fields=["page_number", "chunk_index", "text"]
    )
    top_score = hits[0][0]["distance"] if hits and hits[0] else 0.0
    print(f"[+] Successfully ingested '{collection_name}'! Stored {len(chunks)} chunks (test cosine similarity: {top_score:.4f}).")
    print(f"[*] Milvus collections now: {client.list_collections()}")

if __name__ == "__main__":
    main()
