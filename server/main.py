#!/usr/bin/env python3
"""
FastAPI Backend Service for Milvus Vector Graph, Ingestion Pipeline & Knowledge Governance.
Directly connects to Milvus standalone (localhost:19530).

Modular Architecture:
- server/config.py: Environment variables and physical paths.
- server/services/:
    - milvus_service.py: MilvusClient and embedding model singletons, BM25 & centroids caches.
    - registry_service.py: Knowledge registry, collections/document metadata, audit jobs.
    - extractor_service.py: PDF text extraction and caching in .extracted/.
    - ingestion_service.py: Chunking, embedding, and indexing into Milvus global collection.
    - document_service.py: Document cascading purge and reference checking.
- server/routes/:
    - health.py: Health check & Milvus connectivity.
    - drive.py: File inventory & raw PDF streaming.
    - pipeline.py: Triggering extraction & ingestion.
    - collections.py: Collection management & document attachment.
    - documents.py: Document details, page chunks & deletion.
    - telemetry.py: Dashboard statistics & top passages.
    - graph.py: Knowledge graph topology & 2D coordinates.
    - search.py: Hybrid vector search & semantic clusters.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.config import DATA_DIR
from server.routes.health import router as health_router
from server.routes.drive import router as drive_router
from server.routes.pipeline import router as pipeline_router
from server.routes.collections import router as collections_router
from server.routes.documents import router as documents_router
from server.routes.telemetry import router as telemetry_router
from server.routes.graph import router as graph_router
from server.routes.search import router as search_router

app = FastAPI(
    title="Milvus Vector Graph & Knowledge Ingestion Engine",
    version="2.4.0",
    description="Production-grade API for Milvus Vector Governance, Graph Exploration & Hybrid Retrieval."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for browser PDF rendering
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Register Modular Routers
app.include_router(health_router)
app.include_router(drive_router)
app.include_router(pipeline_router)
app.include_router(collections_router)
app.include_router(documents_router)
app.include_router(telemetry_router)
app.include_router(graph_router)
app.include_router(search_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8080, reload=True)
