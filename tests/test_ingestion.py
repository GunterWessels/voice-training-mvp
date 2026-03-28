import pytest
import yaml
from pathlib import Path


def test_chunk_yaml_file_returns_chunks(tmp_path):
    from ingestion import chunk_yaml_file
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
    from ingestion import chunk_yaml_file
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
    assert len(chunks) == 0
