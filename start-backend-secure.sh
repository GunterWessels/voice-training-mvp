#!/bin/bash

# Secure startup script for LiquidSMARTS Voice Training Backend
# Loads API keys from 1Password and starts the backend service

set -e

cd "$(dirname "$0")"

echo "🎙️ LiquidSMARTS Voice Training - Secure Startup"
echo "==============================================="

# Load secrets from 1Password (voice training essentials)
echo "🔒 Loading secrets from 1Password..."
source ./scripts/load-voice-secrets.sh

# Verify required secrets are available
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "❌ ElevenLabs API key is required but not found in 1Password"
    echo "   Run: ./scripts/setup-1password-secrets.sh"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ At least one AI API key (OpenAI or Anthropic) is required"
    echo "   Run: ./scripts/setup-1password-secrets.sh"
    exit 1
fi

# Start backend service
echo "🚀 Starting backend service with secure environment..."
cd backend
python main.py