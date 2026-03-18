def test_knowledge_chunk_model_has_required_fields():
    from backend.models import KnowledgeChunk
    cols = {c.name for c in KnowledgeChunk.__table__.columns}
    assert {"id", "scenario_id", "product_id", "domain", "content",
            "approved_claim", "keywords", "embedding"} <= cols

def test_scenario_model_has_rag_columns():
    from backend.models import Scenario
    cols = {c.name for c in Scenario.__table__.columns}
    assert {"cof_map", "argument_rubrics", "grading_criteria", "methodology"} <= cols
