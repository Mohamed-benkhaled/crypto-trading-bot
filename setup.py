#!/usr/bin/env python3
"""
Setup script for the Crypto Trading Bot
This script helps initialize the database and create the first admin user.
"""

import os
import sys
import sqlite3
from pathlib import Path

def create_database():
    """Create the SQLite database and tables"""
    try:
        # Import database models
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from core.database import engine, Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_admin_user():
    """Create the first admin user"""
    try:
        from core.database import SessionLocal, User
        from api.routes.auth import get_password_hash
        
        db = SessionLocal()
        
        # Check if admin user already exists
        admin_exists = db.query(User).filter(User.is_admin == True).first()
        if admin_exists:
            print("ℹ️  Admin user already exists")
            db.close()
            return True
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@cryptobot.com",
            hashed_password=get_password_hash("admin"),
            is_active=True,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.close()
        
        print("✅ Admin user created successfully!")
        print("   Username: admin")
        print("   Password: admin")
        print("   ⚠️  Please change the password after first login!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

def create_env_file():
    """Create .env file from template"""
    try:
        env_file = Path(".env")
        if env_file.exists():
            print("ℹ️  .env file already exists")
            return True
        
        # Read template
        template_file = Path("env_example.txt")
        if not template_file.exists():
            print("⚠️  env_example.txt not found, creating basic .env file")
            create_basic_env()
            return True
        
        # Copy template to .env
        with open(template_file, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ .env file created from template")
        print("   Please edit .env file with your API keys and settings")
        return True
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def create_basic_env():
    """Create a basic .env file"""
    basic_env_content = """# Database Configuration
DATABASE_URL=sqlite:///./crypto_bot.db

# JWT Settings
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
BINANCE_TESTNET=true

# Trading Configuration
DEFAULT_TRADING_PAIRS=["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT"]
DEFAULT_TIMEFRAME=1h
MAX_POSITION_SIZE=0.1
STOP_LOSS_PERCENTAGE=0.02
TAKE_PROFIT_PERCENTAGE=0.06
MAX_DRAWDOWN=0.15

# Exchange Settings
EXCHANGE_NAME=binance
EXCHANGE_TESTNET=true

# Web Interface
HOST=0.0.0.0
PORT=8000
DEBUG=true
"""
    
    with open(".env", 'w') as f:
        f.write(basic_env_content)

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import pandas
        import numpy
        import ta
        import ccxt
        import sqlalchemy
        print("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Please run: pip install -r requirements.txt")
        return False

def main():
    """Main setup function"""
    print("🚀 Crypto Trading Bot Setup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Create database
    if not create_database():
        return False
    
    # Create admin user
    if not create_admin_user():
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python main.py")
    print("3. Open http://localhost:8000 in your browser")
    print("4. Login with admin/admin")
    print("5. Change the default password")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
