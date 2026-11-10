"""Lists Gemini models available to your key so you can fill GEMINI_*_MODEL in .env.
Usage:  python scripts/list_gemini_models.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import get_settings  # noqa: E402


def main() -> None:
    key = get_settings().gemini_api_key
    if not key:
        sys.exit("GEMINI_API_KEY is empty in .env")
    from google import genai

    client = genai.Client(api_key=key)
    rows = []
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        rows.append((m.name.replace("models/", ""), ",".join(actions)))
    print(f"{'model':45} supported actions")
    for name, acts in sorted(rows):
        print(f"{name:45} {acts}")
    print("\nPick: a 'generateContent' flash model for GEMINI_LLM_MODEL / GEMINI_VISION_MODEL / GEMINI_STT_MODEL,"
          "\nand an 'embedContent' model for GEMINI_EMBED_MODEL.")


if __name__ == "__main__":
    main()
