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
        self.cof_flags["clinical"] = ev.cof_clinical_mentioned(history)
        self.cof_flags["operational"] = ev.cof_operational_mentioned(history)
        self.cof_flags["financial"] = ev.cof_financial_mentioned(history)

    def _get_stage(self, stage_id: int) -> Optional[Dict]:
        return next((s for s in self.stages if s["id"] == stage_id), None)

    def get_persona_instruction(self) -> str:
        stage = self._get_stage(self.current_stage)
        return stage.get("persona_instruction", "") if stage else ""
