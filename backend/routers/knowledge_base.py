# backend/routers/knowledge_base.py
"""Knowledge Base Manager CRUD endpoints."""
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Optional
import tempfile, os
from auth import require_role
from ingestion import ingest_yaml, embed_text, upsert_chunk
from extractor import extract_text
from db import get_db

router = APIRouter(prefix="/admin/knowledge-base", tags=["knowledge-base"])

# Dependency: require admin role
require_admin = Depends(require_role("admin"))

VALID_DOMAINS = {"product", "clinical", "cof", "objection", "compliance", "stakeholder"}


class ChunkCreate(BaseModel):
    domain: str
    section: Optional[str] = None
    content: str
    approved_claim: bool = False
    keywords: List[str] = []
    source_doc: Optional[str] = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v not in VALID_DOMAINS:
            raise ValueError(f"domain must be one of {VALID_DOMAINS}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()


@router.get("/{product_id}/chunks", dependencies=[Depends(require_role("admin"))])
async def list_chunks(product_id: str, db=Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(
        text(
            "SELECT id, domain, section, approved_claim, content, source_doc, created_at "
            "FROM knowledge_chunks WHERE product_id=:pid ORDER BY domain, section"
        ),
        {"pid": product_id},
    )
    rows = result.fetchall()
    return {"chunks": [dict(r._mapping) for r in rows], "total": len(rows)}


@router.post("/{product_id}/chunks", dependencies=[Depends(require_role("admin"))])
async def add_chunk(
    product_id: str,
    chunk: ChunkCreate,
    scenario_id: Optional[str] = None,
    db=Depends(get_db),
):
    chunk_data = {
        "id": f"{product_id}_{chunk.domain[:2]}_{os.urandom(3).hex()}",
        "product_id": product_id,
        "scenario_ids": [scenario_id] if scenario_id else [],
        "domain": chunk.domain,
        "section": chunk.section,
        "content": chunk.content,
        "source_doc": chunk.source_doc,
        "approved_claim": chunk.approved_claim,
        "keywords": chunk.keywords,
    }
    embedding = await embed_text(chunk.content)
    await upsert_chunk(db, chunk_data, embedding)
    return {"id": chunk_data["id"], "status": "ingested"}


@router.put("/{product_id}/chunks/{chunk_id}", dependencies=[Depends(require_role("admin"))])
async def update_chunk(product_id: str, chunk_id: str, chunk: ChunkCreate, db=Depends(get_db)):
    """Update an existing chunk's content and metadata; re-embeds the content."""
    from sqlalchemy import text

    embedding = await embed_text(chunk.content)
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    await db.execute(
        text("""
            UPDATE knowledge_chunks
            SET domain=:domain, section=:section, content=:content,
                approved_claim=:approved_claim, keywords=:keywords,
                source_doc=:source_doc, embedding=CAST(:embedding AS vector)
            WHERE id=:cid AND product_id=:pid
        """),
        {
            "domain": chunk.domain,
            "section": chunk.section,
            "content": chunk.content,
            "approved_claim": chunk.approved_claim,
            "keywords": chunk.keywords,
            "source_doc": chunk.source_doc,
            "embedding": embedding_literal,
            "cid": chunk_id,
            "pid": product_id,
        },
    )
    await db.commit()
    return {"id": chunk_id, "status": "updated"}


@router.post("/{product_id}/upload", dependencies=[Depends(require_role("admin"))])
async def upload_document(product_id: str, file: UploadFile, db=Depends(get_db)):
    """Upload any file, extract text, return proposed chunks for review."""
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        extracted = extract_text(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not extracted.strip():
        return {
            "proposed_chunks": [],
            "message": "Could not extract readable text from this file. Try a higher-resolution scan or paste content manually.",
        }

    words = extracted.split()
    proposed = []
    for i in range(0, len(words), 400):
        chunk_text = " ".join(words[i : i + 400])
        if chunk_text.strip():
            proposed.append(
                {
                    "content": chunk_text,
                    "source_doc": file.filename,
                    "domain": "product",
                    "section": "",
                    "approved_claim": False,
                    "keywords": [],
                }
            )
    return {"proposed_chunks": proposed, "total": len(proposed)}


@router.delete("/{product_id}/chunks/{chunk_id}", dependencies=[Depends(require_role("admin"))])
async def delete_chunk(product_id: str, chunk_id: str, db=Depends(get_db)):
    from sqlalchemy import text

    await db.execute(
        text("DELETE FROM knowledge_chunks WHERE id=:cid AND product_id=:pid"),
        {"cid": chunk_id, "pid": product_id},
    )
    await db.commit()
    return {"status": "deleted"}


@router.post("/{product_id}/reingest", dependencies=[Depends(require_role("admin"))])
async def reingest_all(product_id: str, db=Depends(get_db)):
    yaml_path = f"content/{product_id}/knowledge_base.yaml"
    stats = await ingest_yaml(yaml_path, db)
    return stats
