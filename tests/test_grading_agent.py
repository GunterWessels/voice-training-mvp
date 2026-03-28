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
    from grading_agent import build_grading_prompt
    transcript = [{"speaker": "user", "text": "Hello"}, {"speaker": "ai", "text": "Hi"}]
    prompt = build_grading_prompt(transcript, [], SAMPLE_CRITERIA, {}, {})
    assert "Hello" in prompt
    assert "cof_coverage" in prompt

def test_overall_score_is_weighted_average():
    from grading_agent import compute_overall_score
    dimensions = [
        {"id": "cof_coverage", "score": 80},
        {"id": "discovery_quality", "score": 60},
        {"id": "argument_coherence", "score": 70},
        {"id": "objection_handling", "score": 90},
    ]
    score = compute_overall_score(dimensions, SAMPLE_CRITERIA)
    expected = int(80*0.35 + 60*0.25 + 70*0.25 + 90*0.15)
    assert score == expected
