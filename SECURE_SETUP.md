# 🔐 Secure Setup with 1Password CLI

This guide shows you how to set up the Voice Training Platform with **enterprise-grade security** using 1Password CLI. Your API keys never touch plain text files.

## 🎯 Why This Approach?

- **Zero plain text secrets** - API keys stored encrypted in 1Password
- **No accidental commits** - Secrets never appear in git repos
- **Automated loading** - No manual copy/paste of sensitive data
- **Audit trail** - 1Password tracks secret access
- **Team ready** - Easy to share securely with team members

---

## 🚀 Quick Setup (3 Commands)

```bash
# 1. Store your API keys securely in 1Password
./scripts/setup-1password-secrets.sh

# 2. Start backend with secrets loaded from 1Password  
./start-backend-secure.sh

# 3. Start frontend (separate terminal)
cd frontend && npm start
```

**That's it!** Your API keys are loaded securely without ever touching disk.

---

## 📋 Detailed Setup

### **Step 1: Store API Keys in 1Password**

```bash
./scripts/setup-1password-secrets.sh
```

This creates 3 secure items in your **LiquidSMARTS vault**:
- **ElevenLabs API** (Required) - For natural voice generation
- **OpenAI API** (Optional) - For AI responses  
- **Anthropic API** (Optional) - Alternative AI provider

**You need:** ElevenLabs API + one AI API minimum.

### **Step 2: Start Services Securely**

**Terminal 1 (Backend):**
```bash
./start-backend-secure.sh
```

**Terminal 2 (Frontend):**  
```bash
cd frontend
npm start
```

### **Step 3: Verify Setup**

Visit http://localhost:3000 and:
1. Create/select a practice cartridge
2. Choose a persona and start practicing  
3. Verify ElevenLabs natural voice works
4. Check that AI responses are contextual

---

## 🔍 How It Works

### **Secret Storage Structure**
```
1Password Vault: LiquidSMARTS
├── ElevenLabs API (API Credential)
├── OpenAI API (API Credential) 
└── Anthropic API (API Credential)
```

### **Loading Process**
1. `load-secrets.sh` queries 1Password CLI for each secret
2. Exports them as environment variables  
3. Backend service uses environment variables
4. **No secrets ever written to disk**

### **Security Features**
- **Encrypted storage** - 1Password's zero-knowledge encryption
- **Access logging** - 1Password tracks when secrets are accessed
- **Auto-expiry** - Can set secrets to expire automatically
- **Team sharing** - Share securely with team members via 1Password

---

## 🛠️ Troubleshooting

### **"op command not found"**
```bash
# Install 1Password CLI
brew install --cask 1password-cli

# Sign in to your account
op signin
```

### **"Item not found in vault"**
```bash
# Re-run the setup to create missing items
./scripts/setup-1password-secrets.sh

# Or manually create in 1Password app:
# Name: "ElevenLabs API"
# Type: "API Credential"  
# Vault: "LiquidSMARTS"
```

### **"No AI API keys found"**
You need at least one AI provider. Add either:
- OpenAI API key, OR
- Anthropic API key

### **Environment not loading**
```bash
# Test the script manually
source ./scripts/load-secrets.sh

# Check if variables are set
echo "ElevenLabs: ${ELEVENLABS_API_KEY:+SET}"
echo "OpenAI: ${OPENAI_API_KEY:+SET}" 
echo "Anthropic: ${ANTHROPIC_API_KEY:+SET}"
```

---

## 📚 File Structure

```
voice-training-mvp/
├── scripts/
│   ├── load-secrets.sh          # Loads env vars from 1Password
│   └── setup-1password-secrets.sh # Creates 1Password items
├── start-backend-secure.sh      # Secure backend startup
├── backend/                     # Backend service files
└── frontend/                    # Frontend React app
```

---

## 🔄 Team Usage

To share this setup with team members:

1. **Share 1Password vault** - Give them access to LiquidSMARTS vault
2. **Share repository** - Standard git clone (no secrets in repo!)
3. **Run setup** - They just run `./scripts/setup-1password-secrets.sh`

**No keys to manage, copy, or accidentally commit!**

---

## 🎯 Benefits Over .env Files

| .env Files | 1Password CLI |
|------------|---------------|
| ❌ Plain text on disk | ✅ Encrypted storage |
| ❌ Easy to accidentally commit | ✅ Never in git |
| ❌ Manual copy/paste | ✅ Automated loading |
| ❌ No access tracking | ✅ Full audit trail |
| ❌ Hard to share securely | ✅ Easy team sharing |

---

## 🚨 Security Best Practices

✅ **DO:**
- Use this 1Password setup for all secrets
- Regularly rotate API keys  
- Use separate keys for dev/staging/prod
- Enable 2FA on all API provider accounts

❌ **DON'T:**
- Put API keys in .env files
- Share keys via Slack/email  
- Commit secrets to git (even private repos)
- Use production keys for development

---

**Your API keys are now enterprise-secure!** 🔐

The voice training platform loads secrets automatically from 1Password, so you get full functionality without any security compromises.

**Ready to start?** Run `./scripts/setup-1password-secrets.sh` to begin!