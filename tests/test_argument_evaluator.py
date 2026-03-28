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
    from argument_evaluator import detect_signals
    text = "When encrustation increases, it directly impacts OR scheduling and throughput"
    strong, weak = detect_signals(text, SAMPLE_RUBRIC_STAGE_3)
    assert len(strong) > 0

def test_detect_weak_signal():
    from argument_evaluator import detect_signals
    text = "Our price is actually competitive and we can discuss pricing options"
    strong, weak = detect_signals(text, SAMPLE_RUBRIC_STAGE_3)
    assert len(weak) > 0

def test_score_delta_strong_is_positive():
    from argument_evaluator import compute_score_delta
    assert compute_score_delta("strong") == 1

def test_score_delta_weak_is_negative():
    from argument_evaluator import compute_score_delta
    assert compute_score_delta("weak") == -1

def test_score_delta_mixed_is_zero():
    from argument_evaluator import compute_score_delta
    assert compute_score_delta("mixed") == 0
