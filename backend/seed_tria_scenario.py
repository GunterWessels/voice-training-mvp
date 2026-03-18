"""
Seed the Tria Stents VAC scenario with full ARC, COF map, rubrics,
grading criteria, and methodology content from the spec.
Run via: railway run python3 backend/seed_tria_scenario.py
"""
import asyncio, json, os

SCENARIO_ID = "bbe7c082-687f-4b62-9b3e-69e1bd87537c"

ARC = {
    "stages": [
        {
            "id": 1, "name": "DISCOVERY",
            "persona_instruction": "Respond briefly and professionally. Do NOT volunteer pain points. Wait for the rep to ask at least two open-ended questions before becoming more forthcoming.",
            "unlock_condition": "open_ended_questions >= 2",
            "max_turns": 6
        },
        {
            "id": 2, "name": "PAIN_SURFACE",
            "persona_instruction": "Reveal the primary operational pain: stent retrieval complications are disrupting OR scheduling — roughly 2-3 unplanned cases per month. Still withhold financial impact. Respond to direct clinical questions honestly.",
            "unlock_condition": "cof_clinical_mentioned == true",
            "max_turns": 5
        },
        {
            "id": 3, "name": "COF_PROBE",
            "persona_instruction": "Test whether the rep connects clinical, operational, and financial domains. If they quantify OR scheduling impact, become collaborative and help them do the math. If not, ask 'So what does that mean for us operationally?' or 'What is the financial case here?'",
            "unlock_condition": "cof_all_mentioned == true",
            "max_turns": 8
        },
        {
            "id": 4, "name": "OBJECTION",
            "persona_instruction": "Introduce the scripted objection exactly: 'This sounds promising but the price point is above what our VAC approved last cycle. I don't see a path to yes right now.'",
            "unlock_condition": "solution_presented == true",
            "max_turns": 4
        },
        {
            "id": 5, "name": "RESOLUTION",
            "persona_instruction": "If rep pivots collaboratively (configuration, phased trial, data review), respond positively and move toward commitment. If rep pivots defensively (discounts, pressure), remain skeptical.",
            "unlock_condition": "objection_addressed == true",
            "max_turns": 6
        },
        {
            "id": 6, "name": "CLOSE",
            "persona_instruction": "Signal readiness to take to VAC or agree to a trial. Session can end here.",
            "unlock_condition": "resolution_positive == true",
            "max_turns": 3
        }
    ]
}

COF_MAP = {
    "product": "Tria Ureteral Stents",
    "clinical_challenge": "Ureteral stent encrustation leads to failed retrievals, re-admissions, procedural complications",
    "operational_consequence": "Unplanned stent removal disrupts OR scheduling; 2-3 fewer cases/week at average facility",
    "financial_reality": "Each unplanned re-intervention costs ~$4,200 in OR time + readmission costs",
    "solution_bridge": "Tria's PercuShield coating reduces encrustation by 59% (sterile) / 41% (bacterial) vs Bard Inlay",
    "cof_connection_statement": "When encrustation drops, OR cancellations drop — protecting the revenue-per-bed-day calculation the CFO runs every quarter",
    "quantified_impact": {
        "clinical":    "59% encrustation reduction in sterile conditions, 41% under bacterial challenge (BEST\u2122 study, p<0.05)",
        "operational": "Fewer unplanned procedures per 100 placements; simplified removal clinics",
        "financial":   "Avoided re-intervention cost exceeds Tria device price differential per year"
    }
}

ARGUMENT_RUBRICS = {
    "stages": [
        {
            "arc_stage": 1, "stage_name": "DISCOVERY",
            "strong_signals": [
                "Opens with customer-focused purpose, not product pitch",
                "Asks open-ended Discover questions about current state",
                "Asks about patient volume, complication rates, or workflow before presenting"
            ],
            "weak_signals": [
                "Opens with product features before establishing need",
                "Uses yes/no questions only",
                "Leads with price or value proposition in stage 1"
            ],
            "persona_if_strong": "Become more forthcoming; volunteer the operational pain earlier than scripted",
            "persona_if_weak": "Stay guarded; give short answers; withhold pain points until explicitly asked"
        },
        {
            "arc_stage": 2, "stage_name": "PAIN_SURFACE",
            "strong_signals": [
                "Asks Dissect questions about consequences: 'How does that impact your patients / OR schedule?'",
                "Probes depth of problem before moving to solutions",
                "Uses customer's own language from stage 1"
            ],
            "weak_signals": [
                "Jumps to solution presentation after first pain signal",
                "Asks surface questions without probing downstream impact",
                "Introduces product name before consequence is confirmed"
            ],
            "persona_if_strong": "Reveal the primary operational pain (OR scheduling disruption); remain withholding on financial impact",
            "persona_if_weak": "Acknowledge the surface concern but do not elaborate; wait for deeper questioning"
        },
        {
            "arc_stage": 3, "stage_name": "COF_PROBE",
            "strong_signals": [
                "Connects clinical finding to an operational consequence",
                "Quantifies or estimates financial impact of the problem",
                "Recaps customer's stated concerns before presenting insight",
                "Uses customer's own language when bridging to financial reality"
            ],
            "weak_signals": [
                "Presents product features without linking to clinical \u2192 operational \u2192 financial chain",
                "Leads with price or product before completing COF bridge",
                "Uses clinical language only with no operational or financial bridge"
            ],
            "persona_if_strong": "Become collaborative; help rep do the math on financial impact; prepare to advance stage",
            "persona_if_weak": "Ask 'So what does that mean for us operationally?' \u2014 stall stage advance until bridge is made"
        },
        {
            "arc_stage": 4, "stage_name": "OBJECTION",
            "strong_signals": [
                "Empathizes before defending: acknowledges concern explicitly",
                "Asks a question to understand the source of the objection",
                "Responds with value, trial, or data \u2014 not discount or price reduction"
            ],
            "weak_signals": [
                "Defends product immediately without acknowledging concern",
                "Offers price concession or discount",
                "Ignores emotional component of objection"
            ],
            "persona_if_strong": "Signal openness to next step; begin movement toward VAC or trial commitment",
            "persona_if_weak": "Remain skeptical; restate concern; do not advance"
        },
        {
            "arc_stage": 5, "stage_name": "RESOLUTION",
            "strong_signals": [
                "Reveals clinical insight (3rd-party evidence, study data)",
                "Relates insight back to customer's specific stated concerns",
                "Offers resources that tell the story (study, clinical reference)"
            ],
            "weak_signals": [
                "Makes claims without clinical evidence backing",
                "Uses data without connecting to customer's specific situation",
                "Presents features again instead of evidence-based insight"
            ],
            "persona_if_strong": "Respond positively; move toward commitment language; collaborative tone",
            "persona_if_weak": "Remain skeptical; ask for evidence: 'Do you have data on that?'"
        },
        {
            "arc_stage": 6, "stage_name": "CLOSE",
            "strong_signals": [
                "Asks for a specific next action (trial, VAC presentation, data review)",
                "Proposes a specific timeline (When)",
                "Commits to a concrete deliverable on their side"
            ],
            "weak_signals": [
                "Vague follow-up: 'I\u2019ll circle back' or 'Let me know'",
                "No timeline proposed",
                "Closes with product summary instead of commitment ask"
            ],
            "persona_if_strong": "Agree to specific next step; signal readiness to take to VAC or approve trial",
            "persona_if_weak": "Respond vaguely; no commitment; 'Send me some information'"
        }
    ]
}

GRADING_CRITERIA = {
    "dimensions": [
        {
            "id": "cof_coverage", "weight": 0.35,
            "description": "Did rep address clinical, operational, and financial domains with specificity?",
            "full":    "All 3 COF domains addressed with specificity tied to this customer's context",
            "partial": "2 domains addressed OR all 3 superficially",
            "none":    "1 domain only, or feature-dump with no outcomes language"
        },
        {
            "id": "discovery_quality", "weight": 0.25,
            "description": "Did rep ask open-ended questions before presenting solutions?",
            "full":    "3+ open-ended questions; waited for responses before pivoting to solution",
            "partial": "1\u20132 open-ended questions OR mixed open/closed question pattern",
            "none":    "Jumped to solution presentation with no discovery"
        },
        {
            "id": "argument_coherence", "weight": 0.25,
            "description": "Were clinical findings connected to operational and financial consequences?",
            "full":    "Explicit chain: clinical finding \u2192 operational consequence \u2192 financial reality \u2192 solution",
            "partial": "2-part chain present (clinical \u2192 operational OR operational \u2192 financial)",
            "none":    "No chain; isolated claims or feature statements only"
        },
        {
            "id": "objection_handling", "weight": 0.15,
            "description": "Did rep address the scripted objection without leading with discount or pressure?",
            "full":    "Empathized, asked, responded with value/trial/data \u2014 no discount language",
            "partial": "Addressed objection but defensively or without empathy step",
            "none":    "Offered discount, conceded on price, ignored objection, or became defensive"
        }
    ],
    "debrief_instructions": {
        "tone":   "Coaching voice, positive-tilt, specific to actual transcript moments \u2014 not generic",
        "format": "2\u20133 sentences per dimension; lead with what worked; end with one concrete improvement",
        "audio":  True,
        "voice":  "same persona as session"
    }
}

METHODOLOGY = {
    "id": "bsci_sales",
    "name": "BSCI SALES Framework (Ignite Selling)",
    "steps": [
        {
            "arc_stage": 1, "step_code": "S", "step_name": "Start",
            "sub_steps": ["Purpose", "Payoff", "My START"],
            "strong_patterns": ["Opens with customer benefit", "States payoff for customer", "Open Discover questions"],
            "weak_patterns": ["Opens with product", "No purpose stated", "Closed questions only"],
            "hint_if_weak": "Open with what\u2019s in it for them \u2014 state your purpose and the payoff for their team before asking anything."
        },
        {
            "arc_stage": 2, "step_code": "A1", "step_name": "Ask \u2014 Discover",
            "strong_patterns": ["Current-state questions", "Volume/frequency probes", "Open-ended with 'what/how'"],
            "weak_patterns": ["Feature pitch before discovery", "Yes/no only"],
            "hint_if_weak": "Ask about their current situation before introducing solutions. 'How often does...' is a Discover question."
        },
        {
            "arc_stage": 2, "step_code": "A2", "step_name": "Ask \u2014 Dissect",
            "strong_patterns": ["Consequence questions", "'How does that impact...'", "'What happens when...'"],
            "weak_patterns": ["Surface question without probing impact", "Moves to solution after first pain mention"],
            "hint_if_weak": "Probe the consequences: 'How does that impact your patients or your OR schedule?'"
        },
        {
            "arc_stage": 3, "step_code": "A3+L", "step_name": "Ask \u2014 Develop + Listen/Recap",
            "strong_patterns": ["'How would it help if...'", "Recap before insight", "Uses customer language"],
            "weak_patterns": ["Pitches before recapping", "No Develop question asked", "Skips to Explain Insights"],
            "hint_if_weak": "Before presenting your insight, recap what you heard: 'So if I\u2019m understanding you correctly...'"
        },
        {
            "arc_stage": 4, "step_code": "Resistance", "step_name": "Overcoming Resistance",
            "strong_patterns": ["Empathizes first", "Asks before responding", "No discount language"],
            "weak_patterns": ["Defends immediately", "Price concession offered", "Emotional component ignored"],
            "hint_if_weak": "Empathize first, then ask a question before you respond. 'I hear you \u2014 what specifically is driving that concern?'"
        },
        {
            "arc_stage": 5, "step_code": "E", "step_name": "Explain Insights",
            "strong_patterns": ["Reveals 3rd-party evidence", "Relates evidence to customer\u2019s stated situation", "Offers resources"],
            "weak_patterns": ["Claims without evidence", "Data without customer connection", "Feature repeat"],
            "hint_if_weak": "Share a clinical insight that tells the story \u2014 then connect it directly to what they told you earlier."
        },
        {
            "arc_stage": 6, "step_code": "S2", "step_name": "Secure Commitments",
            "strong_patterns": ["Specific action (What)", "Specific timeline (When)", "Concrete rep commitment"],
            "weak_patterns": ["Vague follow-up", "No timeline", "Summary instead of ask"],
            "hint_if_weak": "Ask for a specific next step with a date: 'Can we schedule a 30-minute VAC prep by end of next week?'"
        }
    ],
    "resistance_model": {
        "sequence": ["Empathize", "Ask", "Respond"],
        "strong_patterns": ["Acknowledges concern before defending", "Asks a question before responding", "No discount language"],
        "weak_patterns": ["Defends immediately", "Offers price concession", "Ignores emotional component"]
    }
}


async def seed():
    import asyncpg
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)

    row = await conn.fetchrow("SELECT id, name FROM scenarios WHERE id = $1", SCENARIO_ID)
    if not row:
        print(f"ERROR: Scenario {SCENARIO_ID} not found")
        await conn.close()
        return

    print(f"Updating scenario: {row['name']}")
    await conn.execute(
        """UPDATE scenarios SET
               arc              = $1::jsonb,
               cof_map          = $2::jsonb,
               argument_rubrics = $3::jsonb,
               grading_criteria = $4::jsonb,
               methodology      = $5::jsonb
           WHERE id = $6""",
        json.dumps(ARC),
        json.dumps(COF_MAP),
        json.dumps(ARGUMENT_RUBRICS),
        json.dumps(GRADING_CRITERIA),
        json.dumps(METHODOLOGY),
        SCENARIO_ID,
    )
    await conn.close()
    print("Done. Scenario seeded with full ARC, COF map, rubrics, grading criteria, and methodology.")

asyncio.run(seed())
