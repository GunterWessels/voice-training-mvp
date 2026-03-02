#!/usr/bin/env python3
"""
Setup script for Enhanced Voice Training Platform
"""

import os
import subprocess
import sys

def check_env_vars():
    """Check for required environment variables"""
    required_vars = ['ELEVENLABS_API_KEY']
    optional_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print("❌ Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        return False
    
    if missing_optional:
        print("⚠️  Missing optional environment variables:")
        for var in missing_optional:
            print(f"   - {var}")
        print("   Note: AI responses will use mock data without these.")
    
    print("✅ Environment variables configured")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "websockets", "httpx", "python-multipart"], check=True)
        print("✅ Python dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False

def install_frontend_deps():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")
    
    try:
        subprocess.run(["npm", "install", "--prefix", "frontend"], check=True)
        print("✅ Frontend dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install frontend dependencies")
        return False

def create_sample_env():
    """Create sample .env file"""
    env_content = """# Enhanced Voice Training Platform Configuration

# Required: ElevenLabs API Key for natural voice generation
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: AI service providers (one required for AI responses)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database (SQLite is used by default)
DATABASE_URL=sqlite:///./voice_training.db
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file template")
    else:
        print("ℹ️  .env file already exists")

def initialize_database():
    """Initialize the database"""
    print("🗄️  Initializing database...")
    
    try:
        # Import and initialize services
        from backend.cartridge_service import CartridgeService
        from backend.database import Database
        
        # Initialize database
        db = Database()
        
        # Initialize cartridge service (creates tables)
        cartridge_service = CartridgeService()
        
        print("✅ Database initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def create_sample_cartridge():
    """Create a sample cartridge for testing"""
    print("🎯 Creating sample cartridge...")
    
    try:
        from backend.cartridge_service import CartridgeService
        
        cartridge_service = CartridgeService()
        cartridge_id = cartridge_service.create_sample_cartridge()
        
        print(f"✅ Sample cartridge created: {cartridge_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to create sample cartridge: {e}")
        return False

def print_startup_instructions():
    """Print instructions for starting the platform"""
    print("\n" + "="*60)
    print("🚀 ENHANCED VOICE TRAINING PLATFORM - READY!")
    print("="*60)
    print()
    print("To start the platform:")
    print()
    print("1. Backend (Terminal 1):")
    print("   cd backend")
    print("   python main.py")
    print()
    print("2. Frontend (Terminal 2):")
    print("   cd frontend")
    print("   npm start")
    print()
    print("🌟 NEW FEATURES:")
    print("   • ElevenLabs TTS for natural voice")
    print("   • Practice Cartridges with deal-specific context")
    print("   • Toggleable training features:")
    print("     - Instructions & Coaching")
    print("     - Feedback & Assessment")
    print("     - Objection Handling")
    print("     - Time Pressure & Difficulty Scaling")
    print()
    print("📋 WORKFLOW:")
    print("   1. Select/Create Practice Cartridge")
    print("   2. Choose AI Persona")
    print("   3. Configure Training Features")
    print("   4. Start Voice Practice Session")
    print()
    print("🔑 REQUIRED:")
    print("   • Set ELEVENLABS_API_KEY in .env file")
    print("   • Set OPENAI_API_KEY or ANTHROPIC_API_KEY for AI")
    print()
    print("Access: http://localhost:3000")
    print("="*60)

def main():
    """Main setup function"""
    print("🎙️ Enhanced Voice Training Platform Setup")
    print("=========================================")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('backend') or not os.path.exists('frontend'):
        print("❌ Please run this script from the voice-training-mvp directory")
        sys.exit(1)
    
    success = True
    
    # Create environment file
    create_sample_env()
    
    # Check environment variables
    success &= check_env_vars()
    
    # Install dependencies
    success &= install_dependencies()
    success &= install_frontend_deps()
    
    # Initialize database and create sample data
    success &= initialize_database()
    success &= create_sample_cartridge()
    
    if success:
        print_startup_instructions()
    else:
        print("\n❌ Setup completed with errors. Please check the messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()