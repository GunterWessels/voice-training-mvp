import pytest, json
from pathlib import Path

def test_validate_cof_map_passes_valid(tmp_path):
    from content_loader import validate_cof_map
    valid = {
        "product": "Test", "clinical_challenge": "a",
        "operational_consequence": "b", "financial_reality": "c",
        "solution_bridge": "d", "cof_connection_statement": "e",
        "quantified_impact": {"clinical": "x", "operational": "y", "financial": "z"}
    }
    assert validate_cof_map(valid) is True

def test_validate_grading_criteria_weights_sum_to_one(tmp_path):
    from content_loader import validate_grading_criteria
    criteria = {"dimensions": [
        {"id": "a", "weight": 0.35, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "b", "weight": 0.25, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "c", "weight": 0.25, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "d", "weight": 0.15, "description": "x", "full": "f", "partial": "p", "none": "n"},
    ], "debrief_instructions": {"tone": "t", "format": "f", "audio": True, "voice": "v"}}
    assert validate_grading_criteria(criteria) is True

def test_validate_grading_criteria_rejects_bad_weights():
    from content_loader import validate_grading_criteria
    criteria = {"dimensions": [
        {"id": "a", "weight": 0.5, "description": "x", "full": "f", "partial": "p", "none": "n"},
        {"id": "b", "weight": 0.8, "description": "x", "full": "f", "partial": "p", "none": "n"},
    ], "debrief_instructions": {"tone": "t", "format": "f", "audio": True, "voice": "v"}}
    assert validate_grading_criteria(criteria) is False
