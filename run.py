#!/usr/bin/env python3
"""
Orca — Sistema de Restauração Florestal
Main entry point for CLI usage

Usage:
    python run.py                 # Interactive CLI
    python run.py --version       # Show version
    python run.py --help          # Show help
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == '__main__':
    from atm import main
    main()