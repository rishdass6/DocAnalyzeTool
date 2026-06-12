from fastapi import FastAPI, Response, Cookie, status, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from routers.documents import router as documents_router
from fastapi.openapi.utils import get_openapi
from routers.chat import router as chat_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
import asyncio
from limiter import limiter

from session_manager import (
    create_session,
    get_session,
    delete_session,
    cleanup_expired_sessions,
    get_session_count
)

@asynccontextmanager
async def manage_database(app: FastAPI):
    print(f"Starting background task...")
    task = asyncio.create_task(cleanup_expired_sessions())

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="DocChat API",
    version = "0.1.0",
    lifespan=manage_database
)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    error_code = getattr(exc, "error_code", "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": str(exc.detail),
            "detail": {}
        },
    )

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

@app.post("/api/session/create")
async def create(response: Response):
    session_id = create_session()
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=3600,
        secure=False
    )

    return {
        "session_id": session_id,
        "message": "Session created"
    }

@app.delete("/api/session")
async def delete(response: Response, session_id: Optional[str] = Cookie(default=None)):
    # 1. Check if cookie exists
    if session_id is None:
        response.status_code = status.HTTP_400_BAD_REQUEST # Or just 400
        return {"error": "no_session", "message": "No session cookie found"}
    
    # 2. Check if session exists in our state
    existing_session = get_session(session_id)
    if existing_session is None:
        response.status_code = status.HTTP_404_NOT_FOUND # Or just 404
        return {"error": "not_found", "message": "Session not found"}
    
    delete_session(session_id)
    response.delete_cookie("session_id")

    return {"message": "Session deleted!"}

@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "active_sessions": get_session_count(),
        "version": "0.1.0"
    }

@app.get("/api/session/verify")
async def verify_session(session_id: Optional[str] = Cookie(default=None)):
    # session_id is now correctly injected by FastAPI from the parameter list
    result = get_session(session_id)

    if result is None:
        return {"valid": False}
    else:
        return {"valid": True, "session_id": session_id}
    
