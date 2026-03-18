#!/usr/bin/env python3
# scripts/load_content.py
"""CLI: load Tier 2 JSONB content files for a scenario into the scenarios table."""
import asyncio, argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-id", required=True, help="UUID of the scenario to update")
    parser.add_argument("--dir", required=True, help="Directory containing cof_map.yaml etc.")
    args = parser.parse_args()
    from backend.db import get_db
    from backend.content_loader import load_scenario_content
    async for db in get_db():
        result = await load_scenario_content(args.scenario_id, args.dir, db)
        print(f"Loaded {result['fields_loaded']} fields into scenario {args.scenario_id}")

asyncio.run(main())
