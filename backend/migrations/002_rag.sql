-- Voice Training Platform — RAG Schema
-- PostgreSQL 14+ with pgvector
-- Adds knowledge base, embeddings, and RAG-supporting JSONB columns

CREATE EXTENSION IF NOT EXISTS vector;

-- Knowledge Chunks Table (RAG vector store)
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

-- Vector similarity search index (cosine distance)
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Query support indexes
CREATE INDEX idx_knowledge_chunks_scenario ON knowledge_chunks (scenario_id, domain);
CREATE INDEX idx_knowledge_chunks_product ON knowledge_chunks (product_id);

-- Scenarios: Add RAG and grading metadata
ALTER TABLE scenarios
  ADD COLUMN IF NOT EXISTS cof_map          JSONB,
  ADD COLUMN IF NOT EXISTS argument_rubrics JSONB,
  ADD COLUMN IF NOT EXISTS grading_criteria JSONB,
  ADD COLUMN IF NOT EXISTS methodology      JSONB;

-- Completions: Add dimension-specific scoring
ALTER TABLE completions
  ADD COLUMN IF NOT EXISTS dimension_scores JSONB;
