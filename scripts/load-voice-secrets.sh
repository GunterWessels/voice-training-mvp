#!/bin/bash

# LiquidSMARTS Voice Training - Fast Secret Loader
# Loads only the essential secrets needed for voice training platform

set -e

VAULT="LiquidSMARTS"

echo "🎙️ Loading voice training secrets from 1Password..."

# Function to safely get secret from 1Password
get_secret() {
    local item_name="$1"
    local field_name="${2:-credential}"
    
    if op item get "$item_name" --vault="$VAULT" >/dev/null 2>&1; then
        op item get "$item_name" --vault="$VAULT" --fields="$field_name" --reveal 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# === ESSENTIAL VOICE TRAINING APIS ===
export ELEVENLABS_API_KEY=$(get_secret "ElevenLabs API")
export OPENAI_API_KEY=$(get_secret "OpenAI API") 
export ANTHROPIC_API_KEY=$(get_secret "Anthropic API")

# === DATABASE ===
export DATABASE_URL="sqlite:///./voice_training.db"

# Quick validation
critical_missing=0

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "❌ ElevenLabs API key missing"
    critical_missing=1
else
    echo "✅ ElevenLabs API loaded"
fi

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ No AI API keys found"
    critical_missing=1
else
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "✅ OpenAI API loaded"
    fi
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "✅ Anthropic API loaded"
    fi
fi

if [ $critical_missing -eq 0 ]; then
    echo "🚀 Voice training environment ready!"
else
    echo "⚠️  Missing critical secrets - run: ./scripts/import-all-secrets.sh"
    exit 1
fi