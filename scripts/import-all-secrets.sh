#!/bin/bash

# Import all LiquidSMARTS credentials from Server.env.txt into 1Password
# This script securely migrates all credentials to encrypted storage

set -e

VAULT="LiquidSMARTS"
SOURCE_FILE="/Users/gunterwessels/Library/Mobile Documents/com~apple~CloudDocs/Documents/Sandbox/Server.env.txt"

echo "🔐 Importing LiquidSMARTS Master Credentials to 1Password"
echo "=========================================================="
echo "Source: $SOURCE_FILE"
echo "Vault: $VAULT"
echo ""

if [ ! -f "$SOURCE_FILE" ]; then
    echo "❌ Source file not found: $SOURCE_FILE"
    exit 1
fi

# Function to create API credential item
create_api_item() {
    local title="$1"
    local key="$2"
    local category="${3:-API Credential}"
    local notes="$4"
    
    if [ -z "$key" ]; then
        echo "⏭️  Skipping $title (empty value)"
        return
    fi
    
    # Check if item already exists
    if op item get "$title" --vault="$VAULT" >/dev/null 2>&1; then
        echo "⏭️  $title already exists, updating..."
        op item edit "$title" --vault="$VAULT" credential[password]="$key"
    else
        echo "✅ Creating $title"
        if [ -n "$notes" ]; then
            op item create \
                --category="$category" \
                --title="$title" \
                --vault="$VAULT" \
                credential[password]="$key" \
                notes="$notes"
        else
            op item create \
                --category="$category" \
                --title="$title" \
                --vault="$VAULT" \
                credential[password]="$key"
        fi
    fi
}

# Function to create login item with multiple fields
create_login_item() {
    local title="$1"
    local username="$2"
    local password="$3"
    local url="$4"
    local notes="$5"
    
    if op item get "$title" --vault="$VAULT" >/dev/null 2>&1; then
        echo "⏭️  $title already exists"
        return
    fi
    
    echo "✅ Creating $title (Login)"
    
    if [ -n "$notes" ]; then
        op item create \
            --category="Login" \
            --title="$title" \
            --vault="$VAULT" \
            username="$username" \
            password="$password" \
            url="$url" \
            notes="$notes"
    else
        op item create \
            --category="Login" \
            --title="$title" \
            --vault="$VAULT" \
            username="$username" \
            password="$password" \
            url="$url"
    fi
}

# Parse the env file and extract values
echo "📖 Parsing credentials from $SOURCE_FILE..."

# Core LLM APIs
ANTHROPIC_API_KEY=$(grep "ANTHROPIC_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
OPENAI_API_KEY=$(grep "OPENAI_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
GOOGLE_API_KEY=$(grep "GOOGLE_API_KEY=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)
CEREBRAS_API_KEY=$(grep "CEREBRAS_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
ELEVENLABS_API_KEY=$(grep "ELEVENLABS_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)

# Supabase
SUPABASE_URL=$(grep "SUPABASE_URL=" "$SOURCE_FILE" | cut -d'=' -f2)
SUPABASE_SERVICE_ROLE_KEY=$(grep "SUPABASE_SERVICE_ROLE_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)

# LinkedIn
LINKEDIN_CLIENT_ID=$(grep "LINKEDIN_CLIENT_ID=" "$SOURCE_FILE" | cut -d'=' -f2)
LINKEDIN_CLIENT_SECRET=$(grep "LINKEDIN_CLIENT_SECRET=" "$SOURCE_FILE" | cut -d'=' -f2)
LINKEDIN_ACCESS_TOKEN=$(grep "LINKEDIN_ACCESS_TOKEN=" "$SOURCE_FILE" | cut -d'=' -f2)

# GoHighLevel CRM
GHL_API_KEY=$(grep "GHL_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
GHL_LOCATION_ID=$(grep "GHL_LOCATION_ID=" "$SOURCE_FILE" | cut -d'=' -f2)

# Voice Agents
LIVEKIT_URL=$(grep "LIVEKIT_URL=" "$SOURCE_FILE" | cut -d'=' -f2)
LIVEKIT_API_KEY=$(grep "LIVEKIT_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
LIVEKIT_API_SECRET=$(grep "LIVEKIT_API_SECRET=" "$SOURCE_FILE" | cut -d'=' -f2)
CARTESIA_API_KEY=$(grep "CARTESIA_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
DEEPGRAM_API_KEY=$(grep "DEEPGRAM_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)

# Slack
SLACK_WEBHOOK_URL=$(grep "SLACK_WEBHOOK_URL=" "$SOURCE_FILE" | cut -d'=' -f2-)
SLACK_BOT_TOKEN=$(grep "SLACK_BOT_TOKEN=" "$SOURCE_FILE" | cut -d'=' -f2)

# Twitter/X
TWITTER_API_KEY=$(grep "TWITTER_API_KEY=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)
TWITTER_API_SECRET=$(grep "TWITTER_API_SECRET=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)
TWITTER_ACCESS_TOKEN=$(grep "TWITTER_ACCESS_TOKEN=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)
TWITTER_ACCESS_TOKEN_SECRET=$(grep "TWITTER_ACCESS_TOKEN_SECRET=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)

# Email/SMTP
SMTP_USER=$(grep "SMTP_USER=" "$SOURCE_FILE" | cut -d'=' -f2)
SMTP_PASSWORD=$(grep "SMTP_PASSWORD=" "$SOURCE_FILE" | cut -d'=' -f2)

# Twilio
TWILIO_SID=$(grep "TWILIO_SID=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)
TWILIO_AUTH_TOKEN=$(grep "AUTH_TOKEN=" "$SOURCE_FILE" | head -1 | cut -d'=' -f2)
TWILIO_PHONE_NUMBER=$(grep "TWILIO_PHONE_NUMBER=" "$SOURCE_FILE" | cut -d'=' -f2)

# Other services
SERPTOOL_API_KEY=$(grep "SERPTOOL_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
TAILSCALE_API_KEY=$(grep "TAILSCALE_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
HETZNER_API_KEY=$(grep "HETZNER_API_KEY=" "$SOURCE_FILE" | cut -d'=' -f2)
TELEGRAM_API=$(grep "TELEGRAM_API=" "$SOURCE_FILE" | cut -d'=' -f2)
RESEND_API=$(grep "RESEND_API=" "$SOURCE_FILE" | cut -d'=' -f2)
RAILWAY_API=$(grep "Railway_api=" "$SOURCE_FILE" | cut -d'=' -f2)
META_ACCESS_TOKEN=$(grep "ACCESS_TOKEN=" "$SOURCE_FILE" | cut -d'=' -f2)

echo ""
echo "🚀 Creating 1Password items..."
echo ""

# Create Core LLM API items
echo "=== Core LLM APIs ==="
create_api_item "Anthropic API" "$ANTHROPIC_API_KEY" "API Credential" "Claude AI API key"
create_api_item "OpenAI API" "$OPENAI_API_KEY" "API Credential" "ChatGPT/GPT-4 API key"
create_api_item "Google AI API" "$GOOGLE_API_KEY" "API Credential" "Google AI/Gemini API key"
create_api_item "Cerebras API" "$CEREBRAS_API_KEY" "API Credential" "Cerebras inference API key"
create_api_item "ElevenLabs API" "$ELEVENLABS_API_KEY" "API Credential" "Voice synthesis API key"

echo ""
echo "=== Database & Storage ==="
create_api_item "Supabase Service Key" "$SUPABASE_SERVICE_ROLE_KEY" "API Credential" "Database: $SUPABASE_URL"

echo ""
echo "=== Social Media & CRM ==="
create_api_item "LinkedIn Client Secret" "$LINKEDIN_CLIENT_SECRET" "API Credential" "Client ID: $LINKEDIN_CLIENT_ID"
create_api_item "LinkedIn Access Token" "$LINKEDIN_ACCESS_TOKEN" "API Credential" "OAuth access token"
create_api_item "GoHighLevel API" "$GHL_API_KEY" "API Credential" "Location ID: $GHL_LOCATION_ID"
create_api_item "Twitter API Key" "$TWITTER_API_KEY" "API Credential" "Twitter/X API access"
create_api_item "Twitter API Secret" "$TWITTER_API_SECRET" "API Credential" "Twitter/X API secret"
create_api_item "Twitter Access Token" "$TWITTER_ACCESS_TOKEN" "API Credential" "Twitter/X access token"
create_api_item "Twitter Access Secret" "$TWITTER_ACCESS_TOKEN_SECRET" "API Credential" "Twitter/X access secret"
create_api_item "Meta Access Token" "$META_ACCESS_TOKEN" "API Credential" "Facebook/Instagram API"

echo ""
echo "=== Voice & Communication ==="
create_api_item "LiveKit API Key" "$LIVEKIT_API_KEY" "API Credential" "URL: $LIVEKIT_URL"
create_api_item "LiveKit API Secret" "$LIVEKIT_API_SECRET" "API Credential" "LiveKit API secret"
create_api_item "Cartesia API" "$CARTESIA_API_KEY" "API Credential" "Voice synthesis API"
create_api_item "Deepgram API" "$DEEPGRAM_API_KEY" "API Credential" "Speech-to-text API"
create_api_item "Slack Bot Token" "$SLACK_BOT_TOKEN" "API Credential" "Slack bot integration"
create_api_item "Slack Webhook" "$SLACK_WEBHOOK_URL" "API Credential" "Slack incoming webhook"
create_api_item "Twilio Account SID" "$TWILIO_SID" "API Credential" "Phone: $TWILIO_PHONE_NUMBER"
create_api_item "Twilio Auth Token" "$TWILIO_AUTH_TOKEN" "API Credential" "Twilio authentication"
create_api_item "Telegram Bot API" "$TELEGRAM_API" "API Credential" "Telegram bot token"

echo ""
echo "=== Email & SMTP ==="
create_login_item "Gmail SMTP" "$SMTP_USER" "$SMTP_PASSWORD" "smtp.gmail.com" "App password for SMTP"

echo ""
echo "=== Infrastructure & Tools ==="
create_api_item "SerpTool API" "$SERPTOOL_API_KEY" "API Credential" "Search API tool"
create_api_item "TailScale API" "$TAILSCALE_API_KEY" "API Credential" "VPN management API"
create_api_item "Hetzner VPS API" "$HETZNER_API_KEY" "API Credential" "Server management API"
create_api_item "Resend API" "$RESEND_API" "API Credential" "Email delivery service"
create_api_item "Railway API" "$RAILWAY_API" "API Credential" "Deployment platform API"

echo ""
echo "🎉 Import complete!"
echo ""
echo "All credentials have been securely imported to 1Password vault: $VAULT"
echo ""
echo "Next steps:"
echo "1. Update your scripts to use: source ./scripts/load-secrets.sh"
echo "2. Remove the plain text Server.env.txt file"
echo "3. Add Server.env.txt to .gitignore if not already there"
echo ""
echo "🔒 Your secrets are now encrypted and secure in 1Password!"