# backend/rag_service.py
"""Tier 1 vector retrieval — embed query, cosine search knowledge_chunks."""
from typing import List, Dict, Any
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

_RETRIEVAL_STAGES = {3, 4, 5}
openai_client = AsyncOpenAI()

def should_retrieve_for_stage(arc_stage: int) -> bool:
    return arc_stage in _RETRIEVAL_STAGES

async def embed_query(query: str) -> List[float]:
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small", input=query
    )
    return response.data[0].embedding

async def retrieve(
    query: str,
    scenario_id: str,
    domain: str,
    db: AsyncSession,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Return top_k most similar chunks for query, scoped to scenario + domain."""
    embedding = await embed_query(query)
    # pgvector requires "[x,y,z,...]" literal — str(list) produces spaces which asyncpg rejects
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    result = await db.execute(text("""
        SELECT id, content, section, approved_claim, keywords,
               1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM knowledge_chunks
        WHERE scenario_id = :scenario_id AND domain = :domain
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), {"embedding": embedding_literal, "scenario_id": scenario_id,
           "domain": domain, "top_k": top_k})
    rows = result.fetchall()  # SQLAlchemy CursorResult.fetchall() is synchronous after await execute()
    return [{"id": r.id, "content": r.content, "section": r.section,
             "approved_claim": r.approved_claim, "similarity": r.similarity}
            for r in rows]
