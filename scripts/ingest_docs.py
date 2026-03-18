#!/usr/bin/env python3
# scripts/ingest_docs.py
"""CLI: ingest a knowledge_base.yaml file into pgvector."""
import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to knowledge_base.yaml")
    parser.add_argument("--scenario-id", default=None, help="Override scenario UUID (PostgreSQL scenarios.id)")
    args = parser.parse_args()

    from backend.db import get_db
    from backend.ingestion import ingest_yaml

    async for db in get_db():
        stats = await ingest_yaml(args.file, db, scenario_id=args.scenario_id)
        print(f"Ingested: {stats['ingested']} | Skipped: {stats['skipped']} | Total: {stats['total']}")


asyncio.run(main())
