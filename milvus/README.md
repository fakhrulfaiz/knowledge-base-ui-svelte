# Milvus Standalone & Attu Web UI Setup

This directory contains the Docker Compose environment for Milvus standalone, MinIO, etcd, and Attu v2.4 (the official Milvus Web UI), along with a standalone ingestion pipeline.

---

## 1. Quick Access: Milvus Web UI (Attu v2.4)

- **Web UI URL**: [http://localhost:8000](http://localhost:8000)
- **Attu Version**: `v2.4` (Dedicated and fully compatible with Milvus 2.4.x)
- **Connection Details in Attu**:
  - **Milvus Address**: `milvus-standalone:19530` (pre-filled by default)
  - **Username / Password**: Leave blank (Authentication is disabled by default)
  - Click **Connect** to enter the workspace directly!

---

## 2. Ingested Dataset: 100G Networking Technology Overview

- **Source Document**: `100G Networking Technology Overview - Slides - Toronto (August 2016).pdf`
- **Total Pages Extracted**: 25 pages
- **Chunking Parameters**:
  - **Chunk Size**: `500` characters
  - **Overlap**: `50` characters
- **Total Chunks Stored**: 32 chunks
- **Collection Name**: `networking_100g_overview`
- **Embedding Model**: `BAAI/bge-small-en-v1.5` (FastEmbed ONNX runtime)
- **Vector Dimension**: 384-dimensional dense vectors
- **Index Type**: `HNSW` (`M=16, efConstruction=64`, metric: `COSINE`)

---

## 3. Schema Structure

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INT64` (Primary Key) | Sequential chunk ID |
| `page_number` | `INT64` | Source slide page number (1–25) |
| `chunk_index` | `INT64` | Chunk sequence index |
| `char_count` | `INT64` | Length of chunk text in characters |
| `doc_name` | `VARCHAR(256)` | Document name identifier |
| `text` | `VARCHAR(4096)` | Raw text content of the chunk |
| `vector` | `FLOAT_VECTOR(384)` | 384-dim dense embedding vector |

---

## 4. Re-running the Ingestion Script

To re-extract and re-index the PDF anytime:

```bash
uv run --with pypdf --with pymilvus --with fastembed python milvus/ingest_pdf.py
```

---

## 5. Docker Services Overview

```bash
# Check container status
docker compose -f milvus/docker-compose.yml ps

# View logs
docker compose -f milvus/docker-compose.yml logs -f

# Stop containers
docker compose -f milvus/docker-compose.yml down

# Start containers
docker compose -f milvus/docker-compose.yml up -d
```
