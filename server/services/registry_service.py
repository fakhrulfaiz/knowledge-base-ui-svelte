import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from server.config import REGISTRY_PATH, DATA_DIR

import colorsys

def get_distinct_color(identifier: str) -> str:
    """Pure dynamic string-to-hex generator across the entire 360° color wheel."""
    if not identifier:
        return "#38bdf8"
    clean_str = identifier.strip().lower()
    h = 0
    for char in clean_str:
        h = ord(char) + ((h << 5) - h)
        h &= 0xFFFFFFFF
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.52, 0.72)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

def initialize_default_registry() -> Dict[str, Any]:
    """Generates initial registry state seeded from live Milvus collections and /data files."""
    initial_collections = [
        {
            "id": "col-networking-100g",
            "name": "100G Networking Technology Overview",
            "collection_name": "networking_100g_overview",
            "description": "High-throughput optical interconnects, PAM-4 modulation, and switch silicon architecture.",
            "scope": "team",
            "teamName": "Hardware & Infrastructure",
            "allocatedGb": 25,
            "createdBy": {"name": "Elena Rostova", "email": "elena.rostova@enterprise.corp"},
            "createdAt": "2026-08-15T09:00:00Z",
            "updatedAt": "2026-09-26T14:20:00Z",
            "tags": ["Networking", "Silicon", "Hardware & Infrastructure"],
            "colorTheme": get_distinct_color("networking_100g_overview")
        },
        {
            "id": "col-cppcon-unwinding",
            "name": "CppCon: Unwinding the Stack (Windows)",
            "collection_name": "cppcon_unwinding_the_stack",
            "description": "James McNellis in-depth breakdown of SEH, C++ exception tables, and stack unwinding on x64.",
            "scope": "team",
            "teamName": "Systems & Architecture",
            "allocatedGb": 20,
            "createdBy": {"name": "Marcus Vance", "email": "marcus.vance@enterprise.corp"},
            "createdAt": "2026-08-20T10:30:00Z",
            "updatedAt": "2026-09-25T11:00:00Z",
            "tags": ["C++", "Windows Internals", "Systems & Architecture"],
            "colorTheme": get_distinct_color("cppcon_unwinding_the_stack")
        },
        {
            "id": "col-db-olap",
            "name": "Database Queries, Data Mining & OLAP",
            "collection_name": "database_queries_data_mining_olap",
            "description": "Multidimensional analysis, star schemas, OLAP cubes, and association rule data mining.",
            "scope": "team",
            "teamName": "Data Science & BI",
            "allocatedGb": 30,
            "createdBy": {"name": "Dr. Soraya Chen", "email": "soraya.chen@enterprise.corp"},
            "createdAt": "2026-08-22T08:00:00Z",
            "updatedAt": "2026-09-24T16:45:00Z",
            "tags": ["OLAP", "Data Mining", "Data Science & BI"],
            "colorTheme": get_distinct_color("database_queries_data_mining_olap")
        },
        {
            "id": "col-cordis-research",
            "name": "CORDIS EU Research & Innovation",
            "collection_name": "cordis_eu_research",
            "description": "European Union scientific framework project deliverables, funding impact, and technology transfer.",
            "scope": "org",
            "teamName": "EU Research",
            "allocatedGb": 50,
            "createdBy": {"name": "Enterprise Governance Council", "email": "council@enterprise.corp"},
            "createdAt": "2026-07-10T12:00:00Z",
            "updatedAt": "2026-09-26T15:10:00Z",
            "tags": ["EU Research", "CORDIS", "Horizon Europe"],
            "colorTheme": get_distinct_color("cordis_eu_research")
        },
        {
            "id": "col-cpp-exceptions-1989",
            "name": "C++ Exception Handling Roots (1989)",
            "collection_name": "cpp_exception_handling_1989",
            "description": "Bjarne Stroustrup and Andrew Koenig historic paper on exception handling design principles.",
            "scope": "project",
            "projectName": "Legacy Compilers",
            "allocatedGb": 15,
            "createdBy": {"name": "Liam Zhang", "email": "liam.zhang@enterprise.corp"},
            "createdAt": "2026-09-01T14:00:00Z",
            "updatedAt": "2026-09-23T09:30:00Z",
            "tags": ["C++", "Language Design", "Compilers"],
            "colorTheme": get_distinct_color("cpp_exception_handling_1989")
        },
        {
            "id": "col-olap-decision-support",
            "name": "OLAP Decision Support Architecture",
            "collection_name": "olap_decision_support_systems",
            "description": "Analytical processing frameworks, DSS integration, and executive business intelligence modeling.",
            "scope": "team",
            "teamName": "Data Science & BI",
            "allocatedGb": 35,
            "createdBy": {"name": "Sarah Jenkins", "email": "sarah.jenkins@enterprise.corp"},
            "createdAt": "2026-09-05T16:00:00Z",
            "updatedAt": "2026-09-25T17:00:00Z",
            "tags": ["OLAP", "Decision Support", "BI"],
            "colorTheme": get_distinct_color("olap_decision_support_systems")
        }
    ]

    initial_documents = [
        {
            "id": "doc-networking-slides",
            "collectionId": "col-networking-100g",
            "collections": ["col-networking-100g", "all_knowledge_base"],
            "title": "100G Networking Technology Overview",
            "filename": "100G Networking Technology Overview - Slides - Toronto (August 2016).pdf",
            "pdfUrl": "http://localhost:8080/data/100G%20Networking%20Technology%20Overview%20-%20Slides%20-%20Toronto%20(August%202016).pdf",
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
            "pdfUrl": "http://localhost:8080/data/2018%20CppCon%20Unwinding%20the%20Stack%20-%20Exploring%20how%20C%2B%2B%20Exceptions%20work%20on%20Windows%20-%20James%20McNellis.pdf",
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
            "pdfUrl": "http://localhost:8080/data/A%20Brief%20Tutorial%20on%20Database%20Queries%2C%20Data%20Mining%2C%20and%20OLAP%20-%202006%20(hamel-197-manuscript-final).pdf",
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
            "pdfUrl": "http://localhost:8080/data/cordis.pdf",
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
            "pdfUrl": "http://localhost:8080/data/except89.pdf",
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
            "pdfUrl": "http://localhost:8080/data/Online_Analytical_Processing_OLAP_for_Decision_Sup.pdf",
            "fileType": "pdf",
            "source": "drive",
            "visibility": "shared",
            "uploadedBy": "Sarah Jenkins",
            "uploadedAt": "2026-09-05T16:10:00Z",
            "status": "indexed"
        }
    ]

    return {
        "collections": initial_collections,
        "documents": initial_documents,
        "pipeline_jobs": []
    }

def load_registry() -> Dict[str, Any]:
    if not os.path.exists(REGISTRY_PATH):
        reg = initialize_default_registry()
        save_registry(reg)
        return reg
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Registry read error, reinitializing: {e}")
        reg = initialize_default_registry()
        save_registry(reg)
        return reg

def save_registry(data: Dict[str, Any]):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_pipeline_job(job_type: str, target: str, status: str, duration_ms: int, details: str):
    reg = load_registry()
    new_job = {
        "id": f"job-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": job_type,
        "target": target,
        "status": status,
        "durationMs": duration_ms,
        "details": details
    }
    reg.setdefault("pipeline_jobs", []).insert(0, new_job)
    reg["pipeline_jobs"] = reg["pipeline_jobs"][:50]
    save_registry(reg)
