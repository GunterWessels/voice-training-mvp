# tests/test_rag_models.py
def test_knowledge_chunk_model_has_required_fields():
    from models import KnowledgeChunk  # short path — consistent with conftest
    cols = {c.name for c in KnowledgeChunk.__table__.columns}
    assert {"id", "scenario_id", "product_id", "domain", "content",
            "approved_claim", "keywords", "embedding"} <= cols

def test_scenario_model_has_rag_columns():
    from models import Scenario  # short path
    cols = {c.name for c in Scenario.__table__.columns}
    assert {"cof_map", "argument_rubrics", "grading_criteria", "methodology"} <= cols
