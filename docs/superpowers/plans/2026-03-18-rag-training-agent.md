# RAG Training Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 6-domain RAG knowledge layer, per-turn argument evaluator, post-session grading agent, rep hint system, and admin Knowledge Base Manager UI to the LiquidSMARTS™ Voice Training Platform.

**Architecture:** 2-tier hybrid RAG — pgvector semantic search for BSCI-sourced product/clinical docs (Tier 1), deterministic JSONB lookup for LiquidSMARTS™-authored COF maps/rubrics/grading criteria/methodology (Tier 2). Argument evaluator runs deterministic pattern matching first, LLM fallback only when needed. Grading agent fires once post-session.

**Tech Stack:** FastAPI + asyncpg + SQLAlchemy (backend), pgvector (PostgreSQL extension), OpenAI embeddings (text-embedding-3-small), Claude Sonnet (grading), Haiku (argument eval), pdfplumber + python-docx + python-pptx + openpyxl (file extraction), Claude Vision API (images/scanned PDFs), Next.js 15 TypeScript (admin UI), Railway PostgreSQL.

---

## File Map

### New backend files
| File | Responsibility |
|------|---------------|
| `backend/rag_service.py` | Tier 1 vector retrieval — embed query, cosine search knowledge_chunks |
| `backend/argument_evaluator.py` | Per-turn 2-layer evaluation — pattern match + LLM fallback |
| `backend/grading_agent.py` | Post-session grading — Claude Sonnet structured debrief |
| `backend/extractor.py` | Universal file text extraction — all formats, Vision fallback |
| `backend/ingestion.py` | Chunk YAML source file, embed, upsert to knowledge_chunks |
| `backend/content_loader.py` | Load Tier 2 JSONB content from YAML files into scenarios table |
| `backend/routers/knowledge_base.py` | Admin API endpoints for KB Manager (CRUD + ingest) |
| `backend/migrations/002_rag.sql` | pgvector extension, knowledge_chunks table, new scenario/completion columns |
| `scripts/ingest_docs.py` | CLI wrapper: ingest a knowledge_base.yaml or uploaded file |
| `scripts/validate_content.py` | Validate Tier 2 YAML files before loading |
| `scripts/load_content.py` | Load Tier 2 JSONB into scenarios table |

### Modified backend files
| File | What changes |
|------|-------------|
| `backend/requirements.txt` | Add: pgvector, pdfplumber, python-docx, python-pptx, openpyxl, pyyaml, pytesseract |
| `backend/models.py` | Add KnowledgeChunk model; extend Scenario + Completion models |
| `backend/main.py` | Mount knowledge_base router; inject RAG + evaluator into WebSocket handler |
| `backend/arc_engine.py` | Accept evaluator output to update persona instruction per turn |

### New frontend files
| File | Responsibility |
|------|---------------|
| `frontend-next/app/admin/knowledge-base/page.tsx` | KB Manager page — two-tab layout |
| `frontend-next/components/admin/KBUploadTab.tsx` | Tab 1: drag/drop + manual chunk form + chunk review |
| `frontend-next/components/admin/KBManageTab.tsx` | Tab 2: chunks table + edit/delete/re-ingest |
| `frontend-next/components/RepHint.tsx` | In-session hint overlay component |
| `frontend-next/components/GradingDebrief.tsx` | Post-session debrief with dimension scores + audio |
| `frontend-next/tests/KBUpload.test.tsx` | Tests for upload + chunk review flow |
| `frontend-next/tests/RepHint.test.tsx` | Tests for hint throttle rules |
| `frontend-next/tests/GradingDebrief.test.tsx` | Tests for debrief display |

### Modified frontend files
| File | What changes |
|------|-------------|
| `frontend-next/components/VoiceChat.tsx` | Add hint slot; wire grading debrief on session end |
| `frontend-next/components/CofGates.tsx` | Show hint from evaluator output alongside gate status |

---

## Task 1: Database Migration (pgvector + RAG schema)

**Files:**
- Create: `backend/migrations/002_rag.sql`

- [ ] **Step 1: Write the migration**

```sql
-- backend/migrations/002_rag.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id    UUID REFERENCES scenarios(id) ON DELETE CASCADE,
  product_id     TEXT NOT NULL,
  domain         TEXT NOT NULL CHECK (domain IN ('product','clinical','cof','objection','compliance','stakeholder')),
  section        TEXT,
  content        TEXT NOT NULL,
  source_doc     TEXT,
  page           INTEGER,
  approved_claim BOOLEAN DEFAULT FALSE,
  keywords       TEXT[],
  embedding      vector(1536),
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON knowledge_chunks (scenario_id, domain);
CREATE INDEX ON knowledge_chunks (product_id);

ALTER TABLE scenarios
  ADD COLUMN IF NOT EXISTS cof_map          JSONB,
  ADD COLUMN IF NOT EXISTS argument_rubrics JSONB,
  ADD COLUMN IF NOT EXISTS grading_criteria JSONB,
  ADD COLUMN IF NOT EXISTS methodology      JSONB;

ALTER TABLE completions
  ADD COLUMN IF NOT EXISTS dimension_scores JSONB;
```

- [ ] **Step 2: Apply migration**

```bash
cd voice-training-mvp
psql $DATABASE_URL -f backend/migrations/002_rag.sql
```
Expected: `CREATE EXTENSION`, `CREATE TABLE`, `CREATE INDEX x3`, `ALTER TABLE x2`

- [ ] **Step 3: Verify**

```bash
psql $DATABASE_URL -c "\d knowledge_chunks"
psql $DATABASE_URL -c "\d+ scenarios" | grep -E "cof_map|argument_rubrics|grading_criteria|methodology"
psql $DATABASE_URL -c "\d+ completions" | grep dimension_scores
```

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/002_rag.sql
git commit -m "feat(db): pgvector + knowledge_chunks table + RAG JSONB columns"
```

---

## Task 2: Add Dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Update requirements**

```txt
# Add to backend/requirements.txt
pgvector>=0.3.0
pdfplumber>=0.11.0
python-docx>=1.1.0
python-pptx>=1.0.0
openpyxl>=3.1.0
pyyaml>=6.0
anthropic>=0.40.0
```

- [ ] **Step 2: Install**

```bash
pip install -r backend/requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(deps): add RAG + extraction dependencies"
```

---

## Task 3: SQLAlchemy Models

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rag_models.py
def test_knowledge_chunk_model_has_required_fields():
    from backend.models import KnowledgeChunk
    cols = {c.name for c in KnowledgeChunk.__table__.columns}
    assert {"id", "scenario_id", "product_id", "domain", "content",
            "approved_claim", "keywords", "embedding"} <= cols

def test_scenario_model_has_rag_columns():
    from backend.models import Scenario
    cols = {c.name for c in Scenario.__table__.columns}
    assert {"cof_map", "argument_rubrics", "grading_criteria", "methodology"} <= cols
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_rag_models.py -v
```
Expected: `ImportError` or `AssertionError`

- [ ] **Step 3: Add KnowledgeChunk model and extend Scenario/Completion**

In `backend/models.py`, add after existing imports:

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, String

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    scenario_id    = Column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=True)
    product_id     = Column(String, nullable=False)
    domain         = Column(String, nullable=False)
    section        = Column(String)
    content        = Column(Text, nullable=False)
    source_doc     = Column(String)
    page           = Column(Integer)
    approved_claim = Column(Boolean, default=False)
    keywords       = Column(ARRAY(String))
    embedding      = Column(Vector(1536))
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
```

Add to `Scenario` model:
```python
    cof_map          = Column(JSONB)
    argument_rubrics = Column(JSONB)
    grading_criteria = Column(JSONB)
    methodology      = Column(JSONB)
```

Add to `Completion` model:
```python
    dimension_scores = Column(JSONB)
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_rag_models.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/models.py tests/test_rag_models.py
git commit -m "feat(models): KnowledgeChunk model + RAG columns on Scenario/Completion"
```

---

## Task 4: Universal File Extractor

**Files:**
- Create: `backend/extractor.py`
- Create: `tests/test_extractor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_extractor.py
import pytest
from pathlib import Path

def test_extract_txt(tmp_path):
    from backend.extractor import extract_text
    f = tmp_path / "test.txt"
    f.write_text("Hello clinical world.")
    result = extract_text(str(f))
    assert "Hello clinical world." in result

def test_extract_returns_string_for_unknown_type(tmp_path):
    from backend.extractor import extract_text
    f = tmp_path / "test.xyz"
    f.write_bytes(b"some binary data")
    result = extract_text(str(f))
    assert isinstance(result, str)  # never raises, always returns str

def test_extract_empty_returns_empty_string(tmp_path):
    from backend.extractor import extract_text
    f = tmp_path / "empty.txt"
    f.write_text("")
    result = extract_text(str(f))
    assert result == ""
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_extractor.py -v
```

- [ ] **Step 3: Implement extractor**

```python
# backend/extractor.py
"""Universal file text extractor. Never raises — always returns str."""
import os
import subprocess
from pathlib import Path
from typing import Optional

def extract_text(file_path: str) -> str:
    """Extract text from any file. Returns empty string if extraction fails."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return _extract_pdf(file_path)
        elif suffix in (".docx", ".doc"):
            return _extract_docx(file_path)
        elif suffix in (".txt", ".md", ".csv"):
            return path.read_text(errors="replace")
        elif suffix == ".rtf":
            return _extract_rtf(file_path)
        elif suffix in (".pptx", ".ppt"):
            return _extract_pptx(file_path)
        elif suffix in (".xlsx", ".xls"):
            return _extract_xlsx(file_path)
        elif suffix in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"):
            return _extract_image(file_path)
        else:
            # Try UTF-8 read, fall back to Vision
            try:
                text = path.read_text(errors="strict")
                if len(text.strip()) > 20:
                    return text
            except Exception:
                pass
            return _extract_image(file_path)
    except Exception:
        return ""

def _extract_pdf(file_path: str) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            text_parts.append(text)
    full_text = "\n".join(text_parts).strip()
    # If text yield is too low, it's probably a scanned PDF — use Vision
    if len(full_text) < 50 * max(1, len(text_parts)):
        return _extract_image(file_path)
    return full_text

def _extract_docx(file_path: str) -> str:
    from docx import Document
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def _extract_rtf(file_path: str) -> str:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", file_path],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout if result.returncode == 0 else ""

def _extract_pptx(file_path: str) -> str:
    from pptx import Presentation
    prs = Presentation(file_path)
    parts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                parts.append(shape.text)
    return "\n".join(parts)

def _extract_xlsx(file_path: str) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            row_text = " | ".join(str(c) for c in row if c is not None)
            if row_text.strip():
                parts.append(row_text)
    return "\n".join(parts)

def _extract_image(file_path: str) -> str:
    """Use Claude Vision to extract text from image or scanned document."""
    import anthropic, base64
    path = Path(file_path)
    suffix = path.suffix.lower()
    media_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".tiff": "image/tiff", ".tif": "image/tiff",
        ".bmp": "image/bmp", ".webp": "image/webp", ".pdf": "application/pdf",
    }
    media_type = media_map.get(suffix, "image/png")
    with open(file_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [{
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data}
            }, {
                "type": "text",
                "text": "Extract all readable text from this document. Return only the text, preserving section structure."
            }]
        }]
    )
    return response.content[0].text
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_extractor.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/extractor.py tests/test_extractor.py
git commit -m "feat(extractor): universal file text extraction — PDF/DOCX/images/all formats"
```

---

## Task 5: Ingestion Pipeline

**Files:**
- Create: `backend/ingestion.py`
- Create: `scripts/ingest_docs.py`
- Create: `tests/test_ingestion.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ingestion.py
import pytest, yaml
from pathlib import Path

def test_chunk_yaml_file_returns_chunks(tmp_path):
    from backend.ingestion import chunk_yaml_file
    kb = tmp_path / "knowledge_base.yaml"
    kb.write_text("""
product_id: test_product
scenario_ids: []
chunks:
  - id: test_001
    domain: product
    section: indications
    approved_claim: false
    source: test.pdf
    keywords: [test]
    content: |
      This is test content that is long enough to be a valid chunk.
""")
    chunks = chunk_yaml_file(str(kb))
    assert len(chunks) == 1
    assert chunks[0]["id"] == "test_001"
    assert chunks[0]["domain"] == "product"
    assert chunks[0]["approved_claim"] is False

def test_chunk_yaml_rejects_empty_content(tmp_path):
    from backend.ingestion import chunk_yaml_file
    kb = tmp_path / "knowledge_base.yaml"
    kb.write_text("""
product_id: test_product
scenario_ids: []
chunks:
  - id: test_empty
    domain: product
    section: test
    approved_claim: false
    source: test.pdf
    keywords: []
    content: ""
""")
    chunks = chunk_yaml_file(str(kb))
    assert len(chunks) == 0  # empty content chunks are filtered
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_ingestion.py -v
```

- [ ] **Step 3: Implement ingestion pipeline**

**YAML chunk schema** — canonical key names for `knowledge_base.yaml` chunks:
```yaml
chunks:
  - id: tria_p_001          # required, unique per product
    domain: product          # one of: product, clinical, cof, objection, compliance, stakeholder
    section: indications     # free text slug
    approved_claim: true     # true = FDA-cleared verbatim language
    source: Tria_IFU_v2.pdf  # NOTE: YAML uses "source", loader maps to DB column "source_doc"
    keywords: [stent, IFU]
    content: |
      Full chunk text here...
```

```python
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
            "source_doc": chunk.get("source"),  # YAML field is "source"; DB column is "source_doc"
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
    # pgvector requires embedding as "[x,y,z,...]" literal — not Python str([...]) which adds spaces
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
    """Full pipeline: parse YAML → embed → upsert. Returns stats."""
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
```

- [ ] **Step 4: Create CLI script**

> **CLI design note:** The spec's Section 4.2 shows `--product/--scenario/--dir` flags for discovery-mode ingestion of raw uploaded documents. This CLI uses `--file` for direct YAML ingestion, which is the primary workflow: humans author `knowledge_base.yaml`, run this to embed it. The `--product/--scenario/--dir` discovery path is handled by the admin upload API endpoint (Task 11) which extracts raw files and returns proposed chunks for review. These are two distinct workflows; the YAML path is the source-of-truth ingestion route.

```python
#!/usr/bin/env python3
# scripts/ingest_docs.py
"""CLI: ingest a knowledge_base.yaml file into pgvector."""
import asyncio, argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to knowledge_base.yaml")
    args = parser.parse_args()

    from backend.db import get_db
    from backend.ingestion import ingest_yaml

    async for db in get_db():
        stats = await ingest_yaml(args.file, db)
        print(f"Ingested: {stats['ingested']} | Skipped: {stats['skipped']} | Total: {stats['total']}")

asyncio.run(main())
```

- [ ] **Step 5: Run tests to confirm PASS**

```bash
pytest tests/test_ingestion.py -v
```

- [ ] **Step 6: Smoke test ingest of Tria knowledge base**

```bash
python3 scripts/ingest_docs.py --file content/tria_stents/knowledge_base.yaml
```
Expected: `Ingested: 21 | Skipped: 0 | Total: 21`

- [ ] **Step 7: Commit**

```bash
git add backend/ingestion.py scripts/ingest_docs.py tests/test_ingestion.py
git commit -m "feat(ingestion): YAML chunk pipeline — parse, embed, upsert to pgvector"
```

---

## Task 6: Tier 2 Content Loader

**Files:**
- Create: `backend/content_loader.py`
- Create: `scripts/validate_content.py`
- Create: `scripts/load_content.py`
- Create: `tests/test_content_loader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_content_loader.py
import pytest, json
from pathlib import Path

def test_validate_cof_map_passes_valid(tmp_path):
    from backend.content_loader import validate_cof_map
    valid = {
        "product": "Test", "clinical_challenge": "a",
        "operational_consequence": "b", "financial_reality": "c",
        "solution_bridge": "d", "cof_connection_statement": "e",
        "quantified_impact": {"clinical": "x", "operational": "y", "financial": "z"}
    }
    assert validate_cof_map(valid) is True

def test_validate_grading_criteria_weights_sum_to_one(tmp_path):
    from backend.content_loader import validate_grading_criteria
    criteria = {"dimensions": [
        {"id": "a", "weight": 0.35, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "b", "weight": 0.25, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "c", "weight": 0.25, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "d", "weight": 0.15, "description": "x", "full": "f", "partial": "p", "none": "n"},
    ], "debrief_instructions": {"tone": "t", "format": "f", "audio": True, "voice": "v"}}
    assert validate_grading_criteria(criteria) is True

def test_validate_grading_criteria_rejects_bad_weights():
    from backend.content_loader import validate_grading_criteria
    criteria = {"dimensions": [
        {"id": "a", "weight": 0.5, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "b", "weight": 0.8, "description": "x", "full": "f", "partial": "p", "none": "n"},
    ], "debrief_instructions": {"tone": "t", "format": "f", "audio": True, "voice": "v"}}
    assert validate_grading_criteria(criteria) is False
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_content_loader.py -v
```

- [ ] **Step 3: Implement content_loader**

```python
# backend/content_loader.py
"""Load Tier 2 JSONB content (COF map, rubrics, grading criteria, methodology) into scenarios."""
import yaml
from typing import Any, Dict

def validate_cof_map(data: Dict) -> bool:
    required = {"product","clinical_challenge","operational_consequence",
                "financial_reality","solution_bridge","cof_connection_statement","quantified_impact"}
    return required <= set(data.keys())

def validate_argument_rubrics(data: Dict) -> bool:
    if "stages" not in data or not data["stages"]:
        return False
    for stage in data["stages"]:
        if not all(k in stage for k in ("arc_stage","strong_signals","weak_signals",
                                         "persona_if_strong","persona_if_weak")):
            return False
    return True

def validate_grading_criteria(data: Dict) -> bool:
    if "dimensions" not in data or "debrief_instructions" not in data:
        return False
    total = sum(d.get("weight", 0) for d in data["dimensions"])
    if abs(total - 1.0) > 0.01:  # weights must sum to 1.0 ± 0.01
        return False
    for d in data["dimensions"]:
        if not all(k in d for k in ("id","weight","description","full","partial","none")):
            return False
    return True

def validate_methodology(data: Dict) -> bool:
    return "id" in data and "steps" in data and len(data["steps"]) > 0

async def load_scenario_content(scenario_id: str, content_dir: str, db) -> Dict[str, int]:
    """Load Tier 2 JSONB content files for a scenario into the scenarios table."""
    from pathlib import Path
    from sqlalchemy import text
    base = Path(content_dir)
    updates = {}
    validators = {
        "cof_map": validate_cof_map,
        "argument_rubrics": validate_argument_rubrics,
        "grading_criteria": validate_grading_criteria,
        "methodology": validate_methodology,
    }
    for field, validate_fn in validators.items():
        yaml_path = base / f"{field}.yaml"
        if not yaml_path.exists():
            continue
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        if not validate_fn(data):
            raise ValueError(f"{field}.yaml failed validation")
        updates[field] = data

    if updates:
        set_clause = ", ".join(f"{k} = :{k}::jsonb" for k in updates)
        import json
        params = {"scenario_id": scenario_id}
        params.update({k: json.dumps(v) for k, v in updates.items()})
        await db.execute(
            text(f"UPDATE scenarios SET {set_clause} WHERE id = :scenario_id"),
            params
        )
        await db.commit()
    return {"fields_loaded": len(updates)}
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_content_loader.py -v
```

- [ ] **Step 5: Write CLI scripts**

```python
#!/usr/bin/env python3
# scripts/validate_content.py
"""CLI: validate Tier 2 YAML content files before loading."""
import sys, yaml, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Directory containing cof_map.yaml, argument_rubrics.yaml, etc.")
    args = parser.parse_args()
    from backend.content_loader import validate_cof_map, validate_argument_rubrics, validate_grading_criteria, validate_methodology
    validators = {
        "cof_map.yaml": validate_cof_map,
        "argument_rubrics.yaml": validate_argument_rubrics,
        "grading_criteria.yaml": validate_grading_criteria,
        "methodology.yaml": validate_methodology,
    }
    base = Path(args.dir)
    ok = True
    for fname, fn in validators.items():
        path = base / fname
        if not path.exists():
            print(f"  SKIP  {fname} (not found)")
            continue
        with open(path) as f:
            data = yaml.safe_load(f)
        if fn(data):
            print(f"  OK    {fname}")
        else:
            print(f"  FAIL  {fname}")
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
```

```python
#!/usr/bin/env python3
# scripts/load_content.py
"""CLI: load Tier 2 JSONB content files for a scenario into the scenarios table."""
import asyncio, argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-id", required=True, help="UUID of the scenario to update")
    parser.add_argument("--dir", required=True, help="Directory containing cof_map.yaml etc.")
    args = parser.parse_args()
    from backend.db import get_db
    from backend.content_loader import load_scenario_content
    async for db in get_db():
        result = await load_scenario_content(args.scenario_id, args.dir, db)
        print(f"Loaded {result['fields_loaded']} fields into scenario {args.scenario_id}")

asyncio.run(main())
```

- [ ] **Step 6: Commit**

```bash
git add backend/content_loader.py scripts/validate_content.py scripts/load_content.py tests/test_content_loader.py
git commit -m "feat(content): Tier 2 JSONB content loader + validators + CLI scripts"
```

---

## Task 7: RAG Retrieval Service

**Files:**
- Create: `backend/rag_service.py`
- Create: `tests/test_rag_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rag_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_retrieve_returns_list():
    from backend.rag_service import retrieve
    mock_db = AsyncMock()
    mock_db.execute.return_value.fetchall.return_value = []
    with patch("backend.rag_service.embed_query", return_value=[0.1]*1536):
        results = await retrieve("test query", scenario_id="abc", domain="product", db=mock_db)
    assert isinstance(results, list)

def test_arc_stage_triggers_retrieval():
    from backend.rag_service import should_retrieve_for_stage
    assert should_retrieve_for_stage(1) is False
    assert should_retrieve_for_stage(2) is False
    assert should_retrieve_for_stage(3) is True
    assert should_retrieve_for_stage(4) is True
    assert should_retrieve_for_stage(5) is True
    assert should_retrieve_for_stage(6) is False
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_rag_service.py -v
```

- [ ] **Step 3: Implement rag_service**

```python
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
    rows = result.fetchall()
    return [{"id": r.id, "content": r.content, "section": r.section,
             "approved_claim": r.approved_claim, "similarity": r.similarity}
            for r in rows]
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_rag_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/rag_service.py tests/test_rag_service.py
git commit -m "feat(rag): Tier 1 vector retrieval service with stage-gated triggering"
```

---

## Task 8: Argument Evaluator

**Files:**
- Create: `backend/argument_evaluator.py`
- Create: `tests/test_argument_evaluator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_argument_evaluator.py
import pytest

SAMPLE_RUBRIC_STAGE_3 = {
    "arc_stage": 3, "stage_name": "COF_PROBE",
    "strong_signals": ["connects clinical finding to operational consequence",
                       "quantifies financial impact"],
    "weak_signals": ["leads with price", "features without outcome link"],
    "persona_if_strong": "Become collaborative",
    "persona_if_weak": "Ask about operational impact"
}

def test_detect_strong_signal():
    from backend.argument_evaluator import detect_signals
    text = "When encrustation increases, it directly impacts OR scheduling and throughput"
    strong, weak = detect_signals(text, SAMPLE_RUBRIC_STAGE_3)
    assert len(strong) > 0

def test_detect_weak_signal():
    from backend.argument_evaluator import detect_signals
    text = "Our price is actually competitive and we can discuss pricing options"
    strong, weak = detect_signals(text, SAMPLE_RUBRIC_STAGE_3)
    assert len(weak) > 0

def test_score_delta_strong_is_positive():
    from backend.argument_evaluator import compute_score_delta
    assert compute_score_delta("strong") == 1

def test_score_delta_weak_is_negative():
    from backend.argument_evaluator import compute_score_delta
    assert compute_score_delta("weak") == -1

def test_score_delta_mixed_is_zero():
    from backend.argument_evaluator import compute_score_delta
    assert compute_score_delta("mixed") == 0
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_argument_evaluator.py -v
```

- [ ] **Step 3: Implement argument_evaluator**

```python
# backend/argument_evaluator.py
"""Per-turn 2-layer argument evaluation. Layer 1 deterministic; Layer 2 LLM fallback."""
import re
from typing import Dict, Any, List, Tuple, Optional
import anthropic

# AsyncAnthropic required — evaluate_turn is called from async WebSocket handler
_client = anthropic.AsyncAnthropic()
COF_SEEDS = {
    "clinical":     ["patient","complication","outcome","infection","stent","fragment",
                     "stone","encrustation","urinary","clinical","care","safety","risk"],
    "operational":  ["OR","schedule","throughput","turnover","workflow","procedure",
                     "time","efficiency","volume","capacity","staff","utilization"],
    "financial":    ["cost","budget","revenue","reimbursement","ROI","savings",
                     "expense","margin","price","spend","financial","dollar","investment"],
}

def detect_signals(text: str, rubric_stage: Dict) -> Tuple[List[str], List[str]]:
    """Layer 1: pattern-match text against rubric strong/weak signal phrases."""
    text_lower = text.lower()
    strong = [s for s in rubric_stage.get("strong_signals", [])
              if any(w in text_lower for w in s.lower().split()[:3])]
    weak   = [s for s in rubric_stage.get("weak_signals", [])
              if any(w in text_lower for w in s.lower().split()[:3])]
    return strong, weak

def detect_cof_coverage(text: str) -> Dict[str, bool]:
    text_lower = text.lower()
    return {
        domain: any(term in text_lower for term in terms)
        for domain, terms in COF_SEEDS.items()
    }

def compute_score_delta(quality: str) -> int:
    return {"strong": 1, "mixed": 0, "weak": -1}.get(quality, 0)

async def evaluate_turn(
    rep_text: str,
    arc_stage: int,
    rubric_stage: Dict,
    cof_map: Optional[Dict] = None,
    methodology_step: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Full per-turn evaluation. Returns evaluator output dict."""
    strong, weak = detect_signals(rep_text, rubric_stage)
    cof_coverage = detect_cof_coverage(rep_text)

    # Determine quality from Layer 1
    if strong and not weak:
        quality = "strong"
    elif weak and not strong:
        quality = "weak"
    else:
        quality = "mixed"
        # Layer 2: LLM call only when ambiguous
        if cof_map:
            quality = await _llm_evaluate(rep_text, arc_stage, rubric_stage, cof_map)

    persona_instruction = (
        rubric_stage["persona_if_strong"] if quality == "strong"
        else rubric_stage["persona_if_weak"]
    )

    # Build hint only for weak/mixed
    hint = None
    if quality in ("weak", "mixed") and methodology_step:
        hint = methodology_step.get("hint_if_weak")

    return {
        "arc_stage": arc_stage,
        "strong_signals": strong,
        "weak_signals": weak,
        "argument_quality": quality,
        "cof_coverage": cof_coverage,
        "persona_instruction": persona_instruction,
        "hint_for_rep": hint,
        "score_delta": compute_score_delta(quality),
    }

async def _llm_evaluate(rep_text: str, arc_stage: int,
                        rubric_stage: Dict, cof_map: Dict) -> str:
    """Layer 2: LLM coherence judgment. Returns 'strong', 'mixed', or 'weak'."""
    prompt = f"""Evaluate this sales rep statement at arc stage {arc_stage}.

COF Chain expected: {cof_map.get('cof_connection_statement','')}
Stage rubric strong signals: {rubric_stage['strong_signals']}
Stage rubric weak signals: {rubric_stage['weak_signals']}

Rep statement: "{rep_text}"

Respond with exactly one word: strong, mixed, or weak"""
    # AsyncAnthropic — must await, not block the event loop
    msg = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )
    result = msg.content[0].text.strip().lower()
    return result if result in ("strong", "mixed", "weak") else "mixed"
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_argument_evaluator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/argument_evaluator.py tests/test_argument_evaluator.py
git commit -m "feat(evaluator): 2-layer argument evaluator — pattern match + LLM fallback"
```

---

## Task 9: Grading Agent

**Files:**
- Create: `backend/grading_agent.py`
- Create: `tests/test_grading_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_grading_agent.py
import pytest
from unittest.mock import patch, MagicMock

SAMPLE_CRITERIA = {
    "dimensions": [
        {"id": "cof_coverage", "weight": 0.35, "description": "COF coverage",
         "full": "all 3", "partial": "2 domains", "none": "1 domain"},
        {"id": "discovery_quality", "weight": 0.25, "description": "Discovery",
         "full": "3+ open", "partial": "1-2", "none": "none"},
        {"id": "argument_coherence", "weight": 0.25, "description": "Coherence",
         "full": "full chain", "partial": "partial", "none": "none"},
        {"id": "objection_handling", "weight": 0.15, "description": "Objection",
         "full": "empathize+ask+respond", "partial": "partial", "none": "none"},
    ],
    "debrief_instructions": {"tone": "coaching", "format": "2-3 sentences", "audio": True, "voice": "persona"}
}

def test_build_grading_prompt_contains_transcript():
    from backend.grading_agent import build_grading_prompt
    transcript = [{"speaker": "user", "text": "Hello"}, {"speaker": "ai", "text": "Hi"}]
    prompt = build_grading_prompt(transcript, [], SAMPLE_CRITERIA, {}, {})
    assert "Hello" in prompt
    assert "cof_coverage" in prompt

def test_overall_score_is_weighted_average():
    from backend.grading_agent import compute_overall_score
    dimensions = [
        {"id": "cof_coverage", "score": 80},
        {"id": "discovery_quality", "score": 60},
        {"id": "argument_coherence", "score": 70},
        {"id": "objection_handling", "score": 90},
    ]
    score = compute_overall_score(dimensions, SAMPLE_CRITERIA)
    expected = int(80*0.35 + 60*0.25 + 70*0.25 + 90*0.15)
    assert score == expected
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_grading_agent.py -v
```

- [ ] **Step 3: Implement grading_agent**

```python
# backend/grading_agent.py
"""Post-session grading agent — Claude Sonnet structured debrief."""
import json
from typing import Dict, Any, List
import anthropic

# AsyncAnthropic required — grade_session is called from async WebSocket handler
_client = anthropic.AsyncAnthropic()

def build_grading_prompt(transcript: List[Dict], turn_scores: List[Dict],
                         criteria: Dict, cof_map: Dict, methodology: Dict) -> str:
    transcript_text = "\n".join(
        f"[{t['arc_stage'] if 'arc_stage' in t else '?'}] {t['speaker'].upper()}: {t['text']}"
        for t in transcript
    )
    dims = json.dumps(criteria["dimensions"], indent=2)
    instructions = criteria.get("debrief_instructions", {})
    return f"""You are a sales training coach. Grade this voice training session.

TRANSCRIPT:
{transcript_text}

TURN QUALITY SCORES: {json.dumps(turn_scores)}

GRADING DIMENSIONS:
{dims}

COF CHAIN EXPECTED: {cof_map.get('cof_connection_statement', 'N/A')}

METHODOLOGY: {methodology.get('name', 'Standard')}

Instructions: {instructions.get('tone', '')}. {instructions.get('format', '')}

Return ONLY valid JSON in this exact format:
{{
  "dimensions": [
    {{"id": "cof_coverage", "score": 0-100, "narrative": "2-3 sentences"}},
    {{"id": "discovery_quality", "score": 0-100, "narrative": "2-3 sentences"}},
    {{"id": "argument_coherence", "score": 0-100, "narrative": "2-3 sentences"}},
    {{"id": "objection_handling", "score": 0-100, "narrative": "2-3 sentences"}}
  ],
  "top_strength": "one sentence",
  "top_improvement": "one sentence"
}}"""

def compute_overall_score(dimensions: List[Dict], criteria: Dict) -> int:
    weight_map = {d["id"]: d["weight"] for d in criteria["dimensions"]}
    return int(sum(d["score"] * weight_map.get(d["id"], 0) for d in dimensions))

async def grade_session(
    transcript: List[Dict],
    turn_scores: List[Dict],
    grading_criteria: Dict,
    cof_map: Dict,
    methodology: Dict,
) -> Dict[str, Any]:
    """Run post-session grading. Returns structured debrief dict."""
    prompt = build_grading_prompt(transcript, turn_scores, grading_criteria, cof_map, methodology)
    # AsyncAnthropic — must await to avoid blocking the event loop
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response.content[0].text)
    result["overall_score"] = compute_overall_score(result["dimensions"], grading_criteria)
    result["debrief_audio"] = grading_criteria.get("debrief_instructions", {}).get("audio", True)
    return result
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_grading_agent.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/grading_agent.py tests/test_grading_agent.py
git commit -m "feat(grading): post-session grading agent with weighted dimension debrief"
```

---

## Task 10: Wire Evaluator + RAG into WebSocket Handler

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/arc_engine.py`

> **Integration context:** Before working on this task, read `backend/main.py` and locate: (1) the WebSocket handler function (likely `async def websocket_endpoint` or similar), (2) the `session_context` dict — it is a module-level dict keyed by session_id that stores per-session state, and (3) `current_arc_stage(session_id)` — a function in `backend/arc_engine.py` that returns the integer arc stage (1-6) for the current session. If the arc engine uses a different mechanism (e.g., a class), read `backend/arc_engine.py` first to confirm the API before writing integration code. The snippets below assume the dict-based pattern; adjust if needed.

- [ ] **Step 1: Load Tier 2 content at session start**

In `backend/main.py`, in the session creation / WebSocket connect handler, after fetching the scenario:

```python
# After fetching scenario from DB:
session_context[session_id] = {
    "cof_map": scenario.cof_map or {},
    "argument_rubrics": scenario.argument_rubrics or {"stages": []},
    "grading_criteria": scenario.grading_criteria or {},
    "methodology": scenario.methodology or {},
    "turn_scores": [],
    "transcript": [],
}
```

- [ ] **Step 2: Add per-turn evaluator call**

In the WebSocket message handler, after receiving rep speech:

```python
from backend.argument_evaluator import evaluate_turn
from backend.rag_service import retrieve, should_retrieve_for_stage

ctx = session_context[session_id]
arc_stage = current_arc_stage(session_id)

# Find rubric for current stage
rubric_stage = next(
    (s for s in ctx["argument_rubrics"].get("stages", []) if s["arc_stage"] == arc_stage),
    {}
)
methodology_step = next(
    (s for s in ctx["methodology"].get("steps", []) if s.get("arc_stage") == arc_stage),
    {}
)

eval_result = await evaluate_turn(
    rep_text=user_message,
    arc_stage=arc_stage,
    rubric_stage=rubric_stage,
    cof_map=ctx["cof_map"],
    methodology_step=methodology_step,
)

# Append to turn scores
ctx["turn_scores"].append({
    "arc_stage": arc_stage,
    "quality": eval_result["argument_quality"],
    "score_delta": eval_result["score_delta"],
})

# Tier 1 retrieval if stage warrants it
rag_chunks = []
if should_retrieve_for_stage(arc_stage):
    rag_chunks = await retrieve(
        query=user_message, scenario_id=str(scenario_id),
        domain="clinical", db=db, top_k=3
    )

# Inject persona instruction + RAG context into AI call
extra_context = {
    "persona_instruction": eval_result["persona_instruction"],
    "rag_chunks": [c["content"] for c in rag_chunks],
    "approved_chunks": [c["content"] for c in rag_chunks if c["approved_claim"]],
}
```

- [ ] **Step 3: Send hint to client**

Add to WebSocket response payload when hint exists:

```python
ws_response = {"type": "ai_response", "text": ai_text, "audio_url": audio_url}
if eval_result.get("hint_for_rep"):
    ws_response["hint"] = eval_result["hint_for_rep"]
await websocket.send_json(ws_response)
```

- [ ] **Step 4: Trigger grading on session end**

In session completion handler (after arc stage 6 or clean disconnect):

```python
from backend.grading_agent import grade_session

ctx = session_context.get(session_id, {})
if ctx.get("grading_criteria") and ctx.get("transcript"):
    debrief = await grade_session(
        transcript=ctx["transcript"],
        turn_scores=ctx["turn_scores"],
        grading_criteria=ctx["grading_criteria"],
        cof_map=ctx["cof_map"],
        methodology=ctx["methodology"],
    )
    # Save to completions.dimension_scores
    await db.execute(
        text("UPDATE completions SET dimension_scores = :scores::jsonb WHERE session_id = :sid"),
        {"scores": json.dumps(debrief), "sid": session_id}
    )
    await db.commit()
    # Send debrief to client
    await websocket.send_json({"type": "grading_debrief", "debrief": debrief})
```

- [ ] **Step 5: Run existing test suite to confirm nothing broken**

```bash
pytest tests/ -v --ignore=tests/test_rag_models.py
```
Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/arc_engine.py
git commit -m "feat(ws): wire RAG retrieval + argument evaluator + grading into WebSocket flow"
```

---

## Task 11: Knowledge Base Manager API

**Files:**
- Create: `backend/routers/knowledge_base.py`
- Create: `tests/test_kb_router.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_kb_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# admin_client fixture — provides an authenticated admin AsyncClient
# Adjust the JWT token generation to match your project's auth.py (require_admin checks for admin role in JWT claims)
@pytest.fixture
async def admin_client():
    from backend.main import app
    from backend.auth import create_access_token  # adjust import if function name differs
    token = create_access_token({"sub": "admin-user-id", "role": "admin"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           headers={"Authorization": f"Bearer {token}"}) as ac:
        yield ac

@pytest.mark.asyncio
async def test_list_chunks_requires_admin(client: AsyncClient):
    resp = await client.get("/admin/knowledge-base/tria_stents/chunks")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_add_chunk_validates_domain(admin_client: AsyncClient):
    resp = await admin_client.post("/admin/knowledge-base/tria_stents/chunks", json={
        "domain": "invalid_domain",
        "section": "test",
        "content": "test content",
        "approved_claim": False,
        "keywords": [],
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_kb_router.py -v
```

- [ ] **Step 3: Implement router**

```python
# backend/routers/knowledge_base.py
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Optional
import tempfile, os
from backend.auth import require_admin
from backend.ingestion import ingest_yaml, embed_text, upsert_chunk
from backend.extractor import extract_text
from backend.db import get_db

router = APIRouter(prefix="/admin/knowledge-base", tags=["knowledge-base"])

VALID_DOMAINS = {"product","clinical","cof","objection","compliance","stakeholder"}

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

@router.get("/{product_id}/chunks", dependencies=[Depends(require_admin)])
async def list_chunks(product_id: str, db=Depends(get_db)):
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT id,domain,section,approved_claim,content,source_doc,created_at "
             "FROM knowledge_chunks WHERE product_id=:pid ORDER BY domain,section"),
        {"pid": product_id}
    )
    rows = result.fetchall()
    return {"chunks": [dict(r._mapping) for r in rows], "total": len(rows)}

@router.post("/{product_id}/chunks", dependencies=[Depends(require_admin)])
async def add_chunk(product_id: str, chunk: ChunkCreate,
                    scenario_id: Optional[str] = None, db=Depends(get_db)):
    chunk_data = {
        "id": f"{product_id}_{chunk.domain[:2]}_{os.urandom(3).hex()}",
        "product_id": product_id,
        "scenario_ids": [scenario_id] if scenario_id else [],
        "domain": chunk.domain, "section": chunk.section,
        "content": chunk.content, "source_doc": chunk.source_doc,
        "approved_claim": chunk.approved_claim, "keywords": chunk.keywords,
    }
    embedding = await embed_text(chunk.content)
    await upsert_chunk(db, chunk_data, embedding)
    return {"id": chunk_data["id"], "status": "ingested"}

@router.post("/{product_id}/upload", dependencies=[Depends(require_admin)])
async def upload_document(product_id: str, file: UploadFile, db=Depends(get_db)):
    """Upload any file, extract text, return proposed chunks for review."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        text = extract_text(tmp_path)
    finally:
        os.unlink(tmp_path)
    if not text.strip():
        return {"proposed_chunks": [], "message": "Could not extract readable text from this file. Try a higher-resolution scan or paste content manually."}
    # Split into ~400-word chunks
    words = text.split()
    proposed = []
    for i in range(0, len(words), 400):
        chunk_text = " ".join(words[i:i+400])
        if chunk_text.strip():
            proposed.append({
                "content": chunk_text,
                "source_doc": file.filename,
                "domain": "product",  # default — admin selects in UI
                "section": "",
                "approved_claim": False,
                "keywords": [],
            })
    return {"proposed_chunks": proposed, "total": len(proposed)}

@router.put("/{product_id}/chunks/{chunk_id}", dependencies=[Depends(require_admin)])
async def update_chunk(product_id: str, chunk_id: str, chunk: ChunkCreate, db=Depends(get_db)):
    """Update an existing chunk's content and metadata; re-embeds the content."""
    from sqlalchemy import text
    embedding = await embed_text(chunk.content)
    embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"
    await db.execute(text("""
        UPDATE knowledge_chunks
        SET domain=:domain, section=:section, content=:content,
            approved_claim=:approved_claim, keywords=:keywords,
            source_doc=:source_doc, embedding=CAST(:embedding AS vector)
        WHERE id=:cid AND product_id=:pid
    """), {"domain": chunk.domain, "section": chunk.section, "content": chunk.content,
          "approved_claim": chunk.approved_claim, "keywords": chunk.keywords,
          "source_doc": chunk.source_doc, "embedding": embedding_literal,
          "cid": chunk_id, "pid": product_id})
    await db.commit()
    return {"id": chunk_id, "status": "updated"}

@router.delete("/{product_id}/chunks/{chunk_id}", dependencies=[Depends(require_admin)])
async def delete_chunk(product_id: str, chunk_id: str, db=Depends(get_db)):
    from sqlalchemy import text
    await db.execute(
        text("DELETE FROM knowledge_chunks WHERE id=:cid AND product_id=:pid"),
        {"cid": chunk_id, "pid": product_id}
    )
    await db.commit()
    return {"status": "deleted"}

@router.post("/{product_id}/reingest", dependencies=[Depends(require_admin)])
async def reingest_all(product_id: str, db=Depends(get_db)):
    yaml_path = f"content/{product_id}/knowledge_base.yaml"
    stats = await ingest_yaml(yaml_path, db)
    return stats
```

Register in `backend/main.py`:
```python
from backend.routers.knowledge_base import router as kb_router
app.include_router(kb_router)
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
pytest tests/test_kb_router.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/routers/knowledge_base.py tests/test_kb_router.py backend/main.py
git commit -m "feat(api): Knowledge Base Manager CRUD endpoints — upload/list/add/update/delete/reingest"
```

---

## Task 12: Knowledge Base Manager UI

**Files:**
- Create: `frontend-next/app/admin/knowledge-base/page.tsx`
- Create: `frontend-next/components/admin/KBUploadTab.tsx`
- Create: `frontend-next/components/admin/KBManageTab.tsx`
- Create: `frontend-next/tests/KBUpload.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend-next/tests/KBUpload.test.tsx
import { render, screen } from '@testing-library/react'
import { KBUploadTab } from '@/components/admin/KBUploadTab'

describe('KBUploadTab', () => {
  it('renders drop zone', () => {
    render(<KBUploadTab productId="tria_stents" />)
    expect(screen.getByText(/drop any file/i)).toBeInTheDocument()
  })
  it('shows manual entry form', () => {
    render(<KBUploadTab productId="tria_stents" />)
    expect(screen.getByLabelText(/domain/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/fda-cleared/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
cd frontend-next && npx jest tests/KBUpload.test.tsx
```

- [ ] **Step 3: Build KB page + components**

Create `frontend-next/app/admin/knowledge-base/page.tsx`:
```tsx
'use client'
import { useState } from 'react'
import { KBUploadTab } from '@/components/admin/KBUploadTab'
import { KBManageTab } from '@/components/admin/KBManageTab'

export default function KnowledgeBasePage() {
  const [tab, setTab] = useState<'upload' | 'manage'>('upload')
  const productId = 'tria_stents' // TODO: make dynamic from URL params

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-xl font-semibold mb-6">Knowledge Base — {productId}</h1>
      <div className="border-b border-slate-700 mb-6">
        <div className="flex gap-0">
          {(['upload', 'manage'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? 'border-emerald-500 text-emerald-400'
                          : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
              {t === 'upload' ? 'Upload Doc' : 'Manage Chunks'}
            </button>
          ))}
        </div>
      </div>
      {tab === 'upload' ? <KBUploadTab productId={productId} onIngested={() => setTab('manage')} />
                        : <KBManageTab productId={productId} />}
    </div>
  )
}
```

Create `frontend-next/components/admin/KBUploadTab.tsx`:
```tsx
'use client'
import { useState, useRef } from 'react'

const DOMAINS = ['product','clinical','cof','objection','compliance','stakeholder']

interface Props { productId: string; onIngested?: () => void }

export function KBUploadTab({ productId, onIngested }: Props) {
  const [proposed, setProposed] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const [form, setForm] = useState({ domain: 'product', section: '', content: '', approved_claim: false, keywords: '' })
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    setUploading(true)
    const fd = new FormData(); fd.append('file', file)
    const res = await fetch(`/admin/knowledge-base/${productId}/upload`, { method: 'POST', body: fd })
    const data = await res.json()
    setProposed(data.proposed_chunks || [])
    setUploading(false)
  }

  async function ingestChunk(chunk: any) {
    await fetch(`/admin/knowledge-base/${productId}/chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...chunk, keywords: typeof chunk.keywords === 'string' ? chunk.keywords.split(',').map((k:string)=>k.trim()) : chunk.keywords })
    })
  }

  async function ingestAll() {
    for (const chunk of proposed.filter(c => c._keep !== false)) await ingestChunk(chunk)
    setProposed([])
    onIngested?.()
  }

  async function submitManual(e: React.FormEvent) {
    e.preventDefault()
    await ingestChunk({ ...form, keywords: form.keywords.split(',').map(k=>k.trim()) })
    setForm({ domain: 'product', section: '', content: '', approved_claim: false, keywords: '' })
    onIngested?.()
  }

  return (
    <div className="space-y-6">
      {/* Drop zone */}
      <div onDragOver={e => e.preventDefault()}
           onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if(f) handleFile(f) }}
           className="border-2 border-dashed border-slate-600 rounded-lg p-10 text-center cursor-pointer hover:border-slate-400 transition-colors"
           onClick={() => fileRef.current?.click()}>
        <div className="text-3xl mb-2">📂</div>
        <p className="text-slate-200 font-medium">Drop any file here</p>
        <p className="text-slate-500 text-sm mt-1">PDF · DOCX · TXT · JPG · PNG · TIFF · PPTX · XLSX · RTF · and more</p>
        <input ref={fileRef} type="file" className="hidden" onChange={e => { const f=e.target.files?.[0]; if(f) handleFile(f) }} />
      </div>

      {/* Proposed chunks */}
      {proposed.length > 0 && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-medium text-sm">{proposed.length} chunks proposed — review before ingesting</h3>
            <button onClick={ingestAll} className="bg-emerald-500 text-black text-sm font-semibold px-4 py-1.5 rounded">
              Ingest {proposed.filter(c=>c._keep!==false).length} chunks →
            </button>
          </div>
          {proposed.map((chunk, i) => (
            <div key={i} className={`bg-slate-800 rounded-lg p-4 border ${chunk._keep===false?'opacity-40 border-slate-700':'border-slate-600'}`}>
              <div className="flex gap-3 mb-3 flex-wrap items-center">
                <select value={chunk.domain} onChange={e => { const p=[...proposed]; p[i]={...p[i],domain:e.target.value}; setProposed(p) }}
                  className="bg-slate-700 text-sm rounded px-2 py-1">
                  {DOMAINS.map(d=><option key={d}>{d}</option>)}
                </select>
                <input value={chunk.section||''} placeholder="section"
                  onChange={e => { const p=[...proposed]; p[i]={...p[i],section:e.target.value}; setProposed(p) }}
                  className="bg-slate-700 text-sm rounded px-2 py-1 w-32" />
                <label className="flex items-center gap-2 text-xs text-amber-400">
                  <input type="checkbox" checked={!!chunk.approved_claim}
                    onChange={e => { const p=[...proposed]; p[i]={...p[i],approved_claim:e.target.checked}; setProposed(p) }} />
                  FDA-cleared / approved claim
                </label>
                <span className="ml-auto text-xs text-slate-500">{chunk.content.split(' ').length} words</span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-3">{chunk.content}</p>
              <div className="flex gap-2 mt-3">
                <button onClick={() => { const p=[...proposed]; p[i]={...p[i],_keep:true}; setProposed(p) }}
                  className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded">✓ Keep</button>
                <button onClick={() => { const p=[...proposed]; p[i]={...p[i],_keep:false}; setProposed(p) }}
                  className="text-xs text-red-400 border border-red-400/30 px-3 py-1 rounded">✕ Discard</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Manual entry */}
      <div>
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-slate-800" />
          <span className="text-xs text-slate-600">or add a chunk manually</span>
          <div className="flex-1 h-px bg-slate-800" />
        </div>
        <form onSubmit={submitManual} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-slate-500 block mb-1" htmlFor="domain">Domain</label>
              <select id="domain" value={form.domain} onChange={e=>setForm({...form,domain:e.target.value})}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm">
                {DOMAINS.map(d=><option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Section</label>
              <input value={form.section} onChange={e=>setForm({...form,section:e.target.value})}
                placeholder="e.g. moa, claims" className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm" />
            </div>
            <div className="flex flex-col justify-end">
              <label className="flex items-center gap-2 text-xs text-amber-400 pb-1.5 cursor-pointer" htmlFor="approved">
                <input id="approved" type="checkbox" checked={form.approved_claim}
                  onChange={e=>setForm({...form,approved_claim:e.target.checked})} className="w-3.5 h-3.5" />
                FDA-cleared / approved claim
              </label>
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Keywords (comma-separated)</label>
            <input value={form.keywords} onChange={e=>setForm({...form,keywords:e.target.value})}
              placeholder="encrustation, PercuShield, 59 percent" className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm" />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Content <span className="text-slate-600">(150–400 words)</span></label>
            <textarea value={form.content} onChange={e=>setForm({...form,content:e.target.value})}
              rows={5} className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-2 text-sm resize-y" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={()=>setForm({domain:'product',section:'',content:'',approved_claim:false,keywords:''})}
              className="text-sm text-slate-400 border border-slate-700 px-4 py-1.5 rounded">Clear</button>
            <button type="submit" className="text-sm bg-emerald-500 text-black font-semibold px-4 py-1.5 rounded">
              Add to Knowledge Base + Ingest
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

Create `frontend-next/components/admin/KBManageTab.tsx`:
```tsx
'use client'
import { useEffect, useState } from 'react'

const DOMAIN_COLORS: Record<string,string> = {
  product:'bg-blue-500/15 text-blue-400', clinical:'bg-emerald-500/15 text-emerald-400',
  cof:'bg-amber-500/15 text-amber-400', objection:'bg-purple-500/15 text-purple-400',
  compliance:'bg-red-500/15 text-red-400', stakeholder:'bg-cyan-500/15 text-cyan-400',
}

const DOMAINS = ['product','clinical','cof','objection','compliance','stakeholder']

export function KBManageTab({ productId }: { productId: string }) {
  const [chunks, setChunks] = useState<any[]>([])
  const [editingId, setEditingId] = useState<string|null>(null)
  const [editForm, setEditForm] = useState<any>(null)

  useEffect(() => {
    fetch(`/admin/knowledge-base/${productId}/chunks`)
      .then(r=>r.json()).then(d=>setChunks(d.chunks||[]))
  }, [productId])

  async function deleteChunk(id: string) {
    await fetch(`/admin/knowledge-base/${productId}/chunks/${id}`, { method: 'DELETE' })
    setChunks(c => c.filter(ch => ch.id !== id))
  }

  function startEdit(chunk: any) {
    setEditingId(chunk.id)
    setEditForm({ domain: chunk.domain, section: chunk.section||'', content: chunk.content,
                  approved_claim: chunk.approved_claim, keywords: (chunk.keywords||[]).join(', '), source_doc: chunk.source_doc||'' })
  }

  async function saveEdit(id: string) {
    const payload = { ...editForm, keywords: editForm.keywords.split(',').map((k:string)=>k.trim()).filter(Boolean) }
    const res = await fetch(`/admin/knowledge-base/${productId}/chunks/${id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
    })
    if (res.ok) {
      setChunks(c => c.map(ch => ch.id === id ? {...ch, ...payload} : ch))
      setEditingId(null); setEditForm(null)
    }
  }

  async function reingestAll() {
    await fetch(`/admin/knowledge-base/${productId}/reingest`, { method: 'POST' })
  }

  return (
    <div>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-slate-800/50">
            {['ID','Domain','Section','Approved Claim','Preview','Actions'].map(h=>(
              <th key={h} className="text-left px-3 py-2.5 text-slate-500 border-b border-slate-800 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {chunks.map(chunk => (
            <>
              <tr key={chunk.id} className="border-b border-slate-800/60 hover:bg-slate-800/30">
                <td className="px-3 py-2.5 text-slate-500 font-mono">{chunk.id}</td>
                <td className="px-3 py-2.5">
                  <span className={`px-2 py-0.5 rounded text-xs ${DOMAIN_COLORS[chunk.domain]||''}`}>{chunk.domain}</span>
                </td>
                <td className="px-3 py-2.5 text-slate-400">{chunk.section||'—'}</td>
                <td className="px-3 py-2.5">{chunk.approved_claim ? <span className="text-amber-400">✓ Yes</span> : <span className="text-slate-600">—</span>}</td>
                <td className="px-3 py-2.5 text-slate-500 max-w-xs truncate">{chunk.content?.slice(0,100)}…</td>
                <td className="px-3 py-2.5 flex gap-3">
                  <button onClick={()=>startEdit(chunk)} className="text-blue-400 hover:text-blue-300">Edit</button>
                  <button onClick={()=>deleteChunk(chunk.id)} className="text-red-400 hover:text-red-300">Delete</button>
                </td>
              </tr>
              {editingId === chunk.id && editForm && (
                <tr key={chunk.id+'-edit'} className="bg-slate-800/60 border-b border-slate-700">
                  <td colSpan={6} className="px-4 py-4">
                    <div className="grid grid-cols-3 gap-3 mb-3">
                      <div>
                        <label className="text-xs text-slate-500 block mb-1">Domain</label>
                        <select value={editForm.domain} onChange={e=>setEditForm({...editForm,domain:e.target.value})}
                          className="w-full bg-slate-700 rounded px-2 py-1 text-xs">
                          {DOMAINS.map(d=><option key={d}>{d}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-slate-500 block mb-1">Section</label>
                        <input value={editForm.section} onChange={e=>setEditForm({...editForm,section:e.target.value})}
                          className="w-full bg-slate-700 rounded px-2 py-1 text-xs" />
                      </div>
                      <div className="flex items-end pb-1">
                        <label className="flex items-center gap-2 text-xs text-amber-400 cursor-pointer">
                          <input type="checkbox" checked={editForm.approved_claim}
                            onChange={e=>setEditForm({...editForm,approved_claim:e.target.checked})} />
                          FDA-cleared / approved claim
                        </label>
                      </div>
                    </div>
                    <div className="mb-3">
                      <label className="text-xs text-slate-500 block mb-1">Keywords (comma-separated)</label>
                      <input value={editForm.keywords} onChange={e=>setEditForm({...editForm,keywords:e.target.value})}
                        className="w-full bg-slate-700 rounded px-2 py-1 text-xs" />
                    </div>
                    <div className="mb-3">
                      <label className="text-xs text-slate-500 block mb-1">Content</label>
                      <textarea value={editForm.content} onChange={e=>setEditForm({...editForm,content:e.target.value})}
                        rows={4} className="w-full bg-slate-700 rounded px-2 py-1.5 text-xs resize-y" />
                    </div>
                    <div className="flex gap-2 justify-end">
                      <button onClick={()=>{setEditingId(null);setEditForm(null)}}
                        className="text-xs text-slate-400 border border-slate-700 px-3 py-1 rounded">Cancel</button>
                      <button onClick={()=>saveEdit(chunk.id)}
                        className="text-xs bg-emerald-500 text-black font-semibold px-3 py-1 rounded">Save + Re-embed</button>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
      <div className="flex justify-end mt-4">
        <button onClick={reingestAll} className="text-sm border border-slate-700 text-slate-400 px-4 py-1.5 rounded hover:border-slate-500">
          Re-ingest All
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
cd frontend-next && npx jest tests/KBUpload.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend-next/app/admin/knowledge-base/ frontend-next/components/admin/ frontend-next/tests/KBUpload.test.tsx
git commit -m "feat(ui): Knowledge Base Manager — upload/review/manage chunks in admin dashboard"
```

---

## Task 13: Rep Hint + Grading Debrief UI

**Files:**
- Create: `frontend-next/components/RepHint.tsx`
- Create: `frontend-next/components/GradingDebrief.tsx`
- Modify: `frontend-next/components/VoiceChat.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend-next/tests/RepHint.test.tsx
import { render, screen } from '@testing-library/react'
import { RepHint } from '@/components/RepHint'

it('renders hint text when provided', () => {
  render(<RepHint hint="Try connecting to the financial impact." />)
  expect(screen.getByText(/financial impact/i)).toBeInTheDocument()
})

it('renders nothing when hint is null', () => {
  const { container } = render(<RepHint hint={null} />)
  expect(container.firstChild).toBeNull()
})
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
cd frontend-next && npx jest tests/RepHint.test.tsx
```

- [ ] **Step 3: Build RepHint component**

```tsx
// frontend-next/components/RepHint.tsx
'use client'

interface Props { hint: string | null }

export function RepHint({ hint }: Props) {
  if (!hint) return null
  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 animate-fade-in">
      <div className="bg-slate-800/90 backdrop-blur border border-amber-500/30 text-amber-300 text-sm px-4 py-2.5 rounded-full shadow-lg max-w-sm text-center">
        💡 {hint}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Build GradingDebrief component**

```tsx
// frontend-next/components/GradingDebrief.tsx
'use client'
import { useEffect } from 'react'

interface Dimension { id: string; score: number; narrative: string }
interface Debrief {
  overall_score: number
  dimensions: Dimension[]
  top_strength: string
  top_improvement: string
  debrief_audio: boolean
}
interface Props { debrief: Debrief | null; onDismiss: () => void }

const DIM_LABELS: Record<string,string> = {
  cof_coverage: 'COF Coverage', discovery_quality: 'Discovery',
  argument_coherence: 'Argument Coherence', objection_handling: 'Objection Handling'
}

export function GradingDebrief({ debrief, onDismiss }: Props) {
  if (!debrief) return null
  return (
    <div className="fixed inset-0 bg-black/70 flex items-end justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 space-y-5">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-slate-500 text-xs uppercase tracking-wider mb-1">Session Score</p>
            <p className="text-4xl font-bold text-white">{debrief.overall_score}<span className="text-xl text-slate-500">/100</span></p>
          </div>
          <button onClick={onDismiss} className="text-slate-500 hover:text-white text-xl">✕</button>
        </div>

        <div className="space-y-3">
          {debrief.dimensions.map(dim => (
            <div key={dim.id} className="bg-slate-800 rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-200">{DIM_LABELS[dim.id]||dim.id}</span>
                <span className={`text-sm font-bold ${dim.score>=80?'text-emerald-400':dim.score>=60?'text-amber-400':'text-red-400'}`}>
                  {dim.score}
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-1.5 mb-2">
                <div className={`h-1.5 rounded-full transition-all ${dim.score>=80?'bg-emerald-500':dim.score>=60?'bg-amber-500':'bg-red-500'}`}
                  style={{width:`${dim.score}%`}} />
              </div>
              <p className="text-xs text-slate-400">{dim.narrative}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <p className="text-xs text-emerald-400 font-medium mb-1">Top Strength</p>
            <p className="text-xs text-slate-300">{debrief.top_strength}</p>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
            <p className="text-xs text-amber-400 font-medium mb-1">Top Improvement</p>
            <p className="text-xs text-slate-300">{debrief.top_improvement}</p>
          </div>
        </div>

        <button onClick={onDismiss} className="w-full bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium py-2.5 rounded-lg transition-colors">
          Done
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Wire into VoiceChat**

In `frontend-next/components/VoiceChat.tsx`, add state and handle new WebSocket message types:

```tsx
const [hint, setHint] = useState<string | null>(null)
const [debrief, setDebrief] = useState<any | null>(null)

// In WebSocket onmessage handler, add:
if (data.type === 'ai_response' && data.hint) {
  setHint(data.hint)
  setTimeout(() => setHint(null), 6000) // clear after 6s or next turn
}
if (data.type === 'grading_debrief') {
  setDebrief(data.debrief)
}

// Clear hint on next rep turn:
// In the send message function, add: setHint(null)

// Add to JSX:
// <RepHint hint={hint} />
// <GradingDebrief debrief={debrief} onDismiss={() => setDebrief(null)} />
```

- [ ] **Step 6: Run tests to confirm PASS**

```bash
cd frontend-next && npx jest tests/RepHint.test.tsx tests/GradingDebrief.test.tsx
```

- [ ] **Step 7: Run full test suite**

```bash
cd frontend-next && npx jest
pytest tests/ -v
```
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add frontend-next/components/RepHint.tsx frontend-next/components/GradingDebrief.tsx \
        frontend-next/components/VoiceChat.tsx frontend-next/tests/
git commit -m "feat(ui): RepHint overlay + GradingDebrief post-session panel"
```

---

## Task 14: Deploy to Railway

**Files:**
- Modify: `backend/Dockerfile` (if exists, otherwise Railway auto-detects)

- [ ] **Step 1: Confirm environment variables are set in Railway**

In Railway dashboard, verify these vars exist on the backend service:

```
OPENAI_API_KEY         ← for embeddings + GPT-4o-mini persona responses
ANTHROPIC_API_KEY      ← for Claude Haiku (evaluator) + Claude Sonnet (grading)
DATABASE_URL           ← Railway PostgreSQL (already set)
SUPABASE_URL           ← already set
SUPABASE_ANON_KEY      ← already set
SUPABASE_SERVICE_ROLE_KEY ← already set
ELEVENLABS_API_KEY     ← already set
```

- [ ] **Step 2: Run DB migration on Railway PostgreSQL**

```bash
railway run psql $DATABASE_URL -f backend/migrations/002_rag.sql
```
Expected: `CREATE EXTENSION`, `CREATE TABLE`, `ALTER TABLE x2`

- [ ] **Step 3: Ingest Tria knowledge base into Railway PostgreSQL**

```bash
DATABASE_URL=$(railway variables get DATABASE_URL) \
  python3 scripts/ingest_docs.py --file content/tria_stents/knowledge_base.yaml
```
Expected: `Ingested: 21 | Skipped: 0`

- [ ] **Step 4: Push to main and verify Railway CI/CD**

```bash
git push origin main
```
Watch Railway dashboard — backend + frontend services should rebuild and deploy. Expected: green deploy in ~3-4 minutes.

- [ ] **Step 5: Smoke test production**

```bash
# Check knowledge base endpoint
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://train.liquidsmarts.com/admin/knowledge-base/tria_stents/chunks
# Expected: JSON with 21 chunks

# Check backend health
curl https://train.liquidsmarts.com/health
# Expected: {"status": "ok"}
```

- [ ] **Step 6: Run one Quick Drill session end-to-end**
- Open `https://train.liquidsmarts.com` in browser
- Log in and start a Quick Drill on the Tria VAC scenario
- Speak 3–4 turns
- Verify: hint appears when COF domain missed, grading debrief shows on session end
- Check admin dashboard → Knowledge Base → 21 chunks visible

- [ ] **Step 7: Final commit tag**

```bash
git tag v1.1.0-rag
git push origin v1.1.0-rag
```

---

*LiquidSMARTS™ — Commercial Engineering for Healthcare Technology*
