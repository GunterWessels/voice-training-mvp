# backend/content_loader.py
"""Load Tier 2 JSONB content (COF map, rubrics, grading criteria, methodology) into scenarios."""
import yaml
from typing import Any, Dict

def validate_cof_map(data: Dict) -> bool:
    required = {"product","clinical_challenge","operational_consequence",
                "financial_reality","solution_bridge","cof_connection_statement","quantified_impact"}
    return required <= set(data.keys())

def validate_argument_rubrics(data: Dict) -> bool:
    if "stages" not in data or not data["stages"]:
        return False
    for stage in data["stages"]:
        if not all(k in stage for k in ("arc_stage","strong_signals","weak_signals",
                                         "persona_if_strong","persona_if_weak")):
            return False
    return True

def validate_grading_criteria(data: Dict) -> bool:
    if "dimensions" not in data or "debrief_instructions" not in data:
        return False
    total = sum(d.get("weight", 0) for d in data["dimensions"])
    if abs(total - 1.0) > 0.01:
        return False
    for d in data["dimensions"]:
        if not all(k in d for k in ("id","weight","description","full","partial","none")):
            return False
    return True

def validate_methodology(data: Dict) -> bool:
    return "id" in data and "steps" in data and len(data["steps"]) > 0

async def load_scenario_content(scenario_id: str, content_dir: str, db) -> Dict[str, int]:
    """Load Tier 2 JSONB content files for a scenario into the scenarios table."""
    from pathlib import Path
    from sqlalchemy import text
    import json
    base = Path(content_dir)
    updates = {}
    validators = {
        "cof_map": validate_cof_map,
        "argument_rubrics": validate_argument_rubrics,
        "grading_criteria": validate_grading_criteria,
        "methodology": validate_methodology,
    }
    for field, validate_fn in validators.items():
        yaml_path = base / f"{field}.yaml"
        if not yaml_path.exists():
            continue
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        if not validate_fn(data):
            raise ValueError(f"{field}.yaml failed validation")
        updates[field] = data

    if updates:
        set_clause = ", ".join(f"{k} = :{k}::jsonb" for k in updates)
        params = {"scenario_id": scenario_id}
        params.update({k: json.dumps(v) for k, v in updates.items()})
        await db.execute(
            text(f"UPDATE scenarios SET {set_clause} WHERE id = :scenario_id"),
            params
        )
        await db.commit()
    return {"fields_loaded": len(updates)}
