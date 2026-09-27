import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException
import pypdf
from server.config import DATA_DIR, EXTRACTED_DIR
from server.services.registry_service import log_pipeline_job

def extract_pdf_document(filename: str) -> Dict[str, Any]:
    """
    Independent Extractor Service.
    Parses a PDF file from /data, extracts page-by-page text, cleans noise,
    computes document summaries, page structures, and saves to data/.extracted/.
    DOES NOT perform ingestion or Milvus vectorization.
    """
    start_time = time.time()
    pdf_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF '{filename}' not found in Drive ({DATA_DIR})")

    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pages_data = []
        total_chars = 0

        for idx, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""

            text = text.replace('\x00', '')
            text = " ".join(text.split())
            total_chars += len(text)
            
            pages_data.append({
                "pageNumber": idx + 1,
                "header": f"Page {idx + 1}",
                "content": text,
                "charCount": len(text)
            })

        first_non_empty = next((p["content"] for p in pages_data if p["content"].strip()), "")
        summary = first_non_empty[:280] + "..." if len(first_non_empty) > 280 else (first_non_empty or filename)

        extracted_payload = {
            "filename": filename,
            "title": os.path.splitext(filename)[0].replace("_", " ").title(),
            "fileType": "pdf",
            "sizeBytes": os.path.getsize(pdf_path),
            "pageCount": total_pages,
            "totalChars": total_chars,
            "summary": summary,
            "extractedAt": datetime.now(timezone.utc).isoformat(),
            "extractorVersion": "pypdf-2.4-cleaner",
            "pages": pages_data
        }

        # Cache extracted JSON
        out_json_path = os.path.join(EXTRACTED_DIR, f"{filename}.json")
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(extracted_payload, f, ensure_ascii=False, indent=2)

        elapsed_ms = int((time.time() - start_time) * 1000)
        log_pipeline_job(
            job_type="extract",
            target=filename,
            status="completed",
            duration_ms=elapsed_ms,
            details=f"Extracted {total_pages} pages ({total_chars:,} chars) from '{filename}' into structured text cache."
        )

        return extracted_payload
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        log_pipeline_job(
            job_type="extract",
            target=filename,
            status="failed",
            duration_ms=elapsed_ms,
            details=f"Failed to extract '{filename}': {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Extractor error: {str(e)}")

def get_extracted_cache(filename: str) -> Optional[Dict[str, Any]]:
    cache_path = os.path.join(EXTRACTED_DIR, f"{filename}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None
