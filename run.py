#!/usr/bin/env python3
"""
Simple script to run the AdaptiCode backend server.
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.api.app import create_app
from backend.config import Config

if __name__ == '__main__':
    print("=" * 60)
    print("AdaptiCode - Adaptive Learning System for Recursion")
    print("=" * 60)
    print(f"\nStarting server on http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print("\nTo use the system (single server):")
    print("1. Keep this server running")
    print(f"2. Open http://localhost:{Config.FLASK_PORT}/ in your browser")
    print("   - Cover page is at '/' (home)")
    print("   - Practice page with editor is at '/question'")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
        use_reloader=Config.USE_RELOADER

    )

