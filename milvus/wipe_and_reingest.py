import os
import sys
# Add the project root to sys.path so we can import server.main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymilvus import MilvusClient
from server.main import ingest_document_chunks_to_milvus, load_registry, get_milvus_client, DATA_DIR

def main():
    print("Wiping all collections in Milvus...")
    client = get_milvus_client()
    for col in client.list_collections():
        print(f"Dropping {col}...")
        client.drop_collection(collection_name=col)

    print("\nReading registered documents from knowledge_registry.json...")
    reg = load_registry()
    docs = reg.get("documents", [])
    
    unique_pdfs = list(set(d.get("filename") for d in docs if d.get("filename")))
    
    print(f"Found {len(unique_pdfs)} unique PDFs to ingest into global collection.")
    
    for pdf in unique_pdfs:
        pdf_path = os.path.join(DATA_DIR, pdf)
        if not os.path.exists(pdf_path):
            print(f"Skipping {pdf} - file not found in /data/")
            continue
            
        print(f"\nIngesting {pdf} into all_knowledge_base...")
        try:
            res = ingest_document_chunks_to_milvus(filename=pdf, target_milvus_collection="all_knowledge_base")
            print(f"Success! Embedded and indexed {res.get('chunks_ingested')} passages.")
        except Exception as e:
            print(f"Failed to ingest {pdf}: {e}")
            
    print("\nFinished wiping and re-ingesting into the global collection!")

if __name__ == "__main__":
    main()
