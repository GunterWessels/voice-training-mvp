# backend/grading_agent.py
"""Post-session grading agent — Claude Sonnet structured debrief."""
import json
from typing import Dict, Any, List
import anthropic
from anthropic.types import TextBlock

# AsyncAnthropic required — grade_session is called from async WebSocket handler
_client = anthropic.AsyncAnthropic()

def build_grading_prompt(transcript: List[Dict], turn_scores: List[Dict],
                         criteria: Dict, cof_map: Dict, methodology: Dict) -> str:
    transcript_text = "\n".join(
        f"[{t.get('arc_stage', '?')}] {t['speaker'].upper()}: {t['text']}"
        for t in transcript
    )
    dims = json.dumps(criteria["dimensions"], indent=2)
    instructions = criteria.get("debrief_instructions", {})
    # Build the JSON format example dynamically from the actual dimension IDs
    dim_format_lines = ",\n    ".join(
        f'{{"id": "{d["id"]}", "score": 0-100, "narrative": "2-3 sentences"}}'
        for d in criteria["dimensions"]
    )
    # Include SPIN and Challenger framework context if present in methodology
    framework_notes = []
    spin_map = methodology.get("spin_map")
    challenger_map = methodology.get("challenger_map")
    if spin_map:
        framework_notes.append("SPIN QUESTION MAP (for spin_questioning dimension):\n" + json.dumps(spin_map, indent=2))
    if challenger_map:
        framework_notes.append("CHALLENGER SALE MAP (for challenger_insight dimension):\n" + json.dumps(challenger_map, indent=2))
    framework_section = ("\n\n" + "\n\n".join(framework_notes)) if framework_notes else ""

    return f"""You are a sales training coach. Grade this voice training session.

TRANSCRIPT:
{transcript_text}

TURN QUALITY SCORES: {json.dumps(turn_scores)}

GRADING DIMENSIONS:
{dims}

COF CHAIN EXPECTED: {cof_map.get('cof_connection_statement', 'N/A')}

METHODOLOGY: {methodology.get('name', 'Standard')}{framework_section}

Instructions: {instructions.get('tone', '')}. {instructions.get('format', '')}

Return ONLY valid JSON in this exact format:
{{
  "dimensions": [
    {dim_format_lines}
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
    block = response.content[0]
    if isinstance(block, TextBlock):
        result = json.loads(block.text)
    else:
        raise ValueError("Grading agent returned unexpected non-text response block")
    result["overall_score"] = compute_overall_score(result["dimensions"], grading_criteria)
    result["debrief_audio"] = grading_criteria.get("debrief_instructions", {}).get("audio", True)
    return result
