#!/usr/bin/env python3
"""
Launcher for the optimind stdio MCP server (configured in the repo-root .mcp.json).
Thin on purpose — the registry + dispatch live in src/mcp_server.py so they're
unit-testable without the `mcp` package installed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_server import run

if __name__ == "__main__":
    run()
