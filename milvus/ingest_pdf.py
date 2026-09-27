#!/usr/bin/env python3
"""
Simple PDF Text Extractor and Milvus Ingestion Script.
Extracts text from the 100G Networking Technology Overview PDF,
chunks into 500-character segments with 50-character overlap,
generates 384-dimensional dense vector embeddings, and stores
them directly in Milvus standalone.
"""

import os
import sys
import pypdf
from fastembed import TextEmbedding
from pymilvus import MilvusClient, DataType

PDF_PATH = r"e:\Projects\knowledge-base-ui\100G Networking Technology Overview - Slides - Toronto (August 2016).pdf"
COLLECTION_NAME = "networking_100g_overview"
MILVUS_URI = "http://localhost:19530"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def extract_pages(pdf_path: str):
    print(f"[*] Reading PDF: {pdf_path}")
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"[*] Found {total_pages} pages.")

    pages_data = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        # Clean up repeated whitespace
        text = " ".join(text.split())
        if text.strip():
            pages_data.append({
                "page_number": idx + 1,
                "text": text
            })
    print(f"[*] Extracted text from {len(pages_data)} non-empty pages.")
    return pages_data

def chunk_text(pages_data, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    print(f"[*] Chunking with size={chunk_size}, overlap={overlap}...")
    chunks = []
    global_chunk_idx = 1

    for p in pages_data:
        text = p["text"]
        page_num = p["page_number"]
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_str = text[start:end].strip()
            
            if len(chunk_str) >= 20: # ignore trivial noise
                chunks.append({
                    "id": global_chunk_idx,
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx,
                    "text": chunk_str,
                    "char_count": len(chunk_str),
                    "doc_name": "100G Networking Technology Overview"
                })
                global_chunk_idx += 1

            if end >= len(text):
                break
            start += (chunk_size - overlap)

    print(f"[*] Generated {len(chunks)} total chunks.")
    return chunks

def main():
    if not os.path.exists(PDF_PATH):
        print(f"[!] Error: File not found: {PDF_PATH}")
        sys.exit(1)

    # 1. Extract and Chunk
    pages_data = extract_pages(PDF_PATH)
    chunks = chunk_text(pages_data)

    # 2. Embed
    print("[*] Initializing embedding model (BAAI/bge-small-en-v1.5, 384-dim)...")
    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    texts = [c["text"] for c in chunks]
    print(f"[*] Computing embeddings for {len(texts)} chunks...")
    vectors = list(embedding_model.embed(texts))
    embedding_dim = len(vectors[0])
    print(f"[*] Embeddings computed. Vector dimension: {embedding_dim}")

    # Attach vectors
    for c, vec in zip(chunks, vectors):
        c["vector"] = vec.tolist()

    # 3. Connect to Milvus
    print(f"[*] Connecting to Milvus at {MILVUS_URI}...")
    client = MilvusClient(uri=MILVUS_URI)

    # Drop existing collection if present
    if client.has_collection(collection_name=COLLECTION_NAME):
        print(f"[*] Removing existing collection '{COLLECTION_NAME}'...")
        client.drop_collection(collection_name=COLLECTION_NAME)

    # 4. Create Collection Schema
    schema = client.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
        description="100G Networking Technology Overview Chunks"
    )
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="char_count", datatype=DataType.INT64)
    schema.add_field(field_name="doc_name", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4096)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

    # 5. Define Index Parameters
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 64}
    )

    print(f"[*] Creating Milvus collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params
    )

    # 6. Insert data
    print(f"[*] Inserting {len(chunks)} chunks into Milvus collection '{COLLECTION_NAME}'...")
    insert_res = client.insert(
        collection_name=COLLECTION_NAME,
        data=chunks
    )
    print(f"[*] Insert result: {insert_res}")

    # Flush data to ensure it is immediately persistent and indexed
    print(f"[*] Flushing collection '{COLLECTION_NAME}'...")
    client.flush(collection_name=COLLECTION_NAME)

    # 7. Load Collection into memory for querying
    client.load_collection(collection_name=COLLECTION_NAME)
    print(f"[+] Collection '{COLLECTION_NAME}' loaded successfully!")

    # 8. Verify with a sample search
    sample_query = "100G optical transceivers and modulation"
    print(f"\n[*] Executing verification search for: '{sample_query}'...")
    query_vec = list(embedding_model.embed([sample_query]))[0].tolist()
    
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_vec],
        limit=3,
        output_fields=["page_number", "chunk_index", "text"]
    )

    print(f"\n=== Verification Search Results (Top {len(results[0])}) ===")
    for rank, hit in enumerate(results[0], 1):
        print(f"\n[Hit #{rank}] Score: {hit['distance']:.4f} | Page: {hit['entity'].get('page_number')}")
        snippet = hit['entity'].get('text', '')[:200]
        print(f"Snippet: {snippet}...")

    # Summary
    stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
    print("\n" + "="*50)
    print(f"[SUCCESS] Milvus Ingestion Complete!")
    print(f" - Collection: {COLLECTION_NAME}")
    print(f" - Stored Entities: {stats.get('row_count', len(chunks))}")
    print(f" - Vector Dimension: {embedding_dim}")
    print(f" - Chunk Size: {CHUNK_SIZE} chars | Overlap: {CHUNK_OVERLAP} chars")
    print(f" - Milvus UI (Attu): http://localhost:8000")
    print("="*50)

if __name__ == "__main__":
    main()
