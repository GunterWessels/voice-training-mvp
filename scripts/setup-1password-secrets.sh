#!/bin/bash

# Setup 1Password items for LiquidSMARTS Voice Training API keys

set -e

VAULT="LiquidSMARTS"

echo "🔐 Setting up 1Password secrets for Voice Training Platform..."
echo "This will create secure storage for your API keys in vault: $VAULT"
echo ""

# Function to create API key item
create_api_item() {
    local name="$1"
    local title="$2"
    
    echo "Creating 1Password item: $name"
    echo "Please enter your $title when prompted:"
    
    # Create the item with a secure note template
    op item create \
        --category="API Credential" \
        --title="$name" \
        --vault="$VAULT" \
        credential[password]="" \
        --prompt
    
    echo "✅ $name created successfully"
    echo ""
}

echo "We'll create 3 secure items in your LiquidSMARTS vault:"
echo "1. ElevenLabs API - Required for natural voice"  
echo "2. OpenAI API - Optional for AI responses"
echo "3. Anthropic API - Optional for AI responses"
echo ""
echo "You need at least ElevenLabs API + one AI API for the system to work."
echo ""

read -p "Ready to proceed? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    
    # Check if items already exist
    if op item get "ElevenLabs API" --vault="$VAULT" >/dev/null 2>&1; then
        echo "⏭️  ElevenLabs API item already exists"
    else
        create_api_item "ElevenLabs API" "ElevenLabs API Key"
    fi
    
    if op item get "OpenAI API" --vault="$VAULT" >/dev/null 2>&1; then
        echo "⏭️  OpenAI API item already exists"
    else
        echo "Enter OpenAI API key (or press Enter to skip):"
        read -s openai_key
        if [ -n "$openai_key" ]; then
            echo "$openai_key" | op item create \
                --category="API Credential" \
                --title="OpenAI API" \
                --vault="$VAULT" \
                credential[password]=-
            echo "✅ OpenAI API created successfully"
        else
            echo "⏭️  OpenAI API skipped"
        fi
        echo ""
    fi
    
    if op item get "Anthropic API" --vault="$VAULT" >/dev/null 2>&1; then
        echo "⏭️  Anthropic API item already exists"  
    else
        echo "Enter Anthropic API key (or press Enter to skip):"
        read -s anthropic_key
        if [ -n "$anthropic_key" ]; then
            echo "$anthropic_key" | op item create \
                --category="API Credential" \
                --title="Anthropic API" \
                --vault="$VAULT" \
                credential[password]=-
            echo "✅ Anthropic API created successfully"
        else
            echo "⏭️  Anthropic API skipped"
        fi
        echo ""
    fi
    
    echo "🎉 1Password secrets setup complete!"
    echo ""
    echo "Your API keys are now stored securely in 1Password."
    echo "The voice training platform will load them automatically."
    echo ""
    
else
    echo "Setup cancelled."
    exit 1
fi