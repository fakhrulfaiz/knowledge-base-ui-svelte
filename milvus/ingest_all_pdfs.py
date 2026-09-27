#!/usr/bin/env python3
"""
Multi-PDF Extraction and Milvus Ingestion Script.
Extracts and ingests all PDFs in the workspace into Milvus standalone,
EXCEPT for the 100G Networking Technology Overview PDF (which is already ingested).
"""

import os
import sys
import pypdf
from fastembed import TextEmbedding
from pymilvus import MilvusClient, DataType

MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
MODEL_NAME = "BAAI/bge-small-en-v1.5"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 60

# The target PDFs to ingest (excluding 100G Networking)
PDF_TARGETS = [
    {
        "pdf_path": r"e:\Projects\knowledge-base-ui\2018 CppCon Unwinding the Stack - Exploring how C++ Exceptions work on Windows - James McNellis.pdf",
        "collection_name": "cppcon_unwinding_the_stack",
        "doc_name": "CppCon 2018 - Unwinding the Stack (C++ Exceptions on Windows)",
        "description": "James McNellis presentation on C++ Exception handling and stack unwinding internals on Windows."
    },
    {
        "pdf_path": r"e:\Projects\knowledge-base-ui\A Brief Tutorial on Database Queries, Data Mining, and OLAP - 2006 (hamel-197-manuscript-final).pdf",
        "collection_name": "database_queries_data_mining_olap",
        "doc_name": "A Brief Tutorial on Database Queries, Data Mining, and OLAP",
        "description": "Lutz Hamel tutorial on relational database queries, multidimensional data cubes, and OLAP."
    },
    {
        "pdf_path": r"e:\Projects\knowledge-base-ui\cordis.pdf",
        "collection_name": "cordis_eu_research",
        "doc_name": "CORDIS EU Research & Innovation Project",
        "description": "European Commission CORDIS research and innovation results report."
    },
    {
        "pdf_path": r"e:\Projects\knowledge-base-ui\Online_Analytical_Processing_OLAP_for_Decision_Sup.pdf",
        "collection_name": "olap_decision_support_systems",
        "doc_name": "Online Analytical Processing (OLAP) for Decision Support",
        "description": "Enterprise Decision Support Systems and Online Analytical Processing architecture overview."
    }
]

def extract_pages(pdf_path: str):
    print(f"\n[*] Reading PDF: {os.path.basename(pdf_path)}")
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
            
        # Clean null bytes and consecutive whitespace
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
            
            if len(chunk_str) >= 25: # filter tiny noise
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

def ingest_pdf(client: MilvusClient, embedding_model: TextEmbedding, target: dict):
    pdf_path = target["pdf_path"]
    collection_name = target["collection_name"]
    doc_name = target["doc_name"]

    if not os.path.exists(pdf_path):
        print(f"[!] Error: File does not exist: {pdf_path}")
        return False

    # 1. Extract & Chunk
    pages = extract_pages(pdf_path)
    if not pages:
        print(f"[!] No text found in {pdf_path}")
        return False

    chunks = chunk_text(pages, doc_name)
    print(f"[*] Created {len(chunks)} text chunks.")

    # 2. Generate Dense Embeddings
    print(f"[*] Generating {len(chunks)} embeddings with {MODEL_NAME}...")
    texts = [c["text"] for c in chunks]
    vectors = list(embedding_model.embed(texts))
    embedding_dim = len(vectors[0])

    for c, vec in zip(chunks, vectors):
        c["vector"] = vec.tolist()

    # 3. Create or Recreate Collection in Milvus
    if client.has_collection(collection_name=collection_name):
        print(f"[*] Dropping existing collection '{collection_name}'...")
        client.drop_collection(collection_name=collection_name)

    schema = client.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
        description=target["description"]
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

    # 4. Insert in Batches
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        client.insert(collection_name=collection_name, data=batch)

    # 5. Flush and Load
    print(f"[*] Flushing and loading collection '{collection_name}'...")
    client.flush(collection_name=collection_name)
    client.load_collection(collection_name=collection_name)

    # 6. Verify with a quick test search
    sample_q = chunks[0]["text"][:60]
    sample_vec = list(embedding_model.embed([sample_q]))[0].tolist()
    test_hits = client.search(
        collection_name=collection_name,
        data=[sample_vec],
        limit=1,
        output_fields=["page_number", "chunk_index", "text"]
    )
    score = test_hits[0][0]["distance"] if test_hits and test_hits[0] else 0.0
    print(f"[+] Collection '{collection_name}' ready! {len(chunks)} chunks stored (verification test score: {score:.4f}).")
    return True

def main():
    print(f"[*] Connecting to Milvus at {MILVUS_URI}...")
    client = MilvusClient(uri=MILVUS_URI)

    print(f"[*] Loading FastEmbed model ({MODEL_NAME})...")
    embedding_model = TextEmbedding(model_name=MODEL_NAME)

    success_count = 0
    for target in PDF_TARGETS:
        try:
            ok = ingest_pdf(client, embedding_model, target)
            if ok:
                success_count += 1
        except Exception as e:
            print(f"[!] Error ingesting {target['collection_name']}: {e}")

    print("\n" + "="*60)
    print(f"[COMPLETED] Ingested {success_count}/{len(PDF_TARGETS)} PDFs successfully into Milvus!")
    all_cols = client.list_collections()
    print(f"Total Collections currently in Milvus: {all_cols}")
    print("="*60)

if __name__ == "__main__":
    main()
