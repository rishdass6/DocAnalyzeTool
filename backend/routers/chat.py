import os
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import StreamingResponse
from session_manager import get_session
from anthropic import AsyncAnthropic
from retriever import retrieve
from prompt_builder import build_prompt
from pydantic import BaseModel, Field
from limiter import limiter

_anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

router = APIRouter()

class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        description="The search query string",
        min_length=1,
        max_length=2000
    )

@router.post("/chat")
@limiter.limit("5/minute")
async def chat(request: Request, body: QueryRequest, session_id: str | None = Cookie(default=None)):
    if not session_id:
        raise HTTPException(status_code=400, detail="No session cookie found")
    session = get_session(session_id=session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Session not found or expired")
    
    if not session.get("raw_chunks"):
        raise HTTPException(status_code=400, detail="No Documents indexed for this session")
    
    chunks = await retrieve(body.query, session_id)

    if not chunks:
        raise HTTPException(status_code=404, detail="No Relevant Chunks Found")
    
    prompt = build_prompt(body.query, chunks)

    async def stream_response():
        async with _anthropic_client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            try:
                async for delta in stream.text_stream:
                    yield f"data: {delta}\n\n"
                    yield "data: DONE\n\n"
            except Exception as e:
                yield f"Error: {e}"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

