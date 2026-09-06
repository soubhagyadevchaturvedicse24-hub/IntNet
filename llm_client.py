"""
llm_client.py
=============
Central factory for every LLM client in this project.

All calls to "gpt-6-astra" are routed through the Experiential gateway:
  Base URL : https://api.experientiallabs.ai/v1
  Auth     : EXPLABS_API_KEY environment variable
  Model ID : gpt-6-astra  (passed through unchanged)

Any other model falls back to the normal OpenAI client (OPENAI_API_KEY).

Usage
-----
from llm_client import build_client, MODEL_ASTRA

client = build_client()          # returns an openai.OpenAI pointed at Experiential
response = client.chat.completions.create(model=MODEL_ASTRA, messages=[...])
"""

import os
import sys

from openai import OpenAI

# ── Constants ────────────────────────────────────────────────────────────────

MODEL_ASTRA          = "gpt-6-astra"
EXPERIENTIAL_BASE_URL = "https://api.experientiallabs.ai/v1"
EXPLABS_KEY_ENV       = "EXPLABS_API_KEY"


# ── Guard ────────────────────────────────────────────────────────────────────

def _require_explabs_key() -> str:
    """Return the Experiential API key or abort with a clear message."""
    key = os.environ.get(EXPLABS_KEY_ENV, "").strip()
    if not key:
        print(
            "\n[ERROR] The environment variable EXPLABS_API_KEY is not set.\n"
            "\nTo fix this:\n"
            "  1. Open https://api.experientiallabs.ai  →  Settings → API keys\n"
            "  2. Create a new key and copy it.\n"
            "  3. In PowerShell run:\n"
            "       $env:EXPLABS_API_KEY = \"exl-...\"\n"
            "     Or add it permanently via System Environment Variables.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


# ── Factory ──────────────────────────────────────────────────────────────────

def build_client(model: str = MODEL_ASTRA) -> OpenAI:
    """
    Return an OpenAI-compatible client configured for *model*.

    • If model == MODEL_ASTRA  → Experiential gateway, EXPLABS_API_KEY
    • Otherwise               → Standard OpenAI, OPENAI_API_KEY
    """
    if model == MODEL_ASTRA:
        api_key = _require_explabs_key()
        return OpenAI(
            base_url=EXPERIENTIAL_BASE_URL,
            api_key=api_key,
        )

    # Fallback: standard OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not openai_key:
        print(
            "\n[ERROR] OPENAI_API_KEY is not set. "
            "Set it or use MODEL_ASTRA with EXPLABS_API_KEY.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return OpenAI(api_key=openai_key)
