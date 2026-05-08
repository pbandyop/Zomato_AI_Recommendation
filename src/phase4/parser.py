from __future__ import annotations

import json
import re
from typing import Any


def parse_ranking_response(content: str) -> list[dict[str, Any]]:
    """Parse LLM output into a list of ranking dicts (tolerates fenced code blocks)."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Optional: find outermost JSON array
    if not text.startswith("["):
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            text = match.group()
        else:
            raise ValueError("No JSON array found in model output")

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Model output must be a JSON array")
    return data
