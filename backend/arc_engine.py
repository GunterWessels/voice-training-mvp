import logging
import re
from typing import List, Dict, Any, Optional

COF_SEEDS = {
    "clinical": ["patient","complication","outcome","infection","stent","fragment",
                 "stone","encrustation","urinary","clinical","care","safety","risk"],
    "operational": ["or","schedule","throughput","turnover","workflow","procedure",
                    "time","efficiency","volume","capacity","staff","utilization"],
    "financial": ["cost","budget","revenue","reimbursement","roi","savings",
                  "expense","margin","price","spend","financial","dollar","investment"],
    "solution": ["tria","stent","solution","product","system","platform",
                 "offer","propose","address","resolve","help","benefit"],
    "positive_signal": ["trial","pilot","vac","committee","consider","interested",
                        "explore","next step","meeting","approve","move forward"],
    "discount_defense": ["discount","lower price","price reduction","cut","cheaper","negotiate down"],
}

# SPIN question stage seeds (Situation / Problem / Implication / Need-Payoff)
SPIN_SEEDS = {
    "situation": ["how many","how often","currently","tell me about","how do you",
                  "what process","what's your","walk me through","describe your",
                  "what volume","how frequently","what does your","how is your"],
    "problem":   ["challenge","issue","problem","difficulty","concern","struggle",
                  "frustrat","pain","gap","obstacle","what's not working","what keeps",
                  "complaint","difficult","hard to","trouble"],
    "implication": ["impact","consequence","affect","result","mean for","cost you",
                    "lead to","happen when","downstream","what does that","ripple",
                    "broader effect","translates to","compounds","so when that"],
    "need_payoff": ["would it help","how important","what would it mean","value if",
                    "benefit if","solve that","what if you could","how much better",
                    "what would change","if that were fixed","ideal outcome"],
}

# Challenger insight seeds (Teach / Tailor / Take Control)
CHALLENGER_SEEDS = {
    "teach":       ["data shows","study","found that","research","evidence","actually",
                    "surprising","most hospitals","what we've seen","insight","typically",
                    "literature","benchmark","peer reviewed","our data","industry average"],
    "tailor":      ["you mentioned","you told me","based on what you said","given your",
                    "in your case","for your team","your situation","what you described",
                    "connecting back","your specific","given that you"],
    "take_control": ["specific next","next step","by when","schedule","commit",
                     "agree to","trial","vac","proposal","can we","let's set",
                     "move forward","by end of","this week","within"],
}

# SALES framework seeds (Start / Ask / Listen / Explain / Secure + Resistance layer)
SALES_SEEDS = {
    # S — Start: rep opens with a customer-focused purpose and payoff
    "start": [
        "reason for my call", "reason i'm calling", "goal today", "purpose of my call",
        "i wanted to", "i'm reaching out to", "the reason i", "what i'd like to",
        "my goal is", "i'd like to share", "i thought it would be valuable",
        "what i hope we can", "i want to make sure this is valuable for you",
    ],
    # A — Ask: Discover (current concern questions)
    "ask_discover": [
        "how often does", "what are your concerns with", "what challenges do you face",
        "tell me about your current", "how do you currently", "what does your process look like",
        "walk me through how", "how are you handling", "what's your experience with",
        "how frequently do you", "what does your team do when",
    ],
    # A — Ask: Dissect (consequence questions)
    "ask_dissect": [
        "how does that impact", "what happens if", "what's the effect on your patients",
        "what's the downstream effect", "how does that affect", "what are the consequences of",
        "what happens when", "what does that mean for", "how does that translate",
        "what's the ripple effect", "if that goes unaddressed",
    ],
    # A — Ask: Develop (solution-direction questions)
    "ask_develop": [
        "how would it help if", "what are you doing to address", "if we could solve",
        "what would it mean if", "how important would it be", "what would an ideal solution look like",
        "if that problem were fixed", "what would change if", "what would it take",
        "how would that change things", "if you had a way to",
    ],
    # L — Listen/Recap: rep paraphrases or summarizes what the buyer said
    "listen_recap": [
        "so what i'm hearing is", "let me make sure i understand", "you mentioned",
        "if i'm hearing you correctly", "so you're saying", "what i'm taking away is",
        "to recap what you shared", "so the main concern is", "let me summarize",
        "you've told me", "based on what you've said", "it sounds like",
    ],
    # E — Explain: Reveal (rep shares clinical insight or 3rd-party evidence)
    "explain_reveal": [
        "studies show", "clinical data indicates", "our research found",
        "the data shows", "peer-reviewed evidence", "a published study",
        "clinical evidence", "research demonstrates", "findings indicate",
        "our clinical data", "industry data shows", "literature suggests",
        "in a study of", "evidence from", "according to the data",
    ],
    # E — Explain: Relate (rep connects evidence back to buyer's challenge)
    "explain_relate": [
        "given what you told me about", "based on the challenge you described",
        "that's directly relevant to", "connecting back to what you said",
        "given your situation", "given the concern you raised", "in light of what you shared",
        "which maps directly to", "that ties back to", "that aligns with what you mentioned",
    ],
    # S — Secure: What (clear next action)
    "secure_what": [
        "i'll send you", "can we schedule", "the next step would be",
        "i'd like to propose", "let's set up", "what i'll do is",
        "i can get you", "i'll follow up with", "the next action is",
        "let me get you", "i want to set up", "shall we",
    ],
    # S — Secure: When (timeline specified)
    "secure_when": [
        "by friday", "next week", "before end of quarter", "by end of month",
        "this week", "within the next", "by monday", "in the next two weeks",
        "before our next call", "end of the week", "by tomorrow", "within 48 hours",
        "before the end of", "next month",
    ],
    # Resistance — Empathize (acknowledge buyer pushback)
    "resistance_empathize": [
        "i understand", "that makes sense", "i appreciate you sharing that",
        "i hear you", "that's a fair point", "i can see why", "that's understandable",
        "i get that", "i appreciate that concern",
    ],
    # Resistance — Ask (clarifying question after objection)
    "resistance_ask": [
        "help me understand", "what's driving that concern", "can you tell me more about",
        "what specifically concerns you", "what would need to be true",
        "what's behind that", "can you help me understand", "what would it take",
        "what's your concern with",
    ],
    # Resistance — Respond (direct response to the objection)
    "resistance_respond": [
        "i can address that", "here's how we handle", "that's actually",
        "let me address that directly", "the way we approach that is",
        "what i can tell you is", "here's the data on that", "our response to that is",
        "to address your concern", "here's what our experience shows",
    ],
}

CLOSED_QUESTION_STARTERS = re.compile(
    r"^\s*(is|are|do|does|did|can|will|would|have|has)\b", re.IGNORECASE
)


class ConditionEvaluator:
    def _user_turns(self, history: List[Dict]) -> List[str]:
        return [m["text"].lower() for m in history if m.get("speaker") == "user"]

    def _contains_seed(self, text: str, domain: str) -> bool:
        return any(re.search(r'\b' + re.escape(seed) + r'\b', text) for seed in COF_SEEDS[domain])

    def cof_clinical_mentioned(self, history: List[Dict]) -> bool:
        return any(self._contains_seed(t, "clinical") for t in self._user_turns(history))

    def cof_operational_mentioned(self, history: List[Dict]) -> bool:
        return any(self._contains_seed(t, "operational") for t in self._user_turns(history))

    def cof_financial_mentioned(self, history: List[Dict]) -> bool:
        return any(self._contains_seed(t, "financial") for t in self._user_turns(history))

    def _contains_spin_seed(self, text: str, stage: str) -> bool:
        return any(phrase in text for phrase in SPIN_SEEDS[stage])

    def _contains_challenger_seed(self, text: str, step: str) -> bool:
        return any(phrase in text for phrase in CHALLENGER_SEEDS[step])

    def spin_flags(self, history: List[Dict]) -> Dict[str, bool]:
        turns = self._user_turns(history)
        return {
            "situation":   any(self._contains_spin_seed(t, "situation")   for t in turns),
            "problem":     any(self._contains_spin_seed(t, "problem")     for t in turns),
            "implication": any(self._contains_spin_seed(t, "implication") for t in turns),
            "need_payoff": any(self._contains_spin_seed(t, "need_payoff") for t in turns),
        }

    def challenger_flags(self, history: List[Dict]) -> Dict[str, bool]:
        turns = self._user_turns(history)
        return {
            "teach":       any(self._contains_challenger_seed(t, "teach")       for t in turns),
            "tailor":      any(self._contains_challenger_seed(t, "tailor")      for t in turns),
            "take_control":any(self._contains_challenger_seed(t, "take_control") for t in turns),
        }

    def _contains_sales_seed(self, text: str, gate: str) -> bool:
        return any(phrase in text for phrase in SALES_SEEDS[gate])

    def sales_flags(self, history: List[Dict]) -> Dict[str, bool]:
        """Return SALES framework gate flags based on rep turns in history."""
        turns = self._user_turns(history)
        return {
            "start":                any(self._contains_sales_seed(t, "start")                for t in turns),
            "ask_discover":         any(self._contains_sales_seed(t, "ask_discover")         for t in turns),
            "ask_dissect":          any(self._contains_sales_seed(t, "ask_dissect")          for t in turns),
            "ask_develop":          any(self._contains_sales_seed(t, "ask_develop")          for t in turns),
            "listen_recap":         any(self._contains_sales_seed(t, "listen_recap")         for t in turns),
            "explain_reveal":       any(self._contains_sales_seed(t, "explain_reveal")       for t in turns),
            "explain_relate":       any(self._contains_sales_seed(t, "explain_relate")       for t in turns),
            "secure_what":          any(self._contains_sales_seed(t, "secure_what")          for t in turns),
            "secure_when":          any(self._contains_sales_seed(t, "secure_when")          for t in turns),
            "resistance_empathize": any(self._contains_sales_seed(t, "resistance_empathize") for t in turns),
            "resistance_ask":       any(self._contains_sales_seed(t, "resistance_ask")       for t in turns),
            "resistance_respond":   any(self._contains_sales_seed(t, "resistance_respond")   for t in turns),
        }

    def cof_all_mentioned(self, history: List[Dict]) -> bool:
        return (self.cof_clinical_mentioned(history) and
                self.cof_operational_mentioned(history) and
                self.cof_financial_mentioned(history))

    def open_ended_questions_count(self, history: List[Dict]) -> int:
        count = 0
        for turn in self._user_turns(history):
            if "?" in turn and not CLOSED_QUESTION_STARTERS.match(turn):
                count += 1
        return count

    def solution_presented(self, history: List[Dict]) -> bool:
        for turn in self._user_turns(history):
            has_solution_term = self._contains_seed(turn, "solution")
            word_count = len(turn.split())
            if has_solution_term and word_count >= 20:
                return True
        return False

    def objection_addressed(self, history: List[Dict]) -> bool:
        ai_turns = [m["text"].lower() for m in history if m.get("speaker") == "ai"]
        if not any("price" in t or "budget" in t or "vac" in t for t in ai_turns):
            return False
        last_user = self._user_turns(history)
        if not last_user:
            return False
        last = last_user[-1]
        return not any(seed in last for seed in COF_SEEDS["discount_defense"])

    def resolution_positive(self, history: List[Dict]) -> bool:
        ai_turns = [m["text"].lower() for m in history if m.get("speaker") == "ai"]
        if not ai_turns:
            return False
        return self._contains_seed(ai_turns[-1], "positive_signal")

    def evaluate_condition(self, condition: str, history: List[Dict]) -> bool:
        cond = condition.strip()
        if cond.startswith("open_ended_questions >="):
            try:
                n = int(cond.split(">=")[1].strip())
            except ValueError:
                logging.warning(f"arc_engine: malformed condition '{cond}' — expected integer after >=")
                return False
            return self.open_ended_questions_count(history) >= n
        mapping = {
            "cof_clinical_mentioned == true": self.cof_clinical_mentioned,
            "cof_operational_mentioned == true": self.cof_operational_mentioned,
            "cof_financial_mentioned == true": self.cof_financial_mentioned,
            "cof_all_mentioned == true": self.cof_all_mentioned,
            "solution_presented == true": self.solution_presented,
            "objection_addressed == true": self.objection_addressed,
            "resolution_positive == true": self.resolution_positive,
        }
        fn = mapping.get(cond)
        if fn is None:
            logging.warning(f"arc_engine: unknown condition string '{cond}' — stage will not advance")
            return False
        return fn(history)


class ArcStageTracker:
    def __init__(self, arc: Dict[str, Any]):
        self.stages = arc["stages"]
        self.current_stage = self.stages[0]["id"] if self.stages else 1
        self.evaluator = ConditionEvaluator()
        self.cof_flags = {"clinical": False, "operational": False, "financial": False}
        self.spin_flags = {"situation": False, "problem": False, "implication": False, "need_payoff": False}
        self.challenger_flags = {"teach": False, "tailor": False, "take_control": False}
        self.sales_flags: Dict[str, bool] = {
            "start": False, "ask_discover": False, "ask_dissect": False, "ask_develop": False,
            "listen_recap": False, "explain_reveal": False, "explain_relate": False,
            "secure_what": False, "secure_when": False,
            "resistance_empathize": False, "resistance_ask": False, "resistance_respond": False,
        }

    def evaluate(self, history: List[Dict]) -> bool:
        """Evaluate current stage unlock condition. Returns True if stage advanced.

        Design constraint: advances exactly one stage per call. Call on every
        WebSocket turn to ensure no stage is skipped. Batch catch-up not supported.
        """
        self._update_cof_flags(history)
        current = self._get_stage(self.current_stage)
        if not current:
            return False
        next_stage = self._get_stage(self.current_stage + 1)
        if not next_stage:
            return False
        condition = current.get("unlock_condition", "")
        if self.evaluator.evaluate_condition(condition, history):
            self.current_stage += 1
            return True
        return False

    def _update_cof_flags(self, history: List[Dict]):
        ev = self.evaluator
        self.cof_flags["clinical"]     = ev.cof_clinical_mentioned(history)
        self.cof_flags["operational"]  = ev.cof_operational_mentioned(history)
        self.cof_flags["financial"]    = ev.cof_financial_mentioned(history)
        self.spin_flags       = ev.spin_flags(history)
        self.challenger_flags = ev.challenger_flags(history)
        self.sales_flags      = ev.sales_flags(history)

    def _get_stage(self, stage_id: int) -> Optional[Dict]:
        return next((s for s in self.stages if s["id"] == stage_id), None)

    def get_persona_instruction(self) -> str:
        stage = self._get_stage(self.current_stage)
        return stage.get("persona_instruction", "") if stage else ""
