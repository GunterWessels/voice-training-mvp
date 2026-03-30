# backend/rag_service.py
"""Tier 1 vector retrieval — embed query, cosine search knowledge_chunks.

Phase 1 additions:
- session_mode parameter: "certification" adds SQL-level approved_claim / approved filter.
- session_id parameter: enables audit logging to rag_retrievals table.
- Extended return schema includes source_doc, page, manifest_id, approved.
- Every retrieval is logged to rag_retrievals regardless of mode.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
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
    top_k: int = 5,
    session_mode: str = "practice",
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return top_k most similar chunks for query, scoped to scenario + domain.

    session_mode="certification" adds a SQL-level filter:
        kc.approved_claim = true AND rm.approved = true
    using a JOIN to rag_manifest. This is never a prompt instruction — it is
    enforced at the database query level with parameterized SQL.

    Every call logs to rag_retrievals when session_id is provided.

    Returns extended dicts with source_doc, page, manifest_id, approved keys.
    """
    embedding = await embed_query(query)
    # pgvector requires "[x,y,z,...]" literal — str(list) produces spaces which asyncpg rejects
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"

    if session_mode == "certification":
        # Certification mode: must join rag_manifest and filter on both approved flags.
        # NULL manifest_id chunks (pre-Phase 1 admin library) are excluded in cert mode.
        sql = text("""
            SELECT
                kc.id,
                kc.content,
                kc.section,
                kc.source_doc,
                kc.page,
                kc.approved_claim,
                kc.manifest_id,
                rm.approved        AS manifest_approved,
                1 - (kc.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM knowledge_chunks kc
            INNER JOIN rag_manifest rm ON kc.manifest_id = rm.id
            WHERE kc.scenario_id = :scenario_id
              AND kc.domain = :domain
              AND kc.approved_claim = true
              AND rm.approved = true
            ORDER BY kc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
    else:
        # Practice mode: all active chunks for the scenario
        sql = text("""
            SELECT
                kc.id,
                kc.content,
                kc.section,
                kc.source_doc,
                kc.page,
                kc.approved_claim,
                kc.manifest_id,
                COALESCE(rm.approved, false) AS manifest_approved,
                1 - (kc.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM knowledge_chunks kc
            LEFT JOIN rag_manifest rm ON kc.manifest_id = rm.id
            WHERE kc.scenario_id = :scenario_id
              AND kc.domain = :domain
            ORDER BY kc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

    result = await db.execute(sql, {
        "embedding": embedding_literal,
        "scenario_id": scenario_id,
        "domain": domain,
        "top_k": top_k,
    })
    rows = result.fetchall()

    chunks = [
        {
            "id": str(r.id),
            "chunk_id": str(r.id),
            "content": r.content,
            "section": r.section,
            "source_doc": r.source_doc or "",
            "page": r.page,
            "approved_claim": bool(r.approved_claim),
            "approved": bool(r.manifest_approved),
            "manifest_id": str(r.manifest_id) if r.manifest_id else None,
            "similarity": float(r.similarity),
        }
        for r in rows
    ]

    # Audit log: write every retrieval to rag_retrievals (fire and continue)
    if session_id and chunks:
        try:
            await _log_retrievals(
                db=db,
                session_id=session_id,
                chunks=chunks,
                query_text=query,
                session_mode=session_mode,
            )
        except Exception as exc:
            logging.warning("rag_service: failed to log retrievals for session %s: %s", session_id, exc)

    return chunks


async def _log_retrievals(
    db: AsyncSession,
    session_id: str,
    chunks: List[Dict[str, Any]],
    query_text: str,
    session_mode: str,
) -> None:
    """Insert one rag_retrievals row per chunk returned."""
    for chunk in chunks:
        await db.execute(
            text("""
                INSERT INTO rag_retrievals (id, session_id, chunk_id, query_text, session_mode, timestamp)
                VALUES (
                    gen_random_uuid(),
                    :session_id::uuid,
                    :chunk_id::uuid,
                    :query_text,
                    :session_mode::session_mode_enum,
                    NOW()
                )
            """),
            {
                "session_id": session_id,
                "chunk_id": chunk["chunk_id"],
                "query_text": query_text,
                "session_mode": session_mode,
            },
        )
    await db.commit()
