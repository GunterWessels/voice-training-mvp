# 🎙️ Enhanced Voice Training Platform - Quick Start

Your voice training platform has been **dramatically enhanced** with ElevenLabs TTS and cartridge-style practice spaces. Here's what's new and how to use it.

## 🚀 What's New

### ✅ **ElevenLabs Integration**
- **Natural voice quality** replaces terrible browser TTS
- **Persona-optimized voices** (CFO = authoritative, Clinical Director = calm, etc.)
- **Content-aware voice tuning** (objections sound more resistant, enthusiasm more energetic)

### ✅ **Practice Cartridges**
- **Deal-specific RAG** - AI knows your company, pain points, decision makers
- **Contextual conversations** - No more generic responses
- **Scenario-based training** - Opening pitch → Objections → ROI → Closing

### ✅ **Toggleable Training Features**
- **Instructions** - Step-by-step guidance
- **Coaching** - Real-time hints and suggestions  
- **Feedback** - Performance scoring and improvement areas
- **Assessment** - Objective criteria evaluation
- **Evaluation** - Detailed session analysis
- **Practice Loops** - Repeat scenarios for mastery
- **Objection Handling** - Focused resistance training
- **Time Pressure** - Realistic deadline stress
- **Difficulty Scaling** - AI adjusts based on performance

---

## 🛠️ Setup (5 Minutes)

### 1. **Environment Variables**
Create `.env` file in the backend directory:
```bash
# Required for natural voice
ELEVENLABS_API_KEY=your_key_here

# Required for AI responses (choose one)
OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here
```

### 2. **Quick Setup**
```bash
cd voice-training-mvp
python setup_enhanced.py
```

### 3. **Start Services**
**Terminal 1 (Backend):**
```bash
cd backend
python main.py
```

**Terminal 2 (Frontend):**
```bash
cd frontend  
npm start
```

**Access:** http://localhost:3000

---

## 🎯 How to Use

### **Step 1: Create Practice Cartridge**
1. Click "Practice Cartridges" 
2. Either "Create Sample" or "Create New Cartridge"
3. Fill in your deal details:
   - Company name, industry, deal size
   - Decision makers with roles and personas
   - Pain points and value propositions
   - Competition and constraints

### **Step 2: Configure Training Features**
- Toggle features based on your practice goals
- **Beginner:** Instructions + Coaching + Feedback
- **Advanced:** Objection Handling + Time Pressure + Difficulty Scaling

### **Step 3: Select Persona & Practice**
1. Choose cartridge → Select persona → Start session
2. AI will know your deal context and respond realistically
3. Real-time coaching appears in side panel
4. ElevenLabs voice makes it feel like a real conversation

---

## 🎭 Persona Optimization

| Persona | Voice | Personality | Focus Areas |
|---------|--------|-------------|-------------|
| **CFO** | Antoni (authoritative male) | Budget-focused, skeptical | ROI, costs, financial impact |
| **Clinical Director** | Sarah (professional female) | Evidence-based, cautious | Patient outcomes, workflow |
| **IT Director** | Josh (tech-savvy male) | Security-focused, detailed | Integration, compliance |

---

## 🎪 Practice Scenarios

Each cartridge automatically generates:

1. **Opening Pitch** (5 min) - Introduce value proposition
2. **Objection Handling** (8 min per persona) - Address role-specific concerns  
3. **ROI Justification** (10 min) - Financial business case
4. **Technical Discussion** (12 min) - Integration and security
5. **Deal Closing** (15 min) - Final negotiations

---

## ⚙️ Advanced Features

### **Real-Time Coaching**
- Suggestions appear as you speak
- "Try connecting to their key pain point"
- "Consider asking discovery questions"

### **Performance Feedback** 
- Live scoring based on conversation quality
- Strengths identification
- Specific improvement recommendations

### **Voice Optimization**
- AI chooses voice tone based on content type
- Objections sound more resistant
- Enthusiasm sounds more energetic
- Questions sound more inquisitive

---

## 🔧 Troubleshooting

### **No Audio**
- Check ELEVENLABS_API_KEY is set
- Verify API key has credits
- Browser fallback TTS will work if ElevenLabs fails

### **Generic AI Responses**
- Ensure cartridge is selected before starting session
- Check cartridge has decision makers with personas assigned
- Verify deal context fields are filled out

### **Features Not Working**
- Features are toggleable - check they're enabled in side panel
- Some features only work with cartridge context
- Refresh browser if toggles seem stuck

---

## 📊 Expected Results

**Before Enhancement:**
- Terrible browser TTS voices
- Generic, context-free conversations
- No systematic training progression

**After Enhancement:**
- **Natural ElevenLabs voices** feel like real people
- **Deal-specific conversations** with relevant objections
- **Systematic skill development** through toggleable features
- **Context-aware coaching** based on your actual deals

---

## 🚀 Next Steps

1. **Create your real deals** as cartridges
2. **Practice systematically** - start with coaching enabled, gradually add difficulty
3. **Track improvement** through session scoring and feedback
4. **Scale training** by creating cartridges for different deal types

Your voice training just went from **amateur simulation** to **professional preparation**. The combination of natural voices + deal-specific context + toggleable coaching creates a training experience that actually prepares you for real conversations.

**Start with the sample cartridge, then build your own. Happy practicing! 🎤**