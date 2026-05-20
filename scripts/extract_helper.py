#!/usr/bin/env python3
"""
Extraction helper: reads monolith lines and builds srf modules.
Usage: python extract_helper.py
"""
import os, ast, sys

MONO = os.path.join(os.path.dirname(__file__), "src", "atm", "atm_v6_3.py")

def read_lines(start, end):
    """Read lines start..end (1-indexed, inclusive)."""
    with open(MONO, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[start-1:end])

def write_module(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def verify_syntax(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    try:
        ast.parse(src)
        return True, None
    except SyntaxError as e:
        return False, str(e)

if __name__ == "__main__":
    # Quick test
    print(f"Monolith: {len(open(MONO).readlines())} lines")
    print("OK")
