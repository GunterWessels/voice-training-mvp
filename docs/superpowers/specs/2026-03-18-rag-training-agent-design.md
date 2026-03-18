# RAG-Powered Training Agent Design Spec
**Version:** 1.0
**Date:** 2026-03-18
**Author:** LiquidSMARTS™
**Status:** Approved for Implementation

---

## 1. Executive Summary

This spec defines the knowledge architecture, agent evaluation logic, and grading system for the LiquidSMARTS™ Voice Training Platform's RAG layer. It extends the production platform spec (`2026-03-18-voice-platform-production-design.md`) by specifying how agent behavior is grounded in product knowledge, clinical evidence, sales methodology, and structured evaluation criteria.

The system uses a **2-Tier Hybrid RAG architecture**: unstructured BSCI-sourced documents retrieved via semantic vector search (Tier 1), and LiquidSMARTS™-authored structured documents retrieved deterministically by scenario ID (Tier 2). A configurable sales methodology layer (Domain 6) enables deployment to clients using BSCI SALES, SPIN, Challenger, or custom frameworks.

---

## 2. Six Knowledge Domains

| # | Domain | Tier | Source | Retrieval |
|---|--------|------|--------|-----------|
| 1 | Product Knowledge | 1 — Vector | BSCI-provided (IFU, sales aids, coverage docs) | Semantic search, top-5 cosine similarity |
| 2 | Clinical Context | 1 — Vector | BSCI-provided (clinical evidence, MOA, outcomes) | Semantic search, top-5 cosine similarity |
| 3 | COF Connection Map | 2 — Structured | LiquidSMARTS™-authored JSONB | Deterministic: `WHERE scenario_id = $1` |
| 4 | Argument Evaluation Rubrics | 2 — Structured | LiquidSMARTS™-authored JSONB | Deterministic: `WHERE scenario_id = $1` |
| 5 | Grading Criteria | 2 — Structured | LiquidSMARTS™-authored JSONB | Deterministic: `WHERE scenario_id = $1` |
| 6 | Sales Methodology | 2 — Structured | LiquidSMARTS™-authored JSONB | Deterministic: `WHERE scenario_id = $1` |

---

## 3. Architecture

### 3.1 Topology

```
Session Start
  → Load Tier 2 (one query): cof_map + argument_rubrics + grading_criteria + methodology
  → Ready

Per Turn (rep speaks)
  → Layer 1 eval: pattern-match rep utterance against rubric signals + COF seeds + methodology signals
  → Layer 2 eval (if needed): LLM call (Haiku, temp 0.1) for argument coherence judgment
  → Evaluator output: {argument_quality, persona_instruction, hint_for_rep, score_delta}
  → Tier 1 retrieval: vector search product + clinical chunks (if arc stage requires factual grounding)
  → Persona response generated (GPT-4o-mini + enriched system prompt)
  → Rep hint layer updated (throttled — see Section 7.3)
  → Turn score written to session record

Post Session
  → Grading agent call (Claude Sonnet, temp 0.3): transcript + turn_scores[] + grading criteria + methodology
  → Structured debrief generated
  → Debrief delivered: COF gates first (instant) → dimension scores animate in → audio TTS in persona voice
```

### 3.2 Database Changes

**New table: `knowledge_chunks`**

```sql
CREATE TABLE knowledge_chunks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id   UUID REFERENCES scenarios(id),
  product_id    TEXT NOT NULL,
  domain        TEXT NOT NULL,    -- 'product' | 'clinical'
  section       TEXT,
  content       TEXT NOT NULL,
  source_doc    TEXT,
  page          INTEGER,
  approved_claim BOOLEAN DEFAULT FALSE,
  embedding     vector(1536),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON knowledge_chunks (scenario_id, domain);
```

**New columns on `scenarios`**

```sql
ALTER TABLE scenarios
  ADD COLUMN cof_map          JSONB,
  ADD COLUMN argument_rubrics JSONB,
  ADD COLUMN grading_criteria JSONB,
  ADD COLUMN methodology      JSONB;
```

**Updated column on `completions`**

```sql
ALTER TABLE completions
  ADD COLUMN dimension_scores JSONB;
-- Stores per-dimension breakdown: {cof_coverage, discovery_quality, argument_coherence, objection_handling}
-- overall score stays in the existing completions.score INTEGER column
```

---

## 4. Tier 1 — Vector Store (Domains 1 & 2)

### 4.1 Chunk Schema

```yaml
id:             uuid
scenario_id:    uuid            # filter key — retrieval scoped to scenario
product_id:     text            # e.g. "tria_stents"
domain:         product | clinical
section:        text            # e.g. "claims", "moa", "evidence"
content:        text            # 150–400 words, self-contained
source_doc:     text            # filename for traceability
page:           integer
approved_claim: boolean         # true = FDA-cleared language, retrieved verbatim only
embedding:      vector(1536)    # OpenAI text-embedding-3-small
```

**`approved_claim: true` constraint:** When a chunk is flagged as an approved claim, the persona system prompt instructs the model to use the retrieved text verbatim and not paraphrase. This enforces FDA-cleared language integrity.

### 4.2 Ingestion Pipeline

1. Receive BSCI documents (PDF/DOCX: IFU, clinical evidence, coverage policy, sales aid)
2. Extract text via `pdfplumber`; detect section headers and map to schema sections
3. Human review: flag `approved_claim: true` on FDA-cleared statements
4. Chunk at ~400 tokens with 50-token overlap; approved-claim chunks never split mid-statement
5. Embed via OpenAI `text-embedding-3-small` (~$0.02/1M tokens)
6. Insert into `knowledge_chunks` with full metadata
7. CLI: `python3 scripts/ingest_docs.py --product tria_stents --scenario <id> --dir ./docs/bsci/`
8. Re-ingestion: `--replace` flag deletes old chunks for `source_doc` before inserting new

### 4.3 Tier 1 Retrieval Trigger Rules

Tier 1 vector retrieval fires only on arc stages where factual grounding is needed for accurate persona responses. Retrieval is skipped on stages where the persona operates from conversation context alone.

| Arc Stage | Tier 1 Retrieval | Reason |
|-----------|-----------------|--------|
| 1 — DISCOVERY | No | Persona operates from arc instructions only; no product facts needed |
| 2 — PAIN_SURFACE | No | Persona surfaces clinical pain from COF map (Tier 2), not from vector search |
| 3 — COF_PROBE | Yes — clinical domain | Persona may need to confirm or reference clinical evidence when rep brings product up |
| 4 — OBJECTION | Yes — product + clinical | Persona needs accurate product claims and study data to respond to rep's evidence |
| 5 — RESOLUTION | Yes — product + clinical | Persona evaluates whether rep's cited evidence is accurate; factual grounding required |
| 6 — CLOSE | No | Commitment stage; persona operates from conversation context only |

### 4.4 Knowledge Base Source Files

YAML-formatted source files live in `content/<product_id>/knowledge_base.yaml`. These are the human-editable source of truth before ingestion. Each chunk is explicitly authored, reviewed, and flagged. The admin dashboard shows loaded files, chunk counts, and last-ingested timestamps.

**Current files:**

| File | Chunks | Status |
|------|--------|--------|
| `content/tria_stents/knowledge_base.yaml` | 18 | Loaded |

---

## 5. Tier 2 — Structured Lookup (Domains 3–6)

All four structured domains are loaded in a single query at session start and held in session memory for the duration of the conversation. No per-turn DB calls.

### 5.1 Domain 3: COF Connection Map

```json
{
  "product": "Tria Ureteral Stents",
  "clinical_challenge": "Ureteral stent encrustation leads to failed retrievals, re-admissions, procedural complications",
  "operational_consequence": "Unplanned stent removal disrupts OR scheduling; 2-3 fewer cases/week at average facility",
  "financial_reality": "Each unplanned re-intervention costs ~$4,200 in OR time + readmission costs",
  "solution_bridge": "Tria's PercuShield coating reduces encrustation by 59% (sterile) / 41% (bacterial) vs Bard Inlay",
  "cof_connection_statement": "When encrustation drops, OR cancellations drop — protecting the revenue-per-bed-day calculation the CFO runs every quarter",
  "quantified_impact": {
    "clinical":     "59% encrustation reduction in sterile conditions, 41% under bacterial challenge (BEST™ study, p<0.05)",
    "operational":  "Fewer unplanned procedures per 100 placements; simplified removal clinics",
    "financial":    "Avoided re-intervention cost exceeds Tria device price differential per year"
  }
}
```

### 5.2 Domain 4: Argument Evaluation Rubrics

One entry per arc stage. Both drives persona reaction AND feeds parallel scoring.

```json
{
  "stages": [
    {
      "arc_stage": 1,
      "stage_name": "DISCOVERY",
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
      "persona_if_weak":   "Stay guarded; give short answers; withhold pain points until explicitly asked"
    },
    {
      "arc_stage": 2,
      "stage_name": "PAIN_SURFACE",
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
      "persona_if_weak":   "Acknowledge the surface concern but do not elaborate; wait for deeper questioning"
    },
    {
      "arc_stage": 3,
      "stage_name": "COF_PROBE",
      "strong_signals": [
        "Connects clinical finding to an operational consequence",
        "Quantifies or estimates financial impact of the problem",
        "Recaps customer's stated concerns before presenting insight",
        "Uses customer's own language when bridging to financial reality"
      ],
      "weak_signals": [
        "Presents product features without linking to clinical → operational → financial chain",
        "Leads with price or product before completing COF bridge",
        "Uses clinical language only with no operational or financial bridge"
      ],
      "persona_if_strong": "Become collaborative; help rep do the math on financial impact; prepare to advance stage",
      "persona_if_weak":   "Ask 'So what does that mean for us operationally?' — stall stage advance until bridge is made"
    },
    {
      "arc_stage": 4,
      "stage_name": "OBJECTION",
      "strong_signals": [
        "Empathizes before defending: acknowledges concern explicitly",
        "Asks a question to understand the source of the objection",
        "Responds with value, trial, or data — not discount or price reduction"
      ],
      "weak_signals": [
        "Defends product immediately without acknowledging concern",
        "Offers price concession or discount",
        "Ignores emotional component of objection"
      ],
      "persona_if_strong": "Signal openness to next step; begin movement toward VAC or trial commitment",
      "persona_if_weak":   "Remain skeptical; restate concern; do not advance"
    },
    {
      "arc_stage": 5,
      "stage_name": "RESOLUTION",
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
      "persona_if_weak":   "Remain skeptical; ask for evidence: 'Do you have data on that?'"
    },
    {
      "arc_stage": 6,
      "stage_name": "CLOSE",
      "strong_signals": [
        "Asks for a specific next action (trial, VAC presentation, data review)",
        "Proposes a specific timeline (When)",
        "Commits to a concrete deliverable on their side"
      ],
      "weak_signals": [
        "Vague follow-up: 'I'll circle back' or 'Let me know'",
        "No timeline proposed",
        "Closes with product summary instead of commitment ask"
      ],
      "persona_if_strong": "Agree to specific next step; signal readiness to take to VAC or approve trial",
      "persona_if_weak":   "Respond vaguely; no commitment; 'Send me some information'"
    }
  ]
}
```

### 5.3 Domain 5: Grading Criteria

```json
{
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
      "partial": "1–2 open-ended questions OR mixed open/closed question pattern",
      "none":    "Jumped to solution presentation with no discovery"
    },
    {
      "id": "argument_coherence", "weight": 0.25,
      "description": "Were clinical findings connected to operational and financial consequences?",
      "full":    "Explicit chain: clinical finding → operational consequence → financial reality → solution",
      "partial": "2-part chain present (clinical → operational OR operational → financial)",
      "none":    "No chain; isolated claims or feature statements only"
    },
    {
      "id": "objection_handling", "weight": 0.15,
      "description": "Did rep address the scripted objection without leading with discount or pressure?",
      "full":    "Empathized, asked, responded with value/trial/data — no discount language",
      "partial": "Addressed objection but defensively or without empathy step",
      "none":    "Offered discount, conceded on price, ignored objection, or became defensive"
    }
  ],
  "debrief_instructions": {
    "tone":    "Coaching voice, positive-tilt, specific to actual transcript moments — not generic",
    "format":  "2–3 sentences per dimension; lead with what worked; end with one concrete improvement",
    "audio":   true,
    "voice":   "same persona as session"
  }
}
```

### 5.4 Domain 6: Sales Methodology

```json
{
  "id":   "bsci_sales",
  "name": "BSCI SALES Framework (Ignite Selling)",
  "steps": [
    {
      "arc_stage": 1, "step_code": "S", "step_name": "Start",
      "sub_steps": ["Purpose", "Payoff", "My START"],
      "strong_patterns": ["Opens with customer benefit", "States payoff for customer", "Open Discover questions"],
      "weak_patterns": ["Opens with product", "No purpose stated", "Closed questions only"],
      "hint_if_weak": "Open with what's in it for them — state your purpose and the payoff for their team before asking anything."
    },
    {
      "arc_stage": 2, "step_code": "A1", "step_name": "Ask — Discover",
      "strong_patterns": ["Current-state questions", "Volume/frequency probes", "Open-ended with 'what/how'"],
      "weak_patterns": ["Feature pitch before discovery", "Yes/no only"],
      "hint_if_weak": "Ask about their current situation before introducing solutions. 'How often does...' is a Discover question."
    },
    {
      "arc_stage": 2, "step_code": "A2", "step_name": "Ask — Dissect",
      "strong_patterns": ["Consequence questions", "'How does that impact...'", "'What happens when...'"],
      "weak_patterns": ["Surface question without probing impact", "Moves to solution after first pain mention"],
      "hint_if_weak": "Probe the consequences: 'How does that impact your patients or your OR schedule?'"
    },
    {
      "arc_stage": 3, "step_code": "A3+L", "step_name": "Ask — Develop + Listen/Recap",
      "strong_patterns": ["'How would it help if...'", "Recap before insight", "Uses customer language"],
      "weak_patterns": ["Pitches before recapping", "No Develop question asked", "Skips to Explain Insights"],
      "hint_if_weak": "Before presenting your insight, recap what you heard: 'So if I'm understanding you correctly...'"
    },
    {
      "arc_stage": 4, "step_code": "Resistance", "step_name": "Overcoming Resistance",
      "strong_patterns": ["Empathizes first", "Asks before responding", "No discount language"],
      "weak_patterns": ["Defends immediately", "Price concession offered", "Emotional component ignored"],
      "hint_if_weak": "Empathize first, then ask a question before you respond. 'I hear you — what specifically is driving that concern?'"
    },
    {
      "arc_stage": 5, "step_code": "E", "step_name": "Explain Insights",
      "strong_patterns": ["Reveals 3rd-party evidence", "Relates evidence to customer's stated situation", "Offers resources"],
      "weak_patterns": ["Claims without evidence", "Data without customer connection", "Feature repeat"],
      "hint_if_weak": "Share a clinical insight that tells the story — then connect it directly to what they told you earlier."
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
```

---

## 6. Argument Evaluator

### 6.1 Two-Layer Design

**Layer 1 — Deterministic (no LLM, every turn):**
Pattern-match rep utterance against: methodology strong/weak signal lists, COF seed terms (existing), arc stage rubric signal lists. Returns: `signals_detected[]`, `cof_flags`, `methodology_flags`. Fast, zero cost.

**Layer 2 — LLM call (Haiku, temp 0.1, ~3–4× per session avg):**
Fires only when Layer 1 signals are ambiguous OR when argument coherence cannot be determined by pattern alone (e.g., did the rep actually connect clinical to financial, or just mention both terms?). Input: rep utterance + arc stage + COF map + stage rubric. Output: structured JSON.

### 6.2 Evaluator Output Schema

```json
{
  "arc_stage": 3,
  "strong_signals": ["Connected clinical finding to OR throughput", "Used customer's own language"],
  "weak_signals": ["Did not quantify financial impact"],
  "argument_quality": "mixed",
  "cof_coverage": {"clinical": true, "operational": true, "financial": false},
  "methodology_compliance": {"step": "A — Ask (Develop)", "compliant": true},
  "persona_instruction": "Become collaborative on clinical/operational — push back: 'What does that mean for the budget?'",
  "hint_for_rep": "You've covered clinical and operational — don't leave the financial reality on the table.",
  "score_delta": 0
}
```

### 6.3 Three Consumers

1. **Persona system prompt** — `persona_instruction` injected before next AI response
2. **Rep hint layer** — `hint_for_rep` shown on screen (throttled — see 7.3)
3. **Session score record** — `score_delta` appended to `turn_scores[]` array on session

---

## 7. Rep Hint Layer

### 7.1 Display Rules

Hints shown only when one of these conditions is true:
- `argument_quality == "weak"` on current turn
- A COF domain has been missed for 2+ consecutive turns
- A methodology step has been skipped (e.g., no Recap before Explain Insights)

Max 1 hint visible at a time. Hint clears after the rep's next turn. No stacking. These are the complete throttle rules — no additional conditions apply.

### 7.2 Hint Copy Style

Phrased in the active methodology's language. For BSCI SALES: uses SALES step names. Short, actionable, non-judgmental. Example: *"Ask about the consequences before presenting the solution."* Not: *"You didn't ask a Dissect question."*

---

## 8. Grading Agent (Post-Session)

### 8.1 Inputs

- Full transcript with arc stage labels
- `turn_scores[]` — per-turn argument quality record built during session
- COF map (Domain 3)
- Grading criteria (Domain 5) — weighted dimensions + rubric
- Methodology (Domain 6) — step names for debrief vocabulary

### 8.2 LLM Call

Model: Claude Sonnet, temperature 0.3, structured output enforced. One call per session post-completion.

Estimated cost: ~2,000 tokens input + ~500 tokens output = ~$0.003 per session. Well within the $0.40 session budget.

### 8.3 Output Schema

```json
{
  "overall_score": 74,
  "dimensions": [
    {
      "id": "cof_coverage", "score": 80,
      "narrative": "You surfaced the clinical and operational picture clearly. The encrustation → OR disruption link landed. The financial reality stayed implicit — put a number on it next time."
    },
    {
      "id": "discovery_quality", "score": 85,
      "narrative": "Strong Discover questions at the open. You waited for answers before pivoting to Dissect. That patience is why she gave you the scheduling problem."
    },
    {
      "id": "argument_coherence", "score": 65,
      "narrative": "The clinical-to-operational bridge was clean. You didn't complete the chain to financial impact before presenting the solution."
    },
    {
      "id": "objection_handling", "score": 70,
      "narrative": "You Empathized and Asked before responding — that's the model. The response leaned on data, not discount. Tighten the Relate step."
    }
  ],
  "top_strength": "Discovery patience — you earned the pain point.",
  "top_improvement": "Complete the COF chain before revealing your solution.",
  "debrief_audio": true
}
```

### 8.4 Delivery Sequence

1. COF gate report shown first (instant — already computed during session)
2. Grading agent call fires in background during COF gate display (no waiting screen)
3. Dimension scores animate in with narrative text
4. Audio debrief plays in session persona's voice (TTS, existing pipeline)
5. Score saved to `completions` table with dimension breakdown

---

## 9. Content File Management (Admin Dashboard)

The admin dashboard includes a **Knowledge Base** section showing:

| Column | Value |
|--------|-------|
| File | `content/tria_stents/knowledge_base.yaml` |
| Product | Tria Ureteral Stents |
| Chunks | 18 |
| Domains covered | product (5), clinical (4), cof (3), objection (3), compliance (1), stakeholder (2) |
| Approved claims | 3 |
| Last ingested | timestamp |
| Actions | Re-ingest / View chunks / Download |

Files are editable directly in the repository. Admins add chunks by appending to the YAML source file, then trigger re-ingestion from the dashboard or CLI.

---

## 10. Adding a New Product

1. Create `content/<product_id>/knowledge_base.yaml` using the template in the existing file
2. Author Tier 2 JSONB content: `cof_map`, `argument_rubrics`, `grading_criteria`, `methodology`
3. Run `python3 scripts/validate_content.py --scenario <id>`
4. Run `python3 scripts/load_content.py --scenario <id>` to upsert JSONB columns
5. Run `python3 scripts/ingest_docs.py --product <id> --scenario <id>` to embed and store chunks
6. Smoke-test in Quick Drill preset

No code changes required to add a new product.

---

## 11. Methodology Configurations

| Methodology | Config ID | Arc Stage Mapping |
|-------------|-----------|-------------------|
| BSCI SALES (Ignite Selling) | `bsci_sales` | S→1, A(D/Di/Dev)→1-3, L→3, E→5, S→6, Resistance→4 |
| SPIN Selling | `spin` | Situation→1, Problem→2, Implication→3, Need-Payoff→5 |
| Challenger | `challenger` | Warm Up→1, Reframe→2, Rational Drowning→3, Value Prop→5 |
| Custom | `custom_<id>` | Defined per deployment |

Methodology is a JSONB column on `scenarios`. Switching methodology for a scenario requires updating the JSONB and re-running validation — no code changes.

---

## 12. Out of Scope (This Phase)

- Automatic document parsing without human review of `approved_claim` flags
- Real-time manager view of argument evaluation scores
- Multi-language methodology configurations
- Automated YAML authoring (AI-assisted content generation for Tier 2 documents)

---

*LiquidSMARTS™ — Commercial Engineering for Healthcare Technology*
*GFW Management II LLC | gunter@liquidsmarts.com*
