#!/bin/bash

# LiquidSMARTS Master Environment Loader
# Loads ALL credentials from 1Password instead of plain text .env files
# Supports all LiquidSMARTS services and integrations

set -e

VAULT="LiquidSMARTS"

echo "🔒 Loading ALL secrets from 1Password vault: $VAULT"

# Function to safely get secret from 1Password
get_secret() {
    local item_name="$1"
    local field_name="${2:-credential}"
    
    # Check if item exists
    if op item get "$item_name" --vault="$VAULT" >/dev/null 2>&1; then
        op item get "$item_name" --vault="$VAULT" --fields="$field_name" --reveal 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# === CORE LLM APIs ===
export ANTHROPIC_API_KEY=$(get_secret "Anthropic API")
export OPENAI_API_KEY=$(get_secret "OpenAI API")
export GOOGLE_API_KEY=$(get_secret "Google AI API")
export CEREBRAS_API_KEY=$(get_secret "Cerebras API")
export ELEVENLABS_API_KEY=$(get_secret "ElevenLabs API")

# === DATABASE & STORAGE ===
export SUPABASE_SERVICE_ROLE_KEY=$(get_secret "Supabase Service Key")
export SUPABASE_URL="https://zpjqpuyrjssotofxiukh.supabase.co"

# === SOCIAL MEDIA & CRM ===
export LINKEDIN_CLIENT_ID="78fy137dtf73me"
export LINKEDIN_CLIENT_SECRET=$(get_secret "LinkedIn Client Secret")
export LINKEDIN_ACCESS_TOKEN=$(get_secret "LinkedIn Access Token")
export LINKEDIN_REDIRECT_URI="http://localhost:8000/callback"

export GHL_API_KEY=$(get_secret "GoHighLevel API")
export GHL_LOCATION_ID="XLhvbFVq9G5A3lwSTs2U"

export TWITTER_API_KEY=$(get_secret "Twitter API Key")
export TWITTER_API_SECRET=$(get_secret "Twitter API Secret")
export TWITTER_ACCESS_TOKEN=$(get_secret "Twitter Access Token")
export TWITTER_ACCESS_TOKEN_SECRET=$(get_secret "Twitter Access Secret")

export META_ACCESS_TOKEN=$(get_secret "Meta Access Token")

# === VOICE & COMMUNICATION ===
export LIVEKIT_URL="wss://liquidsmartsasalesagent-yo1o1qj8.livekit.cloud"
export LIVEKIT_API_KEY=$(get_secret "LiveKit API Key")
export LIVEKIT_API_SECRET=$(get_secret "LiveKit API Secret")
export CARTESIA_API_KEY=$(get_secret "Cartesia API")
export DEEPGRAM_API_KEY=$(get_secret "Deepgram API")

export SLACK_BOT_TOKEN=$(get_secret "Slack Bot Token")
export SLACK_WEBHOOK_URL=$(get_secret "Slack Webhook")

export TWILIO_SID=$(get_secret "Twilio Account SID")
export TWILIO_AUTH_TOKEN=$(get_secret "Twilio Auth Token")
export TWILIO_PHONE_NUMBER="+18554101968"

export TELEGRAM_API=$(get_secret "Telegram Bot API")

# === EMAIL & SMTP ===
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_TLS="true"
export SMTP_USER=$(get_secret "Gmail SMTP" "username")
export SMTP_PASSWORD=$(get_secret "Gmail SMTP" "password")
export EMAIL_FROM=$(get_secret "Gmail SMTP" "username")
export EMAIL_TO=$(get_secret "Gmail SMTP" "username")

# === INFRASTRUCTURE & TOOLS ===
export SERPTOOL_API_KEY=$(get_secret "SerpTool API")
export TAILSCALE_API_KEY=$(get_secret "TailScale API")
export HETZNER_API_KEY=$(get_secret "Hetzner VPS API")
export RESEND_API=$(get_secret "Resend API")
export RAILWAY_API=$(get_secret "Railway API")

# === DATABASE CONFIG ===
export DATABASE_URL="sqlite:///./voice_training.db"

# Verification and status
loaded_count=0
total_services=0

echo ""
echo "📊 Service Status:"

# Core LLM APIs
echo "=== Core LLM APIs ==="
total_services=$((total_services + 5))
[ -n "$ANTHROPIC_API_KEY" ] && echo "✅ Anthropic API" && loaded_count=$((loaded_count + 1)) || echo "❌ Anthropic API"
[ -n "$OPENAI_API_KEY" ] && echo "✅ OpenAI API" && loaded_count=$((loaded_count + 1)) || echo "❌ OpenAI API"
[ -n "$GOOGLE_API_KEY" ] && echo "✅ Google AI API" && loaded_count=$((loaded_count + 1)) || echo "❌ Google AI API"
[ -n "$CEREBRAS_API_KEY" ] && echo "✅ Cerebras API" && loaded_count=$((loaded_count + 1)) || echo "❌ Cerebras API"
[ -n "$ELEVENLABS_API_KEY" ] && echo "✅ ElevenLabs API" && loaded_count=$((loaded_count + 1)) || echo "❌ ElevenLabs API"

# Database
echo "=== Database & Storage ==="
total_services=$((total_services + 1))
[ -n "$SUPABASE_SERVICE_ROLE_KEY" ] && echo "✅ Supabase" && loaded_count=$((loaded_count + 1)) || echo "❌ Supabase"

# Social & CRM
echo "=== Social Media & CRM ==="
total_services=$((total_services + 7))
[ -n "$LINKEDIN_CLIENT_SECRET" ] && echo "✅ LinkedIn" && loaded_count=$((loaded_count + 1)) || echo "❌ LinkedIn"
[ -n "$GHL_API_KEY" ] && echo "✅ GoHighLevel CRM" && loaded_count=$((loaded_count + 1)) || echo "❌ GoHighLevel CRM"
[ -n "$TWITTER_API_KEY" ] && echo "✅ Twitter/X API" && loaded_count=$((loaded_count + 1)) || echo "❌ Twitter/X API"
[ -n "$TWITTER_API_SECRET" ] && echo "✅ Twitter/X Secret" && loaded_count=$((loaded_count + 1)) || echo "❌ Twitter/X Secret"
[ -n "$TWITTER_ACCESS_TOKEN" ] && echo "✅ Twitter/X Token" && loaded_count=$((loaded_count + 1)) || echo "❌ Twitter/X Token"
[ -n "$TWITTER_ACCESS_TOKEN_SECRET" ] && echo "✅ Twitter/X Token Secret" && loaded_count=$((loaded_count + 1)) || echo "❌ Twitter/X Token Secret"
[ -n "$META_ACCESS_TOKEN" ] && echo "✅ Meta/Facebook" && loaded_count=$((loaded_count + 1)) || echo "❌ Meta/Facebook"

# Voice & Communication
echo "=== Voice & Communication ==="
total_services=$((total_services + 8))
[ -n "$LIVEKIT_API_KEY" ] && echo "✅ LiveKit" && loaded_count=$((loaded_count + 1)) || echo "❌ LiveKit"
[ -n "$CARTESIA_API_KEY" ] && echo "✅ Cartesia" && loaded_count=$((loaded_count + 1)) || echo "❌ Cartesia"
[ -n "$DEEPGRAM_API_KEY" ] && echo "✅ Deepgram" && loaded_count=$((loaded_count + 1)) || echo "❌ Deepgram"
[ -n "$SLACK_BOT_TOKEN" ] && echo "✅ Slack Bot" && loaded_count=$((loaded_count + 1)) || echo "❌ Slack Bot"
[ -n "$SLACK_WEBHOOK_URL" ] && echo "✅ Slack Webhook" && loaded_count=$((loaded_count + 1)) || echo "❌ Slack Webhook"
[ -n "$TWILIO_SID" ] && echo "✅ Twilio SID" && loaded_count=$((loaded_count + 1)) || echo "❌ Twilio SID"
[ -n "$TWILIO_AUTH_TOKEN" ] && echo "✅ Twilio Auth" && loaded_count=$((loaded_count + 1)) || echo "❌ Twilio Auth"
[ -n "$TELEGRAM_API" ] && echo "✅ Telegram" && loaded_count=$((loaded_count + 1)) || echo "❌ Telegram"

# Email
echo "=== Email & SMTP ==="
total_services=$((total_services + 1))
[ -n "$SMTP_PASSWORD" ] && echo "✅ Gmail SMTP" && loaded_count=$((loaded_count + 1)) || echo "❌ Gmail SMTP"

# Infrastructure
echo "=== Infrastructure & Tools ==="
total_services=$((total_services + 5))
[ -n "$SERPTOOL_API_KEY" ] && echo "✅ SerpTool" && loaded_count=$((loaded_count + 1)) || echo "❌ SerpTool"
[ -n "$TAILSCALE_API_KEY" ] && echo "✅ TailScale" && loaded_count=$((loaded_count + 1)) || echo "❌ TailScale"
[ -n "$HETZNER_API_KEY" ] && echo "✅ Hetzner VPS" && loaded_count=$((loaded_count + 1)) || echo "❌ Hetzner VPS"
[ -n "$RESEND_API" ] && echo "✅ Resend" && loaded_count=$((loaded_count + 1)) || echo "❌ Resend"
[ -n "$RAILWAY_API" ] && echo "✅ Railway" && loaded_count=$((loaded_count + 1)) || echo "❌ Railway"

echo ""
echo "📈 Summary: $loaded_count/$total_services services loaded ($(( loaded_count * 100 / total_services ))%)"

# Critical service checks
critical_missing=0

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "🚨 CRITICAL: ElevenLabs API required for voice training"
    critical_missing=1
fi

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "🚨 CRITICAL: At least one AI API (OpenAI or Anthropic) required"
    critical_missing=1
fi

if [ $critical_missing -eq 0 ]; then
    echo "🚀 Environment ready - all critical secrets loaded securely!"
else
    echo "⚠️  Environment loaded with missing critical secrets"
    echo "   Run: ./scripts/import-all-secrets.sh to import all credentials"
fi