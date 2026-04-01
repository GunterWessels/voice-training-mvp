-- Migration: seed LithoVue Elite HCRU scenario + practice series
-- Based on Bhojani et al. CUAJ 2026 — real-world HRU study

INSERT INTO scenarios (
  id, name, division_id, persona_id,
  arc, cof_map, argument_rubrics, grading_criteria, methodology, is_active
)
VALUES (
  'c2e00000-0000-0000-0000-000000000001',
  'LithoVue Elite — HCRU Study Conversation',
  'a1b2c3d4-0000-0000-0000-000000000001',
  'hospital_admin',
  '{"stages": [
    {"id": 1, "name": "DISCOVERY", "persona_instruction": "You are a hospital VP of Surgical Services reviewing the ureteroscopy service line. You are aware of a post-URS complication rate but have not quantified it. Be professional but brief. Wait for the rep to ask at least two open-ended questions before revealing financial concerns.", "unlock_condition": "open_ended_questions >= 2", "max_turns": 6},
    {"id": 2, "name": "PAIN_SURFACE", "persona_instruction": "Acknowledge that post-URS ED returns and readmissions have been flagged in your quality dashboard. Reveal that approximately 10-12% of URS patients are returning within 30 days but you have not attributed a cost to it. Respond honestly to clinical questions.", "unlock_condition": "cof_clinical_mentioned == true", "max_turns": 5},
    {"id": 3, "name": "COF_PROBE", "persona_instruction": "If the rep connects the post-URS return rate to financial and quality metric impact, become collaborative. Help them do the math on bed cost and CMS exposure. If they only talk about the device, stay guarded and ask what the financial case is.", "unlock_condition": "cof_all_mentioned == true", "max_turns": 8},
    {"id": 4, "name": "OBJECTION", "persona_instruction": "Raise this objection exactly: This is an observational study funded by the manufacturer. Our value analysis committee will push back on the study design before approving a premium device.", "unlock_condition": "solution_presented == true", "max_turns": 4},
    {"id": 5, "name": "RESOLUTION", "persona_instruction": "If the rep acknowledges the limitation and pivots to the consistency of findings across time points and subgroups, and references the peer-reviewed journal, respond positively and move toward next steps. If they defend without acknowledging limitation, stay skeptical.", "unlock_condition": "objection_addressed == true", "max_turns": 5},
    {"id": 6, "name": "CLOSE", "persona_instruction": "Signal willingness to bring this to the VAC or arrange a HEMA review. Session can end with a specific next step.", "unlock_condition": "resolution_positive == true", "max_turns": 3}
  ]}'::jsonb,
  '{"product": "LithoVue Elite with IRP Monitoring",
    "clinical_challenge": "Post-ureteroscopy patients return to the ED or are admitted at rates of 8-12% within 30 days — driven by sepsis, infection, and pressure-related complications",
    "operational_consequence": "ED returns and unplanned admissions consume nursing capacity, staff time, and bed availability; quality dashboards flag URS as a high-return service line",
    "financial_reality": "NNT of 21-24 means 20-25 avoidable events per 500 URS cases annually; each event carries ED staff cost, bed cost, and CMS quality metric exposure",
    "solution_bridge": "LithoVue Elite IRP monitoring is associated with 53% lower odds of HRU at 10 days and 47% lower odds at 30 days vs. other single-use scopes (Bhojani CUAJ 2026)",
    "cof_connection_statement": "When intrarenal pressure is monitored in real time, surgeons can adjust irrigation before complications develop — and the HCRU data shows that difference shows up in your ED return rate and your quality dashboard",
    "quantified_impact": {
      "clinical": "10-day HRU: 4.5% vs. 8.7% (OR 0.355, p=0.004); 30-day: 7.2% vs. 12.0% (OR 0.473, p=0.005) — Bhojani et al. CUAJ 2026, n=15,353 real-world patients",
      "operational": "NNT 21-24 to avert one ED visit or inpatient admission; 20-25 avoidable events per 500 cases annually",
      "financial": "Each avoided admission saves bed-night cost + CMS quality exposure; prior infection study: 8.2% vs. 15.4% post-op infection rate (p=0.016)"
    }
  }'::jsonb,
  '{"stages": [
    {"arc_stage": 1, "stage_name": "DISCOVERY",
     "strong_signals": ["Opens with patient outcome or service line question, not device pitch", "Asks about current post-URS complication or return rate", "Asks about quality dashboard or CMS exposure before presenting data"],
     "weak_signals": ["Opens with study data before establishing current state", "Leads with device features", "Does not ask about their specific situation"],
     "persona_if_strong": "Become more forthcoming; reveal the 10-12% return rate earlier",
     "persona_if_weak": "Stay brief; give vague answers; do not volunteer quality data"},
    {"arc_stage": 2, "stage_name": "PAIN_SURFACE",
     "strong_signals": ["Asks how the return rate impacts OR scheduling, quality metrics, or cost", "Probes whether the administrator has quantified the financial burden", "Uses hospital admin language: admissions, quality, dashboard, CMS"],
     "weak_signals": ["Jumps to study data after first pain mention", "Stays in clinical language only without connecting to operations or finance"],
     "persona_if_strong": "Reveal the unquantified cost exposure; invite collaborative math",
     "persona_if_weak": "Acknowledge problem but stay guarded; do not advance stage"},
    {"arc_stage": 3, "stage_name": "COF_PROBE",
     "strong_signals": ["Connects infection/complication rate to ED costs and CMS quality penalties", "Quantifies NNT impact on annual case volume", "Recaps the administrator''s stated concerns before presenting the study"],
     "weak_signals": ["Presents study stats without connecting to this facility''s return rate", "Leads with OR values without contextualizing for a non-clinical audience"],
     "persona_if_strong": "Become collaborative; help do the math on avoided events per year",
     "persona_if_weak": "Ask what the financial case is; stall until COF bridge is made"},
    {"arc_stage": 4, "stage_name": "OBJECTION",
     "strong_signals": ["Acknowledges the observational design limitation proactively", "Cites consistency across time points and subgroups as signal of robustness", "References peer-reviewed journal, not manufacturer claim"],
     "weak_signals": ["Defends study without acknowledging limitation", "Claims the study proves causation", "Becomes defensive or dismissive"],
     "persona_if_strong": "Signal openness to VAC review or HEMA manager meeting",
     "persona_if_weak": "Remain skeptical; state the VAC will reject observational data"},
    {"arc_stage": 5, "stage_name": "RESOLUTION",
     "strong_signals": ["Offers to arrange a HEMA manager review with VAC", "Provides the one-pager or study citation directly", "Frames as initial real-world evidence warranting further review, not definitive proof"],
     "weak_signals": ["Oversells the study as definitive RCT-equivalent evidence", "Cannot cite specific numbers from the study when pressed"],
     "persona_if_strong": "Agree to next step; mention bringing HEMA manager to VAC",
     "persona_if_weak": "Ask for more evidence; no commitment"},
    {"arc_stage": 6, "stage_name": "CLOSE",
     "strong_signals": ["Asks for specific next step: VAC presentation, HEMA review, or pilot discussion", "Names a timeline", "Commits to sending study + one-pager same day"],
     "weak_signals": ["Vague follow-up", "No timeline", "Closes with device summary instead of action"],
     "persona_if_strong": "Agree to specific next step and timeline",
     "persona_if_weak": "Non-committal; no action"}
  ]}'::jsonb,
  '{"dimensions": [
    {"id": "cof_coverage", "weight": 0.25, "description": "Did rep address clinical, operational, and financial domains in hospital admin language?",
     "full": "All 3 COF domains addressed with specificity: return rate (clinical), ED/quality impact (operational), CMS/bed cost (financial)",
     "partial": "2 domains OR all 3 superficially without connecting to this facility",
     "none": "Clinical only, or device feature presentation with no outcomes language"},
    {"id": "discovery_quality", "weight": 0.20, "description": "Did rep ask about current URS return rate and quality exposure before presenting the study?",
     "full": "3+ questions about current state; confirmed their return rate and quality exposure before presenting data",
     "partial": "1-2 questions OR moved to study data without confirming their specific situation",
     "none": "No discovery; opened with HCRU study data immediately"},
    {"id": "argument_coherence", "weight": 0.20, "description": "Did rep connect IRP monitoring → reduced complications → fewer ED returns → financial and quality metric impact?",
     "full": "Explicit 4-part chain: IRP monitoring → complication reduction → HRU reduction → financial/CMS outcome",
     "partial": "2-3 part chain present",
     "none": "No chain; isolated statistics without narrative connection"},
    {"id": "objection_handling", "weight": 0.15, "description": "Did rep handle the observational study design objection with appropriate balance?",
     "full": "Acknowledged limitation, pivoted to robustness evidence (multiple time points, subgroups, peer-reviewed), offered HEMA review",
     "partial": "Partially acknowledged limitation but defended without full robustness pivot",
     "none": "Dismissed limitation, overclaimed study strength, or became defensive"},
    {"id": "spin_questioning", "weight": 0.10, "description": "Did rep progress through SPIN: current return rate (S) → financial/quality impact (P) → downstream cost exposure (I) → value of reduction (N-P)?",
     "full": "All 4 SPIN stages evident in hospital admin context",
     "partial": "2-3 stages present",
     "none": "No SPIN progression; led with study data"},
    {"id": "challenger_insight", "weight": 0.10, "description": "Did rep teach the administrator something they did not know — the NNT math applied to their volume — and drive to a specific commitment?",
     "full": "Calculated NNT impact for their program volume; framed as peer-reviewed evidence warranting VAC review; closed with specific next step + timeline",
     "partial": "Presented NNT but did not tailor to their volume; or tailored well but closed vaguely",
     "none": "No insight; repeated statistics without application; closed with no ask"}
  ],
  "debrief_instructions": {
    "tone": "Coaching voice, positive-tilt, specific to transcript moments — focus on how the rep handled the observational design objection",
    "format": "2-3 sentences per dimension; lead with what worked; end with one concrete improvement",
    "audio": true,
    "voice": "hospital_admin persona"
  }}'::jsonb,
  '{"id": "bsci_sales", "name": "BSCI SALES Framework + SPIN + Challenger — Hospital Admin Context",
    "steps": [
      {"arc_stage": 1, "step_code": "S", "step_name": "Start", "hint_if_weak": "Open with the outcome they care about: post-URS patient returns. State your purpose and the payoff for their quality program before presenting any data."},
      {"arc_stage": 2, "step_code": "A1", "step_name": "Ask — Discover", "hint_if_weak": "Ask about their current post-URS return rate before you share anything. ''What percentage of your URS patients are returning to the ED or getting admitted within 30 days?''"},
      {"arc_stage": 2, "step_code": "A2", "step_name": "Ask — Dissect", "hint_if_weak": "Probe the downstream consequences: ''How does that rate affect your CMS quality scores?'' or ''Have you quantified what each of those returns costs the facility?''"},
      {"arc_stage": 3, "step_code": "A3+L", "step_name": "Ask — Develop + Listen", "hint_if_weak": "Before presenting the HCRU study, recap: ''So if I''m hearing you right, you have a 10-12% return rate and you have not yet connected that to a dollar figure or a quality metric penalty...''"},
      {"arc_stage": 4, "step_code": "Resistance", "step_name": "Overcoming Resistance", "hint_if_weak": "When they challenge the observational design, say: ''That is a fair challenge and worth raising with your VAC. Here is how I would respond to it...'' Then acknowledge and pivot."},
      {"arc_stage": 5, "step_code": "E", "step_name": "Explain Insights", "hint_if_weak": "Share the NNT calculation tailored to their volume. If they do 400 cases a year and NNT is 21, that is 19 avoidable events. Make it specific to their program."},
      {"arc_stage": 6, "step_code": "S2", "step_name": "Secure Commitments", "hint_if_weak": "Ask for a specific meeting: ''Can we arrange a 30-minute session with your HEMA manager and your VAC chair before your next formulary review?''"}
    ],
    "resistance_model": {
      "sequence": ["Empathize", "Ask", "Respond"],
      "strong_patterns": ["Acknowledges observational limitation before defending", "Cites directional consistency across time points", "Offers HEMA manager as resource"],
      "weak_patterns": ["Claims study proves causation", "Dismisses VAC concern", "Cannot cite specific numbers under pressure"]
    }
  }'::jsonb,
  true
)
ON CONFLICT (id) DO UPDATE SET
  arc              = EXCLUDED.arc,
  cof_map          = EXCLUDED.cof_map,
  argument_rubrics = EXCLUDED.argument_rubrics,
  grading_criteria = EXCLUDED.grading_criteria,
  methodology      = EXCLUDED.methodology;

-- Practice series for this scenario
INSERT INTO practice_series (id, name, category, description, approved, created_at)
VALUES (
  'f1a00000-0000-0000-0000-000000000002',
  'LithoVue Elite — HCRU Study (Hospital Admin)',
  'capital_equipment',
  'Practice presenting the Bhojani et al. CUAJ 2026 HCRU study to a hospital VP. Master the COF bridge from IRP monitoring to post-URS return rates to financial and quality metric impact.',
  true,
  NOW()
)
ON CONFLICT (id) DO UPDATE SET
  name        = EXCLUDED.name,
  category    = EXCLUDED.category,
  description = EXCLUDED.description;

INSERT INTO practice_series_items (id, series_id, scenario_id, position)
VALUES (
  'f2a00000-0000-0000-0000-000000000002',
  'f1a00000-0000-0000-0000-000000000002',
  'c2e00000-0000-0000-0000-000000000001',
  1
)
ON CONFLICT (series_id, position) DO NOTHING;
