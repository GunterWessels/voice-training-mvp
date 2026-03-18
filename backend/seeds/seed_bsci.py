"""Seed initial BSCI divisions, cohorts, and scenarios."""
import asyncio
import os
import sys

# Allow running directly: python3 backend/seeds/seed_bsci.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.db import AsyncSessionLocal
from backend.models import Division, Scenario

TRIA_ARC = {
    "stages": [
        {"id": 1, "name": "DISCOVERY",
         "persona_instruction": "You are a busy VAC procurement director. Respond vaguely to generic questions. Wait for focused, open-ended discovery questions before revealing any information.",
         "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
        {"id": 2, "name": "PAIN_SURFACE",
         "persona_instruction": "Reveal stone management throughput issues — OR cases being delayed due to stent fragmentation complications. Do not yet mention cost impact.",
         "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
        {"id": 3, "name": "COF_PROBE",
         "persona_instruction": "If the rep asks about OR scheduling or volume impact, become more collaborative. If they quantify cases-per-week lost, help them do the math. Still guard the financial figure until they ask directly.",
         "unlock_condition": "cof_all_mentioned == true", "max_turns": 8},
        {"id": 4, "name": "OBJECTION",
         "persona_instruction": "Introduce this objection exactly: 'This sounds promising but the price point is above what our VAC approved last cycle. I don't see a path to yes right now.'",
         "unlock_condition": "solution_presented == true", "max_turns": 4},
        {"id": 5, "name": "RESOLUTION",
         "persona_instruction": "If rep proposes a phased trial, data collection period, or configuration change — respond positively and begin moving toward VAC commitment. If rep offers discount or price pressure — remain firmly skeptical.",
         "unlock_condition": "objection_addressed == true", "max_turns": 6},
        {"id": 6, "name": "CLOSE",
         "persona_instruction": "Signal readiness to bring Tria to the next VAC cycle or agree to a 30-day trial. The session can end here.",
         "unlock_condition": "resolution_positive == true", "max_turns": 3},
    ]
}

TRIA_CELEBRATIONS = [
    {"condition": "first_session", "type": "confetti", "content": "You just had your first AI sales conversation. Most people don't even try."},
    {"condition": "first_cof_clean", "type": "badge", "content": "Clean COF sweep."},
    {"condition": "speed_stage_5", "type": "badge", "content": "Fast hands."},
]

async def seed():
    async with AsyncSessionLocal() as db:
        endo = Division(name="Endo Urology", slug="endo-urology")
        cardiac = Division(name="Cardiac Rhythm Management", slug="cardiac-rhythm")
        db.add_all([endo, cardiac])
        await db.flush()

        tria_scenario = Scenario(
            name="VAC Stakeholder — Tria Stents",
            division_id=endo.id,
            product_name="Tria Ureteral Stents",
            persona_id="vac_buyer",
            arc=TRIA_ARC,
            celebration_triggers=TRIA_CELEBRATIONS,
        )
        db.add(tria_scenario)
        await db.commit()
        print(f"Seeded: {endo.name}, {cardiac.name}, Tria Stents scenario ({tria_scenario.id})")

if __name__ == "__main__":
    asyncio.run(seed())
