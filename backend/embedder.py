import os
import asyncio
from openai import AsyncOpenAI
from qdrant_client.models import PointStruct
from rank_bm25 import BM25Okapi
from chunker import Chunk
from session_manager import get_session
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 100

async def _embed_batch(texts: list[str]) -> list[list[float]]:
    response = await client.embeddings.create(
        input = texts,
        model = EMBEDDING_MODEL
    )

    return [item.embedding for item in response.data]

async def _embed_all_chunks(chunks: list[Chunk]) -> list[list[float]]:
    texts = [chunk.text for chunk in chunks]
    batches = [texts[i:i+EMBEDDING_BATCH_SIZE] for i in range(0, len(texts), EMBEDDING_BATCH_SIZE)]
    results =  await asyncio.gather(
        *[_embed_batch(batch) for batch in batches]
    )

    flat = [vec for batch in results for vec in batch]
    return flat

def _store_in_qdrant(session_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    session = get_session(session_id) 
    qdrant_client = session["qdrant_client"]
    collection_name = session["collection_name"]

    points = [
        PointStruct(
            id=chunk.chunk_index,
            vector=vectors[i],
            payload={
                "text": chunk.text,
                "source": chunk.source,
                "page_number": chunk.page_number,
                "section_heading": chunk.section_heading,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end
            }
        )
        for i, chunk in enumerate(chunks)
    ]

    for i in range(0, len(points), 256):
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points[i:i+256]
        )

def _build_bm25_index(session_id: str, chunks: list[Chunk]) -> None:
    tokenized = [chunk.text.lower().split() for chunk in chunks]
    bm25_index = BM25Okapi(tokenized)
    
    session = get_session(session_id)
    session["bm25_index"] = bm25_index

def _store_raw_chunks(session_id: str, chunks: list[Chunk]) -> None:
    session = get_session(session_id)
    if session["raw_chunks"] is None:
        session["raw_chunks"] = chunks
    else:
        existing_length = len(session["raw_chunks"])
        for chunk in chunks:
            chunk.chunk_index += existing_length

        session["raw_chunks"].extend(chunks)

async def embed_and_index(session_id: str, chunks: list[Chunk]) -> None:
    vectors = await _embed_all_chunks(chunks)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _store_in_qdrant, session_id, chunks, vectors)

    await loop.run_in_executor(None, _build_bm25_index, session_id, chunks)

    await loop.run_in_executor(None, _store_raw_chunks, session_id, chunks)

