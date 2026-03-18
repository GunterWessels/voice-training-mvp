# backend/ingestion.py
"""Chunk YAML source files and upsert embeddings to knowledge_chunks table."""
import yaml
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

openai_client = AsyncOpenAI()


def chunk_yaml_file(yaml_path: str) -> List[Dict[str, Any]]:
    """Parse a knowledge_base.yaml and return list of chunk dicts. Filters empty content."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    chunks = []
    for chunk in data.get("chunks", []):
        content = (chunk.get("content") or "").strip()
        if not content:
            continue
        chunks.append({
            "id": chunk["id"],
            "product_id": data["product_id"],
            "scenario_ids": data.get("scenario_ids", []),
            "domain": chunk["domain"],
            "section": chunk.get("section"),
            "content": content,
            "source_doc": chunk.get("source"),  # YAML key is "source"; DB column is "source_doc"
            "approved_claim": chunk.get("approved_claim", False),
            "keywords": chunk.get("keywords", []),
        })
    return chunks


async def embed_text(text: str) -> List[float]:
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


async def upsert_chunk(db: AsyncSession, chunk: Dict[str, Any], embedding: List[float]):
    """Insert or replace a knowledge chunk by id."""
    # pgvector requires "[x,y,z,...]" literal -- not Python str([...]) which adds spaces
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    await db.execute(text("""
        INSERT INTO knowledge_chunks
            (id, scenario_id, product_id, domain, section, content,
             source_doc, approved_claim, keywords, embedding)
        VALUES
            (:id, :scenario_id, :product_id, :domain, :section, :content,
             :source_doc, :approved_claim, :keywords, CAST(:embedding AS vector))
        ON CONFLICT (id) DO UPDATE SET
            content=EXCLUDED.content, embedding=EXCLUDED.embedding,
            domain=EXCLUDED.domain, section=EXCLUDED.section,
            approved_claim=EXCLUDED.approved_claim, keywords=EXCLUDED.keywords,
            source_doc=EXCLUDED.source_doc
    """), {**chunk, "scenario_id": chunk["scenario_ids"][0] if chunk["scenario_ids"] else None,
           "embedding": embedding_literal, "keywords": chunk["keywords"]})


async def ingest_yaml(yaml_path: str, db: AsyncSession) -> Dict[str, int]:
    """Full pipeline: parse YAML -> embed -> upsert. Returns stats."""
    chunks = chunk_yaml_file(yaml_path)
    ingested, skipped = 0, 0
    for chunk in chunks:
        try:
            embedding = await embed_text(chunk["content"])
            await upsert_chunk(db, chunk, embedding)
            ingested += 1
        except Exception:
            skipped += 1
    await db.commit()
    return {"ingested": ingested, "skipped": skipped, "total": len(chunks)}
