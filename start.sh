#!/bin/bash

# Voice Training Platform MVP - Startup Script

echo "🎙️ Starting Voice Training Platform MVP..."

# Check if we're in the right directory
if [[ ! -d "backend" || ! -d "frontend" ]]; then
    echo "❌ Please run this script from the voice-training-mvp directory"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Kill any existing processes on our ports
if check_port 8000; then
    echo "🔄 Stopping existing backend process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

if check_port 3000; then
    echo "🔄 Stopping existing frontend process on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

# Start backend in background
echo "🚀 Starting backend (FastAPI) on port 8000..."
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Test backend
echo "🧪 Testing backend..."
if curl -s http://localhost:8000/ | grep -q "Voice Training Platform MVP"; then
    echo "✅ Backend is running successfully!"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Start frontend if Node.js is available
if command -v npm &> /dev/null; then
    echo "🎨 Starting frontend (React) on port 3000..."
    cd frontend
    
    # Install dependencies if node_modules doesn't exist
    if [[ ! -d "node_modules" ]]; then
        echo "📦 Installing frontend dependencies..."
        npm install
    fi
    
    npm start &
    FRONTEND_PID=$!
    cd ..
    
    echo ""
    echo "🎉 Voice Training Platform MVP is starting up!"
    echo ""
    echo "📍 URLs:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "🎯 To use voice features, ensure:"
    echo "   • You're using Chrome/Edge (best speech recognition)"
    echo "   • You allow microphone access when prompted"
    echo ""
    echo "⚡ Features:"
    echo "   • Real-time voice conversations with AI personas"
    echo "   • Three pre-built healthcare buyer personas"
    echo "   • Session history and basic scoring"
    echo "   • High-quality TTS voices (auto-detected from your API keys)"
    echo ""
    echo "🛑 Press Ctrl+C to stop all services"
    echo ""
    
    # Wait for both processes
    wait $BACKEND_PID $FRONTEND_PID
else
    echo ""
    echo "⚠️  Node.js not found. Backend only mode."
    echo ""
    echo "📍 URLs:"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "💡 To run the full platform:"
    echo "   1. Install Node.js: https://nodejs.org/"
    echo "   2. Run this script again"
    echo ""
    echo "🛑 Press Ctrl+C to stop the backend"
    
    # Wait for backend only
    wait $BACKEND_PID
fi