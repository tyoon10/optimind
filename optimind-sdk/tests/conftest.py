"""
Test bootstrap. Lets the suite run in a bare dev env where the agent runtime's
deps aren't installed:
  - stub `python-dotenv` if absent (src.config imports it at module load),
  - provide dummy required env vars (src.config's Config() validates them on import).
Production is unaffected — these only fill gaps when the real values are missing.
"""

import os
import sys
import types

# src/ lives one level up from tests/; make `import src.*` resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import dotenv  # noqa: F401
except ImportError:
    _stub = types.ModuleType("dotenv")
    _stub.load_dotenv = lambda *a, **k: False
    sys.modules["dotenv"] = _stub

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
