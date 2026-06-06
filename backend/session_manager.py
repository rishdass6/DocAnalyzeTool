import uuid
import time
import asyncio

from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
from qdrant_client.models import VectorParams, Distance

sessions: dict[str, dict] = {}
"""
{
    "qdrant_client": QdrantClient(":memory:"),
    "collection_name": str,
    "raw_chunks": list[dict]
    "bm25_index": BM250kapi | None,
    "created_at": float,
    "last_active": float
}
"""

def create_session():
    session_id = str(uuid.uuid4())
    client = QdrantClient(":memory:")

    client.create_collection(
        collection_name=session_id,
        vectors_config = VectorParams(size = 1536, distance = Distance.COSINE)
    )

    session_data = {
        "qdrant_client": client,
        "collection_name": session_id,
        "raw_chunks": None,
        "bm25_index": None,
        "created_at": time.time(),
        "last_active": time.time()
    }

    sessions[session_id] = session_data

    return session_id

def get_session(session_id: str):
    result = sessions.get(session_id)
    if result is None:
        return None
    
    sessions[session_id]["last_active"] = time.time()
    return result

def delete_session(session_id: str):
    session_dict = sessions.get(session_id)
    if session_dict is None:
        return None
    
    client = session_dict.get("qdrant_client")
    client.close()

    del sessions[session_id]

async def cleanup_expired_sessions():
    while True:
        await asyncio.sleep(300)

        now = time.time()
        threshold = 30 * 60
        invalid_sessions = []

        for session_id, session_data in sessions.items():
            if now - session_data["last_active"] > threshold:
                invalid_sessions.append(session_id)

        for session_id in invalid_sessions:
            delete_session(session_id)

def get_session_count():
    return len(sessions)


    