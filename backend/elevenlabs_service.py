import os
import httpx
import asyncio
import tempfile
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ElevenLabsService:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Optimized voice mappings for different persona types
        self.persona_voices = {
            "cfo": {
                "voice_id": "ErXwobaYiN019PkySvjV",  # Antoni - authoritative male
                "name": "Antoni",
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.40,  # More serious tone
            },
            "clinical_director": {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Sarah - professional female
                "name": "Sarah", 
                "stability": 0.80,
                "similarity_boost": 0.90,
                "style": 0.60,  # Calm, clinical tone
            },
            "it_director": {
                "voice_id": "VR6AewLTigWG4xSOukaG",  # Josh - tech-savvy male
                "name": "Josh",
                "stability": 0.70,
                "similarity_boost": 0.88,
                "style": 0.50,  # Analytical tone
            },
            "sales_rep": {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel - energetic female
                "name": "Rachel",
                "stability": 0.65,
                "similarity_boost": 0.80,
                "style": 0.75,  # Enthusiastic tone
            },
            "coach": {
                "voice_id": "29vD33N1CtxCmqQRPOHJ",  # Drew - supportive male
                "name": "Drew",
                "stability": 0.85,
                "similarity_boost": 0.90,
                "style": 0.65,  # Encouraging tone
            }
        }
        
        # Default fallback voice
        self.default_voice = {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
            "name": "Rachel",
            "stability": 0.75,
            "similarity_boost": 0.85,
            "style": 0.60
        }

    async def text_to_speech(
        self, 
        text: str, 
        persona_id: str = None,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """Convert text to speech using ElevenLabs API"""
        
        if not self.api_key:
            logger.warning("ElevenLabs API key not found, cannot generate speech")
            return None
        
        if not text or not text.strip():
            return None
        
        # Get voice configuration for persona
        voice_config = self.persona_voices.get(persona_id, self.default_voice)
        
        # Override with custom settings if provided
        if voice_settings:
            voice_config = {**voice_config, **voice_settings}
        
        # Prepare request
        url = f"{self.base_url}/text-to-speech/{voice_config['voice_id']}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": voice_config.get("stability", 0.75),
                "similarity_boost": voice_config.get("similarity_boost", 0.85),
                "style": voice_config.get("style", 0.60),
                "use_speaker_boost": True
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"ElevenLabs API error {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None

    async def generate_speech_file(
        self, 
        text: str, 
        persona_id: str = None,
        output_format: str = "mp3"
    ) -> Optional[str]:
        """Generate speech and save to temporary file"""
        
        audio_content = await self.text_to_speech(text, persona_id)
        
        if not audio_content:
            return None
        
        try:
            # Create temporary file
            suffix = f".{output_format}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_content)
                temp_path = temp_file.name
                
            return temp_path
            
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            return None

    def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available voices configured for personas"""
        return {
            persona: {
                "voice_id": config["voice_id"],
                "name": config["name"],
                "description": f"Optimized for {persona.replace('_', ' ').title()}"
            }
            for persona, config in self.persona_voices.items()
        }

    async def get_voice_settings(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get voice settings from ElevenLabs API"""
        
        if not self.api_key:
            return None
            
        url = f"{self.base_url}/voices/{voice_id}/settings"
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Error getting voice settings: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching voice settings: {str(e)}")
            return None

    async def clone_voice_preview(
        self,
        text: str,
        voice_description: str,
        voice_labels: Dict[str, str] = None
    ) -> Optional[bytes]:
        """Generate a preview using voice design (instant voice cloning)"""
        
        if not self.api_key:
            return None
            
        url = f"{self.base_url}/text-to-speech"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Voice design payload
        payload = {
            "text": text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.6,
                "use_speaker_boost": True
            },
            "voice_design": {
                "description": voice_description,
                "labels": voice_labels or {
                    "accent": "american",
                    "description": "professional",
                    "age": "middle_aged",
                    "gender": "male"
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"Voice design error {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error with voice design: {str(e)}")
            return None

    def optimize_voice_for_content(self, content_type: str, persona_id: str) -> Dict[str, float]:
        """Optimize voice settings based on content type"""
        
        base_settings = self.persona_voices.get(persona_id, self.default_voice)
        
        # Content-specific adjustments
        adjustments = {
            "coaching": {
                "stability": 0.85,  # More stable for coaching
                "style": 0.70,      # More expressive
            },
            "objection": {
                "stability": 0.70,  # Slightly less stable for pushback
                "style": 0.45,      # More serious/resistant
            },
            "question": {
                "stability": 0.75,
                "style": 0.65,      # Slightly questioning tone
            },
            "explanation": {
                "stability": 0.80,  # Clear and stable
                "style": 0.55,      # Professional
            },
            "enthusiasm": {
                "stability": 0.65,  # Less stable for energy
                "style": 0.80,      # More expressive
            }
        }
        
        content_adjust = adjustments.get(content_type, {})
        
        return {
            "stability": content_adjust.get("stability", base_settings["stability"]),
            "similarity_boost": base_settings["similarity_boost"],
            "style": content_adjust.get("style", base_settings["style"])
        }

    async def batch_generate_speech(
        self,
        texts: list,
        persona_id: str,
        content_types: list = None
    ) -> list:
        """Generate speech for multiple texts efficiently"""
        
        if not texts:
            return []
        
        results = []
        content_types = content_types or ["explanation"] * len(texts)
        
        # Process in batches to avoid rate limiting
        batch_size = 5
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_types = content_types[i:i + batch_size]
            
            # Create coroutines for batch
            tasks = []
            for text, content_type in zip(batch_texts, batch_types):
                voice_settings = self.optimize_voice_for_content(content_type, persona_id)
                task = self.text_to_speech(text, persona_id, voice_settings)
                tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Rate limiting delay
            if i + batch_size < len(texts):
                await asyncio.sleep(1)  # 1 second between batches
        
        return results