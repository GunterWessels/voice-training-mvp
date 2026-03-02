import asyncio
import httpx
import json
import os
import base64
from typing import Optional, Dict

class TTSService:
    """High-quality Text-to-Speech service supporting ElevenLabs and fallbacks"""
    
    def __init__(self):
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        # Determine best available TTS provider
        if (self.elevenlabs_key and 
            self.elevenlabs_key != "placeholder_key_update_this" and
            not self.elevenlabs_key.startswith("placeholder")):
            self.provider = "elevenlabs"
        elif (self.openai_key and 
              self.openai_key != "placeholder_key_update_this" and
              not self.openai_key.startswith("placeholder")):
            self.provider = "openai"
        else:
            self.provider = "browser"  # Fallback to improved browser TTS
    
    async def generate_speech(
        self, 
        text: str, 
        persona_id: str = "default",
        voice_settings: Dict = None
    ) -> Optional[Dict]:
        """
        Generate high-quality speech audio from text
        Returns: {"audio_data": base64_audio, "content_type": "audio/mpeg"} or None for browser TTS
        """
        
        if self.provider == "elevenlabs":
            return await self._elevenlabs_tts(text, persona_id, voice_settings)
        elif self.provider == "openai":
            return await self._openai_tts(text, persona_id)
        else:
            # Return None to indicate browser should handle TTS
            return None
    
    async def _elevenlabs_tts(self, text: str, persona_id: str, voice_settings: Dict = None) -> Dict:
        """Generate speech using ElevenLabs API"""
        
        # Map personas to ElevenLabs voice IDs
        voice_map = {
            "cfo": "21m00Tcm4TlvDq8ikWAM",  # Rachel - Professional female voice
            "clinical_director": "AZnzlk1XvdvUeBnXmlld",  # Domi - Warm professional voice  
            "it_director": "EXAVITQu4vr4xnSDxMaL",  # Bella - Clear technical voice
            "default": "21m00Tcm4TlvDq8ikWAM"
        }
        
        voice_id = voice_map.get(persona_id, voice_map["default"])
        
        # Default voice settings for natural conversation
        default_settings = {
            "stability": 0.5,
            "similarity_boost": 0.5,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        if voice_settings:
            default_settings.update(voice_settings)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
                    headers={
                        "Accept": "audio/mpeg",
                        "xi-api-key": self.elevenlabs_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": default_settings
                    }
                )
                
                if response.status_code != 200:
                    print(f"ElevenLabs TTS error: {response.status_code} - {response.text}")
                    return None
                
                # Convert audio to base64
                audio_data = base64.b64encode(response.content).decode('utf-8')
                
                return {
                    "audio_data": audio_data,
                    "content_type": "audio/mpeg"
                }
                
        except Exception as e:
            print(f"ElevenLabs TTS error: {e}")
            return None
    
    async def _openai_tts(self, text: str, persona_id: str) -> Dict:
        """Generate speech using OpenAI TTS API"""
        
        # Map personas to OpenAI voices
        voice_map = {
            "cfo": "nova",  # Professional female
            "clinical_director": "alloy",  # Warm professional
            "it_director": "echo",  # Clear technical  
            "default": "nova"
        }
        
        voice = voice_map.get(persona_id, voice_map["default"])
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1",  # Fast model for real-time use
                        "input": text,
                        "voice": voice,
                        "response_format": "mp3",
                        "speed": 0.95  # Slightly slower for training
                    }
                )
                
                if response.status_code != 200:
                    print(f"OpenAI TTS error: {response.status_code}")
                    return None
                
                # Convert audio to base64
                audio_data = base64.b64encode(response.content).decode('utf-8')
                
                return {
                    "audio_data": audio_data,
                    "content_type": "audio/mpeg"
                }
                
        except Exception as e:
            print(f"OpenAI TTS error: {e}")
            return None
    
    def get_provider_info(self) -> Dict:
        """Get information about the current TTS provider"""
        provider_info = {
            "elevenlabs": {
                "name": "ElevenLabs",
                "quality": "Premium",
                "description": "High-quality, natural-sounding AI voices"
            },
            "openai": {
                "name": "OpenAI TTS",
                "quality": "High", 
                "description": "Clear, professional AI voices"
            },
            "browser": {
                "name": "Browser TTS",
                "quality": "Basic",
                "description": "Built-in browser text-to-speech (improved settings)"
            }
        }
        
        return {
            "current_provider": self.provider,
            "info": provider_info[self.provider],
            "available_providers": list(provider_info.keys())
        }