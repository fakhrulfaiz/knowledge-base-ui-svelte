import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymilvus import MilvusClient, DataType
from fastembed import TextEmbedding
from server.main import (
    load_registry, save_registry, get_milvus_client, get_embedding_model,
    DATA_DIR, EXTRACTED_DIR, REGISTRY_PATH, initialize_default_registry
)

DOC_MAPPINGS = [
    {
        "id": "doc-net-100g",
        "collectionId": "col-networking-100g",
        "collections": ["col-networking-100g", "all_knowledge_base"],
        "title": "100G Networking Technology Overview",
        "filename": "100G Networking Technology Overview - Slides - Toronto (August 2016).pdf",
        "fileType": "pdf",
        "source": "drive",
        "visibility": "shared",
        "uploadedBy": "Elena Rostova",
        "uploadedAt": "2026-08-15T09:05:00Z",
        "status": "indexed"
    },
    {
        "id": "doc-cppcon-seh",
        "collectionId": "col-cppcon-unwinding",
        "collections": ["col-cppcon-unwinding", "all_knowledge_base"],
        "title": "CppCon 2018: Unwinding the Stack on Windows",
        "filename": "2018 CppCon Unwinding the Stack - Exploring how C++ Exceptions work on Windows - James McNellis.pdf",
        "fileType": "pdf",
        "source": "drive",
        "visibility": "shared",
        "uploadedBy": "Marcus Vance",
        "uploadedAt": "2026-08-20T10:35:00Z",
        "status": "indexed"
    },
    {
        "id": "doc-db-mining",
        "collectionId": "col-db-olap",
        "collections": ["col-db-olap", "all_knowledge_base"],
        "title": "Tutorial on Database Queries & OLAP",
        "filename": "A Brief Tutorial on Database Queries, Data Mining, and OLAP - 2006 (hamel-197-manuscript-final).pdf",
        "fileType": "pdf",
        "source": "drive",
        "visibility": "shared",
        "uploadedBy": "Dr. Soraya Chen",
        "uploadedAt": "2026-08-22T08:10:00Z",
        "status": "indexed"
    },
    {
        "id": "doc-cordis-eu",
        "collectionId": "col-cordis-research",
        "collections": ["col-cordis-research", "all_knowledge_base"],
        "title": "CORDIS EU Research & Innovation Report",
        "filename": "cordis.pdf",
        "fileType": "pdf",
        "source": "drive",
        "visibility": "shared",
        "uploadedBy": "Enterprise Governance Council",
        "uploadedAt": "2026-07-10T12:15:00Z",
        "status": "indexed"
    },
    {
        "id": "doc-cpp-spec-89",
        "collectionId": "col-cpp-exceptions-1989",
        "collections": ["col-cpp-exceptions-1989", "all_knowledge_base"],
        "title": "C++ Exception Handling (1989)",
        "filename": "except89.pdf",
        "fileType": "pdf",
        "source": "drive",
        "visibility": "private",
        "uploadedBy": "Liam Zhang",
        "uploadedAt": "2026-09-01T14:20:00Z",
        "status": "indexed"
    },
    {
        "id": "doc-olap-dss",
        "collectionId": "col-olap-decision-support",
        "collections": ["col-olap-decision-support", "all_knowledge_base"],
        "title": "OLAP Decision Support Architecture",
        "filename": "Online_Analytical_Processing_OLAP_for_Decision_Sup.pdf",
        "fileType": "pdf",
        "source": "drive",
        "visibility": "shared",
        "uploadedBy": "Sarah Jenkins",
        "uploadedAt": "2026-09-05T16:10:00Z",
        "status": "indexed"
    }
]

def main():
    print("Re-ingesting all 6 documents into single global Milvus collection: all_knowledge_base...")
    client = get_milvus_client()
    col_name = "all_knowledge_base"

    # Drop existing collection to start clean with proper unique primary key schema
    if client.has_collection(col_name):
        print(f"Dropping collection '{col_name}'...")
        client.drop_collection(col_name)

    schema = client.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
        description="Global Knowledge Base collection for all documents"
    )
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="char_count", datatype=DataType.INT64)
    schema.add_field(field_name="doc_name", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="filename", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=8192)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200}
    )
    client.create_collection(
        collection_name=col_name,
        schema=schema,
        index_params=index_params
    )
    print("Created new 'all_knowledge_base' collection.")

    model = get_embedding_model()
    
    total_ingested = 0
    updated_docs = []

    for doc_idx, doc in enumerate(DOC_MAPPINGS, start=1):
        fname = doc["filename"]
        cached_json = os.path.join(EXTRACTED_DIR, f"{fname}.json")
        if not os.path.exists(cached_json):
            print(f"Extraction cache missing for {fname}, skipping!")
            continue

        with open(cached_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        pages = data.get("pages", [])
        title = doc["title"]
        print(f"\nProcessing [{doc_idx}/6]: {title} ({len(pages)} pages)...")

        # Chunk text
        chunks = []
        chunk_idx = 1
        chunk_size = 500
        chunk_overlap = 60

        for p in pages:
            text = p.get("content", "")
            page_num = p.get("pageNumber", 1)
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_str = text[start:end].strip()
                if len(chunk_str) >= 25:
                    global_id = doc_idx * 100000 + chunk_idx
                    chunks.append({
                        "id": global_id,
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "char_count": len(chunk_str),
                        "doc_name": title,
                        "filename": fname,
                        "text": chunk_str
                    })
                    chunk_idx += 1
                if end >= len(text):
                    break
                start += (chunk_size - chunk_overlap)

        if not chunks:
            print(f"No chunks generated for {fname}")
            continue

        print(f"Embedding {len(chunks)} chunks...")
        texts = [c["text"] for c in chunks]
        vectors = list(model.embed(texts))
        for c, v in zip(chunks, vectors):
            c["vector"] = v.tolist()

        client.insert(collection_name=col_name, data=chunks)
        print(f"Inserted {len(chunks)} chunks into Milvus.")
        total_ingested += len(chunks)

        doc_copy = dict(doc)
        doc_copy["chunkCount"] = len(chunks)
        doc_copy["pdfUrl"] = f"http://localhost:8080/data/{fname}"
        updated_docs.append(doc_copy)

    client.flush(collection_name=col_name)
    print(f"\nFlush complete! Total chunks in Milvus: {total_ingested}")

    # Update knowledge_registry.json
    reg = load_registry()
    reg["documents"] = updated_docs
    save_registry(reg)
    print(f"Updated knowledge_registry.json with {len(updated_docs)} documents.")

if __name__ == "__main__":
    main()
