import os
import asyncio
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Cookie, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator

from extractor import extract_text, ALLOWED_EXTENSIONS
from chunker import chunk_pages_large
from embedder import embed_and_index
from session_manager import get_session

from limiter import limiter

# STEP 2 — Instantiate the router
router = APIRouter()

# STEP 3 — Helper to save upload to temp file
async def _save_upload_to_temp(file: UploadFile) -> str:
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while chunk := await file.read(8192):
            tmp.write(chunk)
        return tmp.name
    
# STEP 4 — SSE generator function
async def _process_and_stream(session_id: str, files: list[UploadFile]) -> AsyncGenerator[str, None]:
    yield "data: Starting document processing...\n\n"
    all_chunks = []
    
    for i, file in enumerate(files):
        yield f"data: Extracting file {i+1} of {len(files)}: {file.filename}\n\n"
        suffix = Path(file.filename).suffix.lower()
        
        if suffix not in ALLOWED_EXTENSIONS:
            yield f"data: ERROR: {file.filename} is not a supported file type\n\n"
            continue

        if file.size and file.size > 50 * 1024 * 1024:  # 50MB
            yield f"data: ERROR: {file.filename} exceeds the 50MB size limit\n\n"
            continue
            
        tmp_path = None
        try:
            tmp_path = await _save_upload_to_temp(file)
            pages = await extract_text(tmp_path, file.filename)
            yield f"data: Extracted {len(pages)} pages from {file.filename}\n\n"
        except Exception as e:
            yield f"data: ERROR extracting {file.filename}: {str(e)}\n\n"
            continue
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)     
            
        yield f"data: Chunking {file.filename}...\n\n"
        chunks = await chunk_pages_large(pages)
        yield f"data: Created {len(chunks)} chunks from {file.filename}\n\n"
        all_chunks.extend(chunks)
        
    yield "data: Generating embeddings...\n\n"
    if not all_chunks:
        yield "data: ERROR: No chunks were produced from any file\n\n"
        return
    await embed_and_index(session_id, all_chunks)
    yield f"data: DONE: {len(all_chunks)} chunks indexed and ready\n\n"
    yield "data: COMPLETE\n\n"

# STEP 5 — POST /documents/upload endpoint
@router.post("/documents/upload")
@limiter.limit("5/minute")
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    session_id: Optional[str] = Cookie(default=None)
):
    if not session_id:
        raise HTTPException(status_code=400, detail="No session")
        
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
        
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
        
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")
        
    return StreamingResponse(
        _process_and_stream(session_id, files),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

# STEP 6 — GET /documents/status endpoint
@router.get("/documents/status")
async def get_documents_status(
    session_id: Optional[str] = Cookie(default=None)
):
    if not session_id:
        raise HTTPException(status_code=400, detail="No session")
        
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
        
    raw_chunks = session.get("raw_chunks") or []
    sources = list({chunk.source for chunk in raw_chunks})
    
    return {
        "indexed": len(raw_chunks) > 0,
        "chunk_count": len(raw_chunks),
        "sources": sources
    }