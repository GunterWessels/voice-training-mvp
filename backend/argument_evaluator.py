# backend/argument_evaluator.py
"""Per-turn 2-layer argument evaluation. Layer 1 deterministic; Layer 2 LLM fallback."""
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

    if strong and not weak:
        quality = "strong"
    elif weak and not strong:
        quality = "weak"
    else:
        quality = "mixed"
        if cof_map:
            quality = await _llm_evaluate(rep_text, arc_stage, rubric_stage, cof_map)

    persona_instruction = (
        rubric_stage.get("persona_if_strong", "") if quality == "strong"
        else rubric_stage.get("persona_if_weak", "")
    )

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
