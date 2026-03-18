import json
import os
import re
from typing import List, Dict, Optional, Any

import httpx

from tts_service import TTSService


class AIService:
    def __init__(self):
        # Try to use OpenAI first, then Anthropic
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if self.openai_key and self.openai_key != "placeholder_key_update_this":
            self.provider = "openai"
        elif self.anthropic_key and self.anthropic_key != "placeholder_key_update_this":
            self.provider = "anthropic"
        else:
            # Fallback to mock responses for demo
            self.provider = "mock"

        # Initialize TTS service
        self.tts_service = TTSService()

        # Usage tracking for last AI call (populated by _call_openai / _call_anthropic)
        self._last_tokens_in = 0
        self._last_tokens_out = 0
        self._last_provider = "openai"
        self._last_model = "gpt-4o-mini"

    async def generate_response(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False,
        rag_context: Optional[Dict[str, Any]] = None,
        training_features: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate just the assistant text response (persona reply)."""
        turn = await self.generate_training_turn(
            persona=persona,
            conversation_history=conversation_history,
            user_input=user_input,
            is_greeting=is_greeting,
            rag_context=rag_context,
            training_features=training_features,
        )
        return turn["text"]

    async def generate_training_turn(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False,
        rag_context: Optional[Dict[str, Any]] = None,
        training_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a training turn.

        Returns a dict:
          {
            "text": <persona reply>,
            "coaching": <optional coaching object>,
            "feedback": <optional feedback object>
          }

        If training_features enable coaching/feedback, we request structured JSON from the model.
        """

        training_features = training_features or {}
        want_coaching = bool(training_features.get("coaching") or training_features.get("instructions"))
        want_feedback = bool(training_features.get("feedback") or training_features.get("assessment") or training_features.get("evaluation"))
        want_structured = want_coaching or want_feedback

        if self.provider == "mock":
            return self._generate_mock_turn(
                persona=persona,
                is_greeting=is_greeting,
                user_input=user_input,
                rag_context=rag_context,
                want_coaching=want_coaching,
                want_feedback=want_feedback,
            )

        messages = self._build_messages(
            persona=persona,
            conversation_history=conversation_history,
            user_input=user_input,
            is_greeting=is_greeting,
            rag_context=rag_context,
            training_features=training_features,
            structured_output=want_structured,
        )

        try:
            raw = await self._call_provider(
                messages=messages,
                max_tokens=350 if want_structured else 170,
                temperature=0.4 if want_structured else 0.7,
            )
        except Exception as e:
            print(f"AI API error: {e}")
            return self._generate_mock_turn(
                persona=persona,
                is_greeting=is_greeting,
                user_input=user_input,
                rag_context=rag_context,
                want_coaching=want_coaching,
                want_feedback=want_feedback,
            )

        if not want_structured:
            return {"text": raw.strip(), "coaching": None, "feedback": None}

        parsed = self._parse_json_safely(raw)
        if not parsed:
            # Worst-case fallback: treat entire response as the assistant reply.
            return {"text": raw.strip(), "coaching": None, "feedback": None}

        # Normalize keys
        text = (parsed.get("assistant_reply") or parsed.get("text") or "").strip()
        coaching = parsed.get("coaching") if want_coaching else None
        feedback = parsed.get("feedback") if want_feedback else None

        # If model returned empty assistant text, degrade gracefully.
        if not text:
            text = raw.strip()

        return {"text": text, "coaching": coaching, "feedback": feedback}

    async def generate_response_with_audio(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False,
        rag_context: Optional[Dict[str, Any]] = None,
        training_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate AI response with both text and optional audio (plus optional coaching/feedback)."""

        turn = await self.generate_training_turn(
            persona=persona,
            conversation_history=conversation_history,
            user_input=user_input,
            is_greeting=is_greeting,
            rag_context=rag_context,
            training_features=training_features,
        )

        # Generate audio if TTS service is available
        audio_data = await self.tts_service.generate_speech(
            text=turn["text"],
            persona_id=persona.get("id", "default"),
        )

        return {
            "text": turn["text"],
            "audio": audio_data,
            "tts_provider": self.tts_service.provider,
            "coaching": turn.get("coaching"),
            "feedback": turn.get("feedback"),
        }

    def _build_messages(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False,
        rag_context: Optional[Dict[str, Any]] = None,
        training_features: Optional[Dict[str, Any]] = None,
        structured_output: bool = False,
    ) -> List[Dict]:
        """Build conversation messages for AI API."""

        training_features = training_features or {}
        rag_context = rag_context or {}

        company_background = rag_context.get("company_background")
        decision_maker_profiles = rag_context.get("decision_maker_profiles")
        conversation_guidelines = rag_context.get("conversation_guidelines")
        selected_scenario = rag_context.get("selected_scenario")
        prompt_instructions = rag_context.get("prompt_instructions")
        # Evaluator-injected per-turn overrides (populated by argument_evaluator)
        evaluator_persona_instruction = rag_context.get("persona_instruction")
        rag_chunks = rag_context.get("rag_chunks") or []
        approved_chunks = rag_context.get("approved_chunks") or []

        difficulty_notes = []
        if training_features.get("objection_handling"):
            difficulty_notes.append("Raise realistic objections appropriate to your role.")
        if training_features.get("time_pressure"):
            difficulty_notes.append("Act time-constrained and push for concise answers.")

        system_parts = [
            persona.get("prompt", ""),
            "",
            "You are participating in a MedTech sales training simulation.",
            "The user is a MedTech sales representative practicing their pitch.",
            "Stay in character and respond realistically as this persona would.",
            "Keep responses conversational and under 120 words unless asked for details.",
        ]

        if difficulty_notes:
            system_parts.append("\nDifficulty:\n- " + "\n- ".join(difficulty_notes))

        if prompt_instructions:
            system_parts.append(
                "\nAdditional training instructions (apply these strictly while staying in persona):\n" + str(prompt_instructions).strip()
            )

        if company_background:
            system_parts.append("\nDeal context (use this to ground your objections and questions):\n" + str(company_background).strip())

        if decision_maker_profiles:
            system_parts.append("\nDecision makers:\n" + str(decision_maker_profiles).strip())

        if selected_scenario:
            scenario_lines = []
            if selected_scenario.get("name"):
                scenario_lines.append(f"Name: {selected_scenario.get('name')}")
            if selected_scenario.get("type"):
                scenario_lines.append(f"Type: {selected_scenario.get('type')}")
            if selected_scenario.get("difficulty"):
                scenario_lines.append(f"Difficulty: {selected_scenario.get('difficulty')}")
            if selected_scenario.get("duration_minutes") is not None:
                scenario_lines.append(f"Duration: {selected_scenario.get('duration_minutes')} minutes")
            if selected_scenario.get("description"):
                scenario_lines.append(f"Description: {selected_scenario.get('description')}")
            if selected_scenario.get("context"):
                scenario_lines.append("Context: " + str(selected_scenario.get("context")))
            if selected_scenario.get("success_criteria"):
                scenario_lines.append("Success criteria: " + str(selected_scenario.get("success_criteria")))

            system_parts.append("\nSelected scenario (role-play situation):\n" + "\n".join(scenario_lines))

        if conversation_guidelines:
            system_parts.append("\nTraining mode guidelines:\n" + str(conversation_guidelines).strip())

        # Per-turn evaluator persona override (from argument_evaluator based on rep quality)
        if evaluator_persona_instruction:
            system_parts.append(
                "\nCurrent stage behavior instruction (override default disposition for this turn):\n"
                + str(evaluator_persona_instruction).strip()
            )

        # Tier 1 RAG: approved claims take precedence; all chunks provide grounding
        if approved_chunks:
            system_parts.append(
                "\nApproved clinical/product claims you may reference (cite accurately, do not fabricate):\n"
                + "\n".join(f"- {c}" for c in approved_chunks[:3])
            )
        elif rag_chunks:
            system_parts.append(
                "\nRelevant product/clinical context (use to ground your responses):\n"
                + "\n".join(f"- {c}" for c in rag_chunks[:3])
            )

        if structured_output:
            system_parts.append(
                "\nOUTPUT FORMAT (strict):\n"
                "Return ONLY a valid JSON object with these keys:\n"
                "- assistant_reply: string (in persona voice)\n"
                "- coaching: object|null (sales coach voice to the user)\n"
                "  - suggestions: string[]\n"
                "  - improvements: string[]\n"
                "- feedback: object|null (sales coach evaluation)\n"
                "  - score: integer 0-100\n"
                "  - strengths: string[]\n"
                "  - areas_for_improvement: string[]\n"
                "If coaching is not appropriate, set coaching to null. If feedback is not appropriate, set feedback to null."
            )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": "\n".join([p for p in system_parts if p is not None])}
        ]

        if is_greeting:
            # Use deal context if we have it to avoid generic openings.
            deal_ctx = rag_context.get("deal_context") or {}
            company_name = deal_ctx.get("company_name")
            pain_points = deal_ctx.get("pain_points") or []
            pain_point_hint = pain_points[0] if pain_points else None

            scenario = rag_context.get("selected_scenario") or {}
            scenario_name = scenario.get("name")

            greeting_line = "Hello, I'd like to speak with you about a new medical technology solution that could benefit your organization."
            if company_name and pain_point_hint:
                greeting_line = (
                    f"Hello, I'd like to speak with you about a solution that could help {company_name} with {pain_point_hint}."
                )
            elif company_name:
                greeting_line = f"Hello, I'd like to speak with you about a solution that could benefit {company_name}."

            if scenario_name:
                greeting_line += f" For this practice, let's focus on: {scenario_name}."

            messages.append({"role": "user", "content": greeting_line})
            return messages

        # Add conversation history (last N messages)
        for msg in conversation_history[-8:]:
            role = "user" if msg.get("speaker") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("text", "")})

        # Add current user input
        if user_input:
            messages.append({"role": "user", "content": user_input})

        return messages

    async def _call_provider(self, messages: List[Dict], max_tokens: int, temperature: float) -> str:
        if self.provider == "openai":
            return await self._call_openai(messages, max_tokens=max_tokens, temperature=temperature)
        if self.provider == "anthropic":
            return await self._call_anthropic(messages, max_tokens=max_tokens)
        raise RuntimeError(f"Unknown provider: {self.provider}")

    async def _call_openai(self, messages: List[Dict], max_tokens: int = 150, temperature: float = 0.7) -> str:
        """Call OpenAI API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} {response.text}")

            result = response.json()
            usage = result.get("usage", {})
            self._last_tokens_in = usage.get("prompt_tokens", 0)
            self._last_tokens_out = usage.get("completion_tokens", 0)
            self._last_provider = "openai"
            self._last_model = "gpt-4o-mini"
            return result["choices"][0]["message"]["content"].strip()

    async def _call_anthropic(self, messages: List[Dict], max_tokens: int = 150) -> str:
        """Call Anthropic API."""
        system_message = ""
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": max_tokens,
                    "system": system_message,
                    "messages": user_messages,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.status_code} {response.text}")

            result = response.json()
            usage = result.get("usage", {})
            self._last_tokens_in = usage.get("input_tokens", 0)
            self._last_tokens_out = usage.get("output_tokens", 0)
            self._last_provider = "anthropic"
            self._last_model = "claude-3-haiku-20240307"
            return result["content"][0]["text"].strip()

    def _parse_json_safely(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON object from a model response.

        Models sometimes wrap JSON in prose. We attempt a strict parse first,
        then try to extract the first {...} block.
        """
        raw = (raw or "").strip()
        if not raw:
            return None

        # Strict attempt
        try:
            if raw.startswith("{") and raw.endswith("}"):
                return json.loads(raw)
        except Exception:
            pass

        # Extract first JSON object
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _generate_mock_turn(
        self,
        persona: Dict,
        is_greeting: bool,
        user_input: str = None,
        rag_context: Optional[Dict[str, Any]] = None,
        want_coaching: bool = False,
        want_feedback: bool = False,
    ) -> Dict[str, Any]:
        """Generate mock responses for demo purposes."""

        persona_id = persona.get("id", "default")
        deal_ctx = (rag_context or {}).get("deal_context") or {}
        company = deal_ctx.get("company_name")

        if is_greeting:
            base = {
                "cfo": "Hello. I'm quite busy, so let's keep this brief. What's this about?",
                "clinical_director": "Good afternoon. I can spare a few minutes. What clinical solution are you proposing?",
                "it_director": "Hi. Before we go far, I need to understand the security and integration implications.",
                "ceo": "Hello. Give me the executive summary and the strategic impact.",
            }.get(persona_id, "Hello. How can I help you today?")

            if company:
                base = base.replace("Hello", f"Hello from {company}")

            return {"text": base, "coaching": None, "feedback": None}

        if not user_input:
            return {"text": "I'm listening. Please continue.", "coaching": None, "feedback": None}

        user_lower = user_input.lower()

        # Persona-ish replies
        if persona_id == "cfo":
            if any(k in user_lower for k in ["cost", "price", "budget"]):
                reply = "What are the total costs, including implementation and training?"
            elif any(k in user_lower for k in ["roi", "savings", "payback"]):
                reply = "Show me the ROI and how quickly we get payback."
            else:
                reply = "What's the budget impact and how do you justify it?"
        elif persona_id == "clinical_director":
            if any(k in user_lower for k in ["patient", "outcome", "clinical"]):
                reply = "Do you have peer-reviewed evidence showing improved outcomes?"
            elif "workflow" in user_lower:
                reply = "How does this fit our workflow without disrupting care?"
            else:
                reply = "What clinical evidence supports this, and what changes for our staff?"
        elif persona_id == "it_director":
            if any(k in user_lower for k in ["security", "hipaa", "privacy"]):
                reply = "What security controls and compliance posture do you have?"
            elif any(k in user_lower for k in ["integration", "emr", "epic"]):
                reply = "How does this integrate with our EMR and identity systems?"
            else:
                reply = "Give me the technical requirements and implementation plan."
        elif persona_id == "ceo":
            reply = "What's the strategic upside, the risks, and the timeline to impact?"
        else:
            reply = "That's interesting. Tell me more about how this would work in practice."

        coaching = None
        feedback = None

        if want_coaching:
            coaching = {
                "suggestions": [
                    "Anchor your next point to a specific pain point from the cartridge.",
                    "Ask a short discovery question before presenting more features.",
                ],
                "improvements": [
                    "State a concrete business outcome (time, money, risk).",
                ],
            }

        if want_feedback:
            # Lightweight heuristic
            score = 70
            if company and company.lower() in user_lower:
                score += 10
            if "?" in user_input:
                score += 5
            feedback = {
                "score": min(100, score),
                "strengths": ["Clear articulation"],
                "areas_for_improvement": ["Tighten the value message", "Ask for a next step"],
            }

        return {"text": reply, "coaching": coaching, "feedback": feedback}
