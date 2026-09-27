import os

MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
GLOBAL_COLLECTION = "all_knowledge_base"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
DATA_DIR = os.path.abspath("data")
EXTRACTED_DIR = os.path.join(DATA_DIR, ".extracted")
REGISTRY_PATH = os.path.join(DATA_DIR, "knowledge_registry.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXTRACTED_DIR, exist_ok=True)
