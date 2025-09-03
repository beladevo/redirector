#!/usr/bin/env python3
"""
Redirector - Professional URL redirector with campaign tracking and analytics

This is a compatibility shim for the old single-file structure.
The main application is now in src/redirector/cli/main.py
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the main CLI
from redirector.cli.main import app

if __name__ == "__main__":
    app()