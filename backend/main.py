from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from pydantic import BaseModel

# Load environment variables
load_dotenv()

from ai_service import AIService
from database import Database
from cartridge_service import CartridgeService, DealContext
from elevenlabs_service import ElevenLabsService

app = FastAPI(title="Voice Training Platform MVP")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db = Database()
ai_service = AIService()
cartridge_service = CartridgeService()
elevenlabs_service = ElevenLabsService()

# In-memory WebSocket connections
connections: Dict[str, WebSocket] = {}

class SessionCreate(BaseModel):
    persona_id: str
    user_name: str = "User"

class MessageSend(BaseModel):
    text: str

class DecisionMaker(BaseModel):
    name: str
    role: str
    persona: str

class CartridgeCreate(BaseModel):
    name: str
    description: str = ""
    company_name: str
    industry: str = "Healthcare"
    deal_size: str = ""
    decision_makers: List[DecisionMaker] = []
    pain_points: List[str] = []
    value_propositions: List[str] = []
    competition: List[str] = []
    timeline: str = ""
    budget_constraints: str = ""
    technical_requirements: List[str] = []
    success_metrics: List[str] = []

# Personas
PERSONAS = {
    "cfo": {
        "id": "cfo",
        "name": "Healthcare CFO",
        "description": "Cost-focused, skeptical of new technology",
        "prompt": """You are a Healthcare CFO. You are primarily concerned with costs, ROI, and budget impact. 
        You are skeptical of new technology unless it clearly shows financial benefits. 
        Keep responses brief and focused on financial implications.""",
        "avatar": "💼"
    },
    "clinical_director": {
        "id": "clinical_director", 
        "name": "Clinical Director",
        "description": "Patient outcome focused, evidence-based decision maker",
        "prompt": """You are a Clinical Director. You prioritize patient outcomes and clinical evidence. 
        You want to see peer-reviewed studies and real-world clinical data. 
        You are cautious about changes to clinical workflow.""",
        "avatar": "🩺"
    },
    "it_director": {
        "id": "it_director",
        "name": "IT Director", 
        "description": "Security and integration focused",
        "prompt": """You are an IT Director. You are concerned with security, integration, 
        data privacy, and technical compatibility. You ask detailed technical questions 
        and worry about implementation challenges.""",
        "avatar": "💻"
    }
}

@app.get("/")
async def root():
    return {"message": "Voice Training Platform MVP"}

@app.get("/personas")
async def get_personas():
    """Get available AI personas for training"""
    return {"personas": list(PERSONAS.values())}

@app.get("/tts-info")
async def get_tts_info():
    """Get information about current TTS provider"""
    return {"provider": "elevenlabs", "status": "ready"}

@app.post("/sessions")
async def create_session(session_data: SessionCreate):
    """Create a new training session"""
    session_id = str(uuid.uuid4())
    
    if session_data.persona_id not in PERSONAS:
        raise HTTPException(status_code=400, detail="Invalid persona ID")
    
    # Create session in database
    db.create_session(
        session_id=session_id,
        persona_id=session_data.persona_id,
        user_name=session_data.user_name
    )
    
    return {
        "session_id": session_id,
        "persona": PERSONAS[session_data.persona_id]
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details and conversation history"""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.get_messages(session_id)
    
    return {
        "session": session,
        "messages": messages,
        "persona": PERSONAS.get(session["persona_id"])
    }

@app.get("/sessions")
async def get_sessions(limit: int = 10):
    """Get recent training sessions"""
    sessions = db.get_recent_sessions(limit)
    return {"sessions": sessions}

@app.get("/cartridges")
async def list_cartridges():
    """List all available practice cartridges"""
    cartridges = cartridge_service.list_cartridges()
    return {"cartridges": cartridges}

@app.post("/cartridges")
async def create_cartridge(cartridge_data: CartridgeCreate):
    """Create a new practice cartridge"""
    cartridge_id = cartridge_service.create_cartridge(
        name=cartridge_data.name,
        description=cartridge_data.description,
        deal_context=DealContext(
            company_name=cartridge_data.company_name,
            industry=cartridge_data.industry,
            deal_size=cartridge_data.deal_size,
            decision_makers=cartridge_data.decision_makers,
            pain_points=cartridge_data.pain_points,
            value_propositions=cartridge_data.value_propositions,
            competition=cartridge_data.competition,
            timeline=cartridge_data.timeline,
            budget_constraints=cartridge_data.budget_constraints,
            technical_requirements=cartridge_data.technical_requirements,
            success_metrics=cartridge_data.success_metrics
        )
    )
    return {"cartridge_id": cartridge_id}

@app.post("/cartridges/sample")
async def create_sample_cartridge():
    """Create a sample cartridge for testing"""
    cartridge_id = cartridge_service.create_sample_cartridge()
    return {"cartridge_id": cartridge_id}

@app.get("/cartridges/{cartridge_id}")
async def get_cartridge(cartridge_id: str):
    """Get cartridge details including active features"""
    cartridge_data = cartridge_service.get_cartridge_for_practice(cartridge_id)
    if not cartridge_data:
        raise HTTPException(status_code=404, detail="Cartridge not found")
    return cartridge_data

@app.put("/cartridges/{cartridge_id}/features")
async def update_cartridge_features(cartridge_id: str, features: dict):
    """Update training features for a cartridge"""
    success = cartridge_service.update_training_features(cartridge_id, features)
    if not success:
        raise HTTPException(status_code=404, detail="Cartridge not found")
    return {"status": "updated"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time conversation"""
    await websocket.accept()
    connections[session_id] = websocket
    
    # Get session info
    session = db.get_session(session_id)
    if not session:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return
    
    persona = PERSONAS.get(session["persona_id"])
    if not persona:
        await websocket.send_json({"error": "Invalid persona"})
        await websocket.close()
        return
    
    # Send ready message with persona info and TTS info
    tts_info = ai_service.tts_service.get_provider_info()
    await websocket.send_json({
        "type": "ready",
        "persona": persona,
        "session_id": session_id,
        "tts_info": tts_info
    })
    
    # Send AI greeting with high-quality audio
    greeting_response = await ai_service.generate_response_with_audio(
        persona=persona,
        conversation_history=[],
        is_greeting=True
    )
    
    # Save greeting to database
    db.add_message(
        session_id=session_id,
        speaker="ai",
        text=greeting_response["text"]
    )
    
    # Send greeting with audio data
    message_data = {
        "type": "ai_message",
        "text": greeting_response["text"],
        "tts_provider": greeting_response["tts_provider"]
    }
    
    # Add audio data if available (for ElevenLabs or OpenAI TTS)
    if greeting_response["audio"]:
        message_data["audio"] = greeting_response["audio"]
    
    await websocket.send_json(message_data)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "user_message":
                user_text = data.get("text", "")
                
                # Save user message
                db.add_message(
                    session_id=session_id,
                    speaker="user", 
                    text=user_text
                )
                
                # Get conversation history
                conversation_history = db.get_messages(session_id)
                
                # Generate AI response with audio
                ai_response = await ai_service.generate_response_with_audio(
                    persona=persona,
                    conversation_history=conversation_history,
                    user_input=user_text
                )
                
                # Save AI response
                db.add_message(
                    session_id=session_id,
                    speaker="ai",
                    text=ai_response["text"]
                )
                
                # Send AI response with audio
                message_data = {
                    "type": "ai_message",
                    "text": ai_response["text"],
                    "tts_provider": ai_response["tts_provider"]
                }
                
                # Add audio data if available
                if ai_response["audio"]:
                    message_data["audio"] = ai_response["audio"]
                
                await websocket.send_json(message_data)
                
    except WebSocketDisconnect:
        if session_id in connections:
            del connections[session_id]
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
        if session_id in connections:
            del connections[session_id]

@app.post("/sessions/{session_id}/score")
async def score_session(session_id: str):
    """Generate a simple score for the session"""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.get_messages(session_id)
    user_messages = [msg for msg in messages if msg["speaker"] == "user"]
    
    # Simple scoring based on conversation length and content
    score = min(100, len(user_messages) * 10)  # Basic scoring
    
    feedback = []
    if len(user_messages) >= 5:
        feedback.append("Good conversation length")
    if any(len(msg["text"]) > 50 for msg in user_messages):
        feedback.append("Provided detailed responses")
    if len(user_messages) < 3:
        feedback.append("Try to engage more in the conversation")
    
    # Update session with score
    db.update_session_score(session_id, score)
    
    return {
        "score": score,
        "feedback": feedback,
        "message_count": len(user_messages)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)