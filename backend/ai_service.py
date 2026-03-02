import asyncio
import httpx
import json
import os
from typing import List, Dict, Optional
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
    
    async def generate_response(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False
    ) -> str:
        """Generate AI response based on persona and conversation history"""
        
        if self.provider == "mock":
            return self._generate_mock_response(persona, is_greeting, user_input)
        
        # Build conversation context
        messages = self._build_messages(persona, conversation_history, user_input, is_greeting)
        
        try:
            if self.provider == "openai":
                return await self._call_openai(messages)
            elif self.provider == "anthropic":
                return await self._call_anthropic(messages)
        except Exception as e:
            print(f"AI API error: {e}")
            return self._generate_mock_response(persona, is_greeting, user_input)
    
    async def generate_response_with_audio(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False
    ) -> Dict:
        """Generate AI response with both text and optional audio"""
        
        # Generate text response
        text_response = await self.generate_response(
            persona, conversation_history, user_input, is_greeting
        )
        
        # Generate audio if TTS service is available
        audio_data = await self.tts_service.generate_speech(
            text=text_response,
            persona_id=persona.get("id", "default")
        )
        
        response = {
            "text": text_response,
            "audio": audio_data,
            "tts_provider": self.tts_service.provider
        }
        
        return response
    
    def _build_messages(
        self,
        persona: Dict,
        conversation_history: List[Dict],
        user_input: str = None,
        is_greeting: bool = False
    ) -> List[Dict]:
        """Build conversation messages for AI API"""
        
        messages = [
            {
                "role": "system",
                "content": f"""{persona['prompt']}
                
You are participating in a sales training simulation. The user is a MedTech sales representative 
practicing their pitch. Stay in character and respond realistically as this persona would.
Keep responses conversational and under 100 words unless specifically asked for details.
"""
            }
        ]
        
        if is_greeting:
            messages.append({
                "role": "user",
                "content": "Hello, I'd like to speak with you about a new medical technology solution that could benefit your organization."
            })
        else:
            # Add conversation history
            for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                role = "user" if msg["speaker"] == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg["text"]
                })
            
            # Add current user input
            if user_input:
                messages.append({
                    "role": "user", 
                    "content": user_input
                })
        
        return messages
    
    async def _call_openai(self, messages: List[Dict]) -> str:
        """Call OpenAI API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",  # Cost-effective model
                    "messages": messages,
                    "max_tokens": 150,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
    
    async def _call_anthropic(self, messages: List[Dict]) -> str:
        """Call Anthropic API"""
        # Extract system message
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
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-haiku-20240307",  # Cost-effective model
                    "max_tokens": 150,
                    "system": system_message,
                    "messages": user_messages
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.status_code}")
            
            result = response.json()
            return result["content"][0]["text"].strip()
    
    def _generate_mock_response(self, persona: Dict, is_greeting: bool, user_input: str = None) -> str:
        """Generate mock responses for demo purposes"""
        
        persona_id = persona["id"]
        
        if is_greeting:
            greetings = {
                "cfo": "Hello. I'm quite busy, so let's keep this brief. What's this about?",
                "clinical_director": "Good afternoon. I can spare a few minutes. What clinical solution are you proposing?",
                "it_director": "Hi there. I hope you have your security certifications ready. What system are we discussing?"
            }
            return greetings.get(persona_id, "Hello. How can I help you today?")
        
        # Generate contextual responses based on persona
        if not user_input:
            return "I'm listening. Please continue."
        
        user_lower = user_input.lower()
        
        if persona_id == "cfo":
            if "cost" in user_lower or "price" in user_lower or "budget" in user_lower:
                return "That's exactly what I need to know. What are the total costs, including implementation and training?"
            elif "roi" in user_lower or "savings" in user_lower:
                return "Show me the numbers. How quickly will we see returns on this investment?"
            else:
                return "That sounds interesting, but what's the bottom line impact on our budget?"
        
        elif persona_id == "clinical_director":
            if "patient" in user_lower or "outcome" in user_lower or "clinical" in user_lower:
                return "That's important. Do you have peer-reviewed studies showing clinical improvements?"
            elif "workflow" in user_lower:
                return "We can't disrupt our current clinical workflow. How does this integrate smoothly?"
            else:
                return "I need to see evidence-based results. What clinical data supports this?"
        
        elif persona_id == "it_director":
            if "security" in user_lower or "privacy" in user_lower:
                return "Good, security is critical. What certifications do you have? HIPAA compliance?"
            elif "integration" in user_lower or "system" in user_lower:
                return "How does this integrate with our existing EMR and IT infrastructure?"
            else:
                return "I need technical details. What are the system requirements and security protocols?"
        
        return "That's interesting. Tell me more about how this would work in practice."