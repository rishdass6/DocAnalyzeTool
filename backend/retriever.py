import os
import asyncio
from anthropic import AsyncAnthropic
from sentence_transformers import CrossEncoder
from session_manager import get_session

_anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

RETRIEVAL_TOP_K = 100
RRF_K = 60
RERANK_CANDIDATES = 50
FINAL_TOP_N = 15

async def _expand_query(query: str) -> list[str]:
    prompt = (
        "Rewrite the following question into 2 alternative phrasings "
        "that preserve the same meaning but use different vocabulary. "
        "Return ONLY the 2 alternatives, one per line, no numbering, "
        "no explanation.\n\n"
        f"Question: {query}"
    )

    try:
        response = await _anthropic.messages.create(
            model="claude-haiku-4-5",
            max_tokens=80,
            messages=[{"role":"user", "content":prompt}]
        )

        raw = response.content[0].text.strip()
        variants = [line.strip() for line in raw.split("\n") if line.strip()]

        all_queries = [query] + variants[:2]
        return all_queries
    
    except Exception:
        return [query]
    
def _bm25_search(session_id: str, queries: list[str]) -> list[tuple[int, float]]:
    session = get_session(session_id=session_id)
    bm25_index = session.get("bm25_index")

    if bm25_index is None:
        return []
    
    import numpy as np

    all_scores = None
    for query in queries:
        query_tokens = query.lower().split()
        scores = bm25_index.get_scores(query_tokens)
        if all_scores is None:
            all_scores = scores
        else:
            all_scores = np.maximum(all_scores, scores)

    results = [
        (int(i), float(all_scores[i]))
        for i in range(len(all_scores))
        if all_scores[i] > 0
    ]
    results.sort(key=lambda x: x[1], reverse = True)
    return results[:RETRIEVAL_TOP_K]

async def _vector_search(session_id: str, queries: list[str]) -> list[tuple[int, float]]:
    session = get_session(session_id)
    collection_name = session.get("collection_name")
    qdrant_client = session.get("qdrant_client")

    if qdrant_client is None:
        return []
    
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = await openai_client.embeddings.create(
        input = queries,
        model = "text-embedding-3-small"
    )

    vector_query = [item.embedding for item in response.data]

    all_scores: dict[int, float] = {}
    for vector in vector_query:
        hits = qdrant_client.query_points(
            collection_name = collection_name,
            query = vector,
            limit = RETRIEVAL_TOP_K
        ).points

        for hit in hits:
            chunk_id = hit.id
            score = hit.score
            if chunk_id not in all_scores or score > all_scores[chunk_id]:
                all_scores[chunk_id] = score

    results = sorted(all_scores.items(), key = lambda x: x[1], reverse=True)
    return results[:RETRIEVAL_TOP_K]

async def _dual_retrieval(
        session_id: str,
        queries: list[str]
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    async def bm_search():
        return _bm25_search(session_id=session_id, queries=queries)
    
    bm25_results, vector_results = await asyncio.gather(
        bm_search(),
        _vector_search(session_id=session_id, queries=queries)
    )

    return bm25_results, vector_results


def _reciprocal_rank_fusion(
        bm25_results: list[tuple[int, float]],
        vector_results: list[tuple[int, float]]
    ) -> list[tuple[int, float]]:

    rrf_scores: dict[int, float] = {}

    for rank, (chunk_id, _) in enumerate(bm25_results, 1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)

    for rank, (chunk_id, _) in enumerate(vector_results, 1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)

    results = sorted(rrf_scores.items(), key = lambda x: x[1], reverse=True)
    return results[:RERANK_CANDIDATES]

def _rerank(
        query: str,
        candidate_ids: list[int],
        session_id: str
    ) -> list[dict]:
    
    session = get_session(session_id=session_id)
    raw_chunks = session.get("raw_chunks") or []

    if not raw_chunks or not candidate_ids:
        return []
    
    pairs = []
    valid_ids = []
    for chunk_id in candidate_ids:
        if chunk_id < len(raw_chunks):
            pairs.append([query, raw_chunks[chunk_id].text])
            valid_ids.append(chunk_id)

    if not pairs:
        return []
    
    scores = _cross_encoder.predict(pairs)

    scored = sorted(
        zip(valid_ids, scores),
        key=lambda x: x[1],
        reverse=True
    )

    top_chunks = []
    for chunk_id, score in scored[:FINAL_TOP_N]:
        chunk = raw_chunks[chunk_id]
        top_chunks.append({
            "text": chunk.text,
            "source": chunk.source,
            "page_number": chunk.page_number,
            "section_heading": chunk.section_heading,
            "chunk_index": chunk.chunk_index,
            "relevance_score": float(score)
        })

    return top_chunks

async def retrieve(query: str, session_id: str) -> list[dict]:
    """
    Main entry point for the retrieval pipeline.
 
    Runs all 4 stages and returns the final list of relevant chunks.
    Called by the chat router in Phase 5.
 
    Args:
        query:      The user's raw question string
        session_id: The session UUID from the request cookie
 
    Returns:
        List of 15-20 chunk dicts, sorted by relevance (most relevant first).
        Each dict has: text, source, page_number, section_heading,
                       chunk_index, relevance_score.
        Returns empty list if session has no indexed documents.
    """
    # Guard: if no documents are indexed yet, return immediately
    session = get_session(session_id)
    if not session or not session.get("raw_chunks"):
        return []
 
    # Stage 1: Expand the query into variants
    queries = await _expand_query(query)
 
    # Stage 2: Run BM25 and vector search in parallel
    bm25_results, vector_results = await _dual_retrieval(session_id, queries)
 
    # Guard: if both searches returned nothing, stop here
    if not bm25_results and not vector_results:
        return []
 
    # Stage 3: Fuse the two ranked lists with RRF
    rrf_candidates = _reciprocal_rank_fusion(bm25_results, vector_results)
    candidate_ids = [chunk_id for chunk_id, _ in rrf_candidates]
 
    # Stage 4: Rerank top candidates with the cross-encoder
    # Run in thread pool because _rerank is synchronous (CPU-bound)
    loop = asyncio.get_event_loop()
    final_chunks = await loop.run_in_executor(
        None,           # uses the default thread pool executor
        _rerank,
        query,          # original query (not variants) for reranking
        candidate_ids,
        session_id
    )
 
    return final_chunks
