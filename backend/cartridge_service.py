import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path

@dataclass
class DealContext:
    """Deal-specific context for practice scenarios"""
    company_name: str
    industry: str
    deal_size: str
    decision_makers: List[Dict[str, str]]  # [{"name": "John Smith", "role": "CFO", "persona": "cfo"}]
    pain_points: List[str]
    value_propositions: List[str]
    competition: List[str]
    timeline: str
    budget_constraints: str
    technical_requirements: List[str]
    success_metrics: List[str]

@dataclass
class TrainingFeatures:
    """Toggleable training features"""
    instructions: bool = True
    coaching: bool = True
    feedback: bool = True
    assessment: bool = False
    evaluation: bool = False
    practice_loops: bool = True
    objection_handling: bool = True
    time_pressure: bool = False
    difficulty_scaling: bool = True

@dataclass
class PromptCartridge:
    """Reusable prompt / instruction set that can be attached to practice cartridges"""
    id: str
    name: str
    description: str
    prompt_text: str
    created_at: datetime
    updated_at: datetime
    owner: str = "user"


@dataclass
class PracticeCartridge:
    """Complete practice scenario with context and features"""
    id: str
    name: str
    description: str
    deal_context: DealContext
    features: TrainingFeatures
    scenarios: List[Dict[str, Any]]  # Practice scenarios
    created_at: datetime
    updated_at: datetime
    owner: str = "user"
    prompt_cartridge_id: Optional[str] = None

class CartridgeService:
    def __init__(self, db_path: str = "cartridges.db"):
        # Normalize DB path so running from different working directories is consistent.
        p = Path(db_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent / p
        self.db_path = str(p)
        self.init_database()

    def init_database(self):
        """Initialize cartridge database (and lightweight migrations)."""
        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cartridges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                deal_context TEXT,  -- JSON
                features TEXT,      -- JSON
                scenarios TEXT,     -- JSON
                created_at TEXT,
                updated_at TEXT,
                owner TEXT DEFAULT 'user',
                prompt_cartridge_id TEXT
            )
            """
        )

        # Lightweight migration: add prompt_cartridge_id if missing
        cur = conn.execute("PRAGMA table_info(cartridges)")
        cols = {row[1] for row in cur.fetchall()}
        if "prompt_cartridge_id" not in cols:
            conn.execute("ALTER TABLE cartridges ADD COLUMN prompt_cartridge_id TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_cartridges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                prompt_text TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                owner TEXT DEFAULT 'user'
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_sessions (
                id TEXT PRIMARY KEY,
                cartridge_id TEXT,
                started_at TEXT,
                ended_at TEXT,
                performance_data TEXT,  -- JSON
                feedback TEXT,          -- JSON
                score INTEGER,
                FOREIGN KEY (cartridge_id) REFERENCES cartridges (id)
            )
            """
        )

        conn.commit()
        conn.close()

    def create_cartridge(
        self,
        name: str,
        description: str,
        deal_context: DealContext,
        features: TrainingFeatures = None,
        scenarios: List[Dict[str, Any]] = None,
        prompt_cartridge_id: Optional[str] = None,
    ) -> str:
        """Create a new practice cartridge"""
        
        cartridge_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if features is None:
            features = TrainingFeatures()
        
        if scenarios is None:
            scenarios = self._generate_default_scenarios(deal_context)
        
        cartridge = PracticeCartridge(
            id=cartridge_id,
            name=name,
            description=description,
            deal_context=deal_context,
            features=features,
            scenarios=scenarios,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO cartridges (id, name, description, deal_context, features, scenarios, created_at, updated_at, prompt_cartridge_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cartridge_id,
                name,
                description,
                json.dumps(asdict(deal_context)),
                json.dumps(asdict(features)),
                json.dumps(scenarios),
                now,
                now,
                prompt_cartridge_id,
            ),
        )
        conn.commit()
        conn.close()
        
        return cartridge_id

    def get_cartridge(self, cartridge_id: str) -> Optional[PracticeCartridge]:
        """Get cartridge by ID"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM cartridges WHERE id = ?", (cartridge_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return PracticeCartridge(
            id=row[0],
            name=row[1],
            description=row[2],
            deal_context=DealContext(**json.loads(row[3])),
            features=TrainingFeatures(**json.loads(row[4])),
            scenarios=json.loads(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            owner=row[8] if len(row) > 8 else "user",
            prompt_cartridge_id=row[9] if len(row) > 9 else None,
        )

    def list_cartridges(self, owner: str = "user") -> List[Dict[str, Any]]:
        """List all cartridges for a user"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT id, name, description, created_at, updated_at, prompt_cartridge_id
            FROM cartridges
            WHERE owner = ?
            ORDER BY updated_at DESC
            """,
            (owner,),
        )
        
        cartridges = []
        for row in cursor.fetchall():
            cartridges.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                    "prompt_cartridge_id": row[5],
                }
            )
        
        conn.close()
        return cartridges

    # -------------------------
    # Prompt Cartridges (reusable instruction sets)
    # -------------------------

    def create_prompt_cartridge(
        self,
        name: str,
        description: str,
        prompt_text: str,
        owner: str = "user",
    ) -> str:
        prompt_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO prompt_cartridges (id, name, description, prompt_text, created_at, updated_at, owner)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (prompt_id, name, description, prompt_text, now, now, owner),
        )
        conn.commit()
        conn.close()
        return prompt_id

    def list_prompt_cartridges(self, owner: str = "user") -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT id, name, description, created_at, updated_at
            FROM prompt_cartridges
            WHERE owner = ?
            ORDER BY updated_at DESC
            """,
            (owner,),
        )

        out: List[Dict[str, Any]] = []
        for row in cursor.fetchall():
            out.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
            )

        conn.close()
        return out

    def get_prompt_cartridge(self, prompt_cartridge_id: str) -> Optional[PromptCartridge]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, name, description, prompt_text, created_at, updated_at, owner FROM prompt_cartridges WHERE id = ?",
            (prompt_cartridge_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return PromptCartridge(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            prompt_text=row[3] or "",
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
            owner=row[6] if len(row) > 6 else "user",
        )

    def attach_prompt_cartridge(self, cartridge_id: str, prompt_cartridge_id: Optional[str]) -> bool:
        """Attach (or clear) a prompt cartridge on a practice cartridge."""

        if prompt_cartridge_id:
            pc = self.get_prompt_cartridge(prompt_cartridge_id)
            if not pc:
                return False

        conn = sqlite3.connect(self.db_path)
        result = conn.execute(
            """
            UPDATE cartridges
            SET prompt_cartridge_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (prompt_cartridge_id, datetime.now().isoformat(), cartridge_id),
        )
        success = result.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def update_cartridge_features(self, cartridge_id: str, features: Any) -> bool:
        """Update feature toggles for a cartridge.

        Accepts either a TrainingFeatures dataclass or a plain dict (from the API).
        """

        if isinstance(features, dict):
            features_obj = TrainingFeatures(**features)
        elif isinstance(features, TrainingFeatures):
            features_obj = features
        else:
            raise TypeError("features must be a dict or TrainingFeatures")

        conn = sqlite3.connect(self.db_path)
        result = conn.execute(
            """
            UPDATE cartridges
            SET features = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(asdict(features_obj)),
                datetime.now().isoformat(),
                cartridge_id,
            ),
        )

        success = result.rowcount > 0
        conn.commit()
        conn.close()

        return success

    # Backwards-compatible alias (some parts of the codebase call this name)
    def update_training_features(self, cartridge_id: str, features: Any) -> bool:
        return self.update_cartridge_features(cartridge_id, features)

    def _generate_default_scenarios(self, deal_context: DealContext) -> List[Dict[str, Any]]:
        """Generate default practice scenarios based on deal context"""
        
        scenarios = []
        
        # Opening pitch scenario
        scenarios.append({
            "id": str(uuid.uuid4()),
            "name": "Opening Pitch",
            "type": "introduction",
            "description": f"Introduce your solution to {deal_context.company_name}",
            "duration_minutes": 5,
            "difficulty": "easy",
            "context": {
                "company": deal_context.company_name,
                "industry": deal_context.industry,
                "key_challenges": deal_context.pain_points[:2]
            },
            "success_criteria": [
                "Clearly state value proposition",
                "Connect to specific pain points",
                "Establish credibility"
            ],
            "personas": [dm for dm in deal_context.decision_makers if dm.get("persona")]
        })
        
        # Objection handling scenarios
        for i, decision_maker in enumerate(deal_context.decision_makers):
            if decision_maker.get("persona"):
                scenarios.append({
                    "id": str(uuid.uuid4()),
                    "name": f"Objection Handling - {decision_maker['role']}",
                    "type": "objection_handling",
                    "description": f"Address concerns from {decision_maker['name']} ({decision_maker['role']})",
                    "duration_minutes": 8,
                    "difficulty": "medium",
                    "context": {
                        "persona": decision_maker["persona"],
                        "role": decision_maker["role"],
                        "name": decision_maker["name"],
                        "likely_objections": self._get_persona_objections(decision_maker["persona"], deal_context)
                    },
                    "success_criteria": [
                        "Acknowledge concerns",
                        "Provide specific evidence",
                        "Gain commitment to next step"
                    ]
                })
        
        # Value justification scenario
        scenarios.append({
            "id": str(uuid.uuid4()),
            "name": "ROI Justification",
            "type": "value_justification", 
            "description": f"Justify ${deal_context.deal_size} investment",
            "duration_minutes": 10,
            "difficulty": "hard",
            "context": {
                "deal_size": deal_context.deal_size,
                "value_propositions": deal_context.value_propositions,
                "success_metrics": deal_context.success_metrics,
                "timeline": deal_context.timeline
            },
            "success_criteria": [
                "Present clear ROI calculation",
                "Address budget constraints",
                "Link to business outcomes"
            ],
            "personas": [dm for dm in deal_context.decision_makers if dm.get("persona") == "cfo"]
        })
        
        # Technical deep dive scenario (if technical requirements exist)
        if deal_context.technical_requirements:
            scenarios.append({
                "id": str(uuid.uuid4()),
                "name": "Technical Integration Discussion",
                "type": "technical_discussion",
                "description": "Address technical requirements and integration concerns",
                "duration_minutes": 12,
                "difficulty": "hard",
                "context": {
                    "requirements": deal_context.technical_requirements,
                    "existing_systems": "Legacy EMR systems",
                    "security_concerns": ["HIPAA compliance", "Data encryption", "Access controls"]
                },
                "success_criteria": [
                    "Demonstrate technical understanding",
                    "Address integration complexity",
                    "Provide implementation timeline"
                ],
                "personas": [dm for dm in deal_context.decision_makers if dm.get("persona") == "it_director"]
            })
        
        # Closing scenario
        scenarios.append({
            "id": str(uuid.uuid4()),
            "name": "Deal Closing",
            "type": "closing",
            "description": "Navigate final negotiations and secure commitment",
            "duration_minutes": 15,
            "difficulty": "expert",
            "context": {
                "deal_value": deal_context.deal_size,
                "timeline_pressure": deal_context.timeline,
                "competition": deal_context.competition,
                "decision_committee": deal_context.decision_makers
            },
            "success_criteria": [
                "Handle final objections",
                "Create urgency",
                "Secure written commitment"
            ],
            "personas": deal_context.decision_makers
        })
        
        return scenarios

    def _get_persona_objections(self, persona: str, deal_context: DealContext) -> List[str]:
        """Generate likely objections based on persona type"""
        
        objections = {
            "cfo": [
                f"${deal_context.deal_size} seems expensive for our current budget",
                "What's the real ROI timeline? I need concrete numbers",
                "How does this compare to other cost-saving initiatives?",
                "We need to see at least 15% cost reduction in year one"
            ],
            "clinical_director": [
                "Will this disrupt our current clinical workflows?",
                "Do you have peer-reviewed studies on patient outcomes?",
                "Our staff is already overworked - how much training is required?",
                "What happens if the technology fails during patient care?"
            ],
            "it_director": [
                "How does this integrate with our Epic EMR system?",
                "What are the cybersecurity implications?",
                "Do you support our existing network infrastructure?",
                "What's your disaster recovery and backup strategy?"
            ],
            "ceo": [
                "How does this align with our 3-year strategic plan?",
                "What competitive advantages does this provide?",
                "Can you guarantee the implementation timeline?",
                "How will this impact our patient satisfaction scores?"
            ]
        }
        
        return objections.get(persona, ["I need more information to make this decision"])

    def get_cartridge_for_practice(self, cartridge_id: str) -> Dict[str, Any]:
        """Get cartridge data optimized for practice session"""
        
        cartridge = self.get_cartridge(cartridge_id)
        if not cartridge:
            return None
        
        # Build RAG context for AI
        rag_context = {
            "deal_context": asdict(cartridge.deal_context),
            "training_features": asdict(cartridge.features),
            "available_scenarios": cartridge.scenarios,
            "company_background": self._build_company_background(cartridge.deal_context),
            "decision_maker_profiles": self._build_decision_maker_profiles(cartridge.deal_context.decision_makers),
            "conversation_guidelines": self._build_conversation_guidelines(cartridge.features),
        }

        prompt_cartridge = None
        if getattr(cartridge, "prompt_cartridge_id", None):
            pc = self.get_prompt_cartridge(cartridge.prompt_cartridge_id)
            if pc:
                prompt_cartridge = asdict(pc)
                rag_context["prompt_instructions"] = pc.prompt_text
                rag_context["prompt_cartridge"] = {"id": pc.id, "name": pc.name, "description": pc.description}

        return {
            "cartridge": asdict(cartridge),
            "rag_context": rag_context,
            "active_features": asdict(cartridge.features),
            "prompt_cartridge": prompt_cartridge,
        }

    def _build_company_background(self, deal_context: DealContext) -> str:
        """Build comprehensive company background for RAG"""
        
        return f"""
Company: {deal_context.company_name}
Industry: {deal_context.industry}
Deal Size: {deal_context.deal_size}
Timeline: {deal_context.timeline}
Budget Constraints: {deal_context.budget_constraints}

Pain Points:
{chr(10).join(f"- {point}" for point in deal_context.pain_points)}

Value Propositions:
{chr(10).join(f"- {prop}" for prop in deal_context.value_propositions)}

Technical Requirements:
{chr(10).join(f"- {req}" for req in deal_context.technical_requirements)}

Success Metrics:
{chr(10).join(f"- {metric}" for metric in deal_context.success_metrics)}

Competition:
{chr(10).join(f"- {comp}" for comp in deal_context.competition)}
        """.strip()

    def _build_decision_maker_profiles(self, decision_makers: List[Dict[str, str]]) -> str:
        """Build decision maker profiles for RAG"""
        
        profiles = []
        for dm in decision_makers:
            profile = f"{dm['name']} - {dm['role']}"
            if dm.get('persona'):
                profile += f" (Persona: {dm['persona']})"
            profiles.append(profile)
        
        return "\n".join(profiles)

    def _build_conversation_guidelines(self, features: TrainingFeatures) -> str:
        """Build conversation guidelines based on active features"""
        
        guidelines = []
        
        if features.instructions:
            guidelines.append("Provide clear instructions and guidance during practice")
        
        if features.coaching:
            guidelines.append("Offer real-time coaching and suggestions")
        
        if features.feedback:
            guidelines.append("Give specific feedback after responses")
        
        if features.assessment:
            guidelines.append("Assess performance against objective criteria")
        
        if features.evaluation:
            guidelines.append("Provide detailed performance evaluation")
        
        if features.practice_loops:
            guidelines.append("Allow practice repetition for improvement")
        
        if features.objection_handling:
            guidelines.append("Focus on objection handling skills")
        
        if features.time_pressure:
            guidelines.append("Add time pressure to increase difficulty")
        
        if features.difficulty_scaling:
            guidelines.append("Adjust difficulty based on performance")
        
        return "\n".join(guidelines)

    def create_sample_cartridge(self) -> str:
        """Create a sample cartridge for testing"""
        
        deal_context = DealContext(
            company_name="Regional Medical Center",
            industry="Healthcare",
            deal_size="$2.5M",
            decision_makers=[
                {"name": "Sarah Johnson", "role": "CFO", "persona": "cfo"},
                {"name": "Dr. Michael Chen", "role": "Clinical Director", "persona": "clinical_director"},
                {"name": "Robert Kim", "role": "IT Director", "persona": "it_director"}
            ],
            pain_points=[
                "High readmission rates driving penalties",
                "Manual discharge planning processes",
                "Poor care coordination between departments",
                "Lack of real-time patient data visibility"
            ],
            value_propositions=[
                "Reduce readmissions by 25% through predictive analytics",
                "Automate discharge planning workflow",
                "Integrate all department communications",
                "Provide real-time patient dashboards"
            ],
            competition=["Epic MyChart", "Cerner PowerChart", "Allscripts"],
            timeline="6 months implementation",
            budget_constraints="Must show ROI within 18 months",
            technical_requirements=[
                "HIPAA compliance",
                "Epic EMR integration", 
                "Single sign-on (SSO)",
                "Mobile device support",
                "Real-time data sync"
            ],
            success_metrics=[
                "25% reduction in readmissions",
                "50% faster discharge planning",
                "90% staff adoption rate",
                "15% cost savings in year one"
            ]
        )
        
        features = TrainingFeatures(
            instructions=True,
            coaching=True,
            feedback=True,
            assessment=False,
            evaluation=False,
            practice_loops=True,
            objection_handling=True,
            time_pressure=False,
            difficulty_scaling=True
        )
        
        return self.create_cartridge(
            name="Regional Medical Center - Care Coordination Platform",
            description="Practice selling a $2.5M care coordination platform to a regional medical center",
            deal_context=deal_context,
            features=features
        )

    def start_practice_session(self, cartridge_id: str) -> str:
        """Start a new practice session"""
        
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO practice_sessions (id, cartridge_id, started_at)
            VALUES (?, ?, ?)
        """, (session_id, cartridge_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return session_id

    def end_practice_session(
        self,
        session_id: str,
        performance_data: Dict[str, Any],
        feedback: Dict[str, Any],
        score: int
    ) -> bool:
        """End practice session with results"""
        
        conn = sqlite3.connect(self.db_path)
        result = conn.execute("""
            UPDATE practice_sessions 
            SET ended_at = ?, performance_data = ?, feedback = ?, score = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            json.dumps(performance_data),
            json.dumps(feedback),
            score,
            session_id
        ))
        
        success = result.rowcount > 0
        conn.commit()
        conn.close()
        
        return success