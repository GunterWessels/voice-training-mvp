import pytest
from backend.arc_engine import ConditionEvaluator, ArcStageTracker

# --- COF Gate Detection ---

def test_clinical_gate_detects_patient_mention():
    history = [{"speaker": "user", "text": "How are patient outcomes affected by stent encrustation?"}]
    ev = ConditionEvaluator()
    assert ev.cof_clinical_mentioned(history) is True

def test_clinical_gate_false_for_irrelevant_text():
    history = [{"speaker": "user", "text": "What is your budget for next quarter?"}]
    ev = ConditionEvaluator()
    assert ev.cof_clinical_mentioned(history) is False

def test_operational_gate_detects_or_mention():
    history = [{"speaker": "user", "text": "How many OR cases are you scheduling per week?"}]
    ev = ConditionEvaluator()
    assert ev.cof_operational_mentioned(history) is True

def test_financial_gate_detects_cost_mention():
    history = [{"speaker": "user", "text": "What does a re-intervention cost your facility?"}]
    ev = ConditionEvaluator()
    assert ev.cof_financial_mentioned(history) is True

def test_all_cof_requires_all_three():
    history = [
        {"speaker": "user", "text": "How are patient outcomes?"},
        {"speaker": "user", "text": "What about OR scheduling throughput?"},
        # No financial mention yet
    ]
    ev = ConditionEvaluator()
    assert ev.cof_all_mentioned(history) is False

def test_open_ended_question_detection():
    history = [
        {"speaker": "user", "text": "What challenges are you facing with stone management?"},
        {"speaker": "user", "text": "How does that impact your clinical team?"},
    ]
    ev = ConditionEvaluator()
    assert ev.open_ended_questions_count(history) == 2

def test_closed_question_not_counted():
    history = [{"speaker": "user", "text": "Is this a problem for you?"}]
    ev = ConditionEvaluator()
    assert ev.open_ended_questions_count(history) == 0

def test_solution_presented_requires_length():
    short = [{"speaker": "user", "text": "Our Tria stent helps."}]
    long = [{"speaker": "user", "text": "Our Tria stent system addresses stone management throughput by reducing OR time and eliminating fragmentation complications, which directly maps to the issues you described."}]
    ev = ConditionEvaluator()
    assert ev.solution_presented(short) is False
    assert ev.solution_presented(long) is True

# --- Arc Stage Tracker ---

def test_arc_starts_at_stage_1():
    arc = {"stages": [{"id": 1, "name": "DISCOVERY", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6}]}
    tracker = ArcStageTracker(arc)
    assert tracker.current_stage == 1

def test_arc_advances_when_condition_met():
    arc = {"stages": [
        {"id": 1, "name": "DISCOVERY", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
        {"id": 2, "name": "PAIN_SURFACE", "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
    ]}
    tracker = ArcStageTracker(arc)
    history = [
        {"speaker": "user", "text": "What challenges are you seeing with stone management?"},
        {"speaker": "user", "text": "How does that affect your OR schedule?"},
    ]
    tracker.evaluate(history)
    assert tracker.current_stage == 2

def test_arc_does_not_advance_when_condition_not_met():
    arc = {"stages": [
        {"id": 1, "name": "DISCOVERY", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
        {"id": 2, "name": "PAIN_SURFACE", "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
    ]}
    tracker = ArcStageTracker(arc)
    history = [{"speaker": "user", "text": "Is this a problem for you?"}]
    tracker.evaluate(history)
    assert tracker.current_stage == 1

def test_cof_gate_accuracy_against_fixtures():
    import json
    from pathlib import Path
    fixture_dir = Path(__file__).parent / "fixtures" / "transcripts"
    fixtures = list(fixture_dir.glob("*.json"))
    assert len(fixtures) >= 10, f"Need at least 10 labeled fixtures, found {len(fixtures)}"
    ev = ConditionEvaluator()
    correct = 0
    for path in fixtures:
        with open(path) as fh:
            f = json.load(fh)
        history = f["turns"]
        exp = f["expected"]
        results = {
            "cof_clinical": ev.cof_clinical_mentioned(history),
            "cof_operational": ev.cof_operational_mentioned(history),
            "cof_financial": ev.cof_financial_mentioned(history),
        }
        if results == exp:
            correct += 1
    accuracy = correct / len(fixtures)
    assert accuracy >= 0.90, f"COF gate accuracy {accuracy:.0%} below 90% threshold"
