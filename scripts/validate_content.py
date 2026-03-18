#!/usr/bin/env python3
# scripts/validate_content.py
"""CLI: validate Tier 2 YAML content files before loading."""
import sys, yaml, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Directory containing cof_map.yaml, argument_rubrics.yaml, etc.")
    args = parser.parse_args()
    from backend.content_loader import validate_cof_map, validate_argument_rubrics, validate_grading_criteria, validate_methodology
    validators = {
        "cof_map.yaml": validate_cof_map,
        "argument_rubrics.yaml": validate_argument_rubrics,
        "grading_criteria.yaml": validate_grading_criteria,
        "methodology.yaml": validate_methodology,
    }
    base = Path(args.dir)
    ok = True
    for fname, fn in validators.items():
        path = base / fname
        if not path.exists():
            print(f"  SKIP  {fname} (not found)")
            continue
        with open(path) as f:
            data = yaml.safe_load(f)
        if fn(data):
            print(f"  OK    {fname}")
        else:
            print(f"  FAIL  {fname}")
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
