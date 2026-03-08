"""Robust JSON extraction from LLM responses."""

import json
import re
from loguru import logger


def extract_json(raw: str, context: str = "") -> dict:
    """Extract JSON object from an LLM response using multiple strategies.

    Args:
        raw: Raw LLM response text.
        context: Label for log messages (e.g. "planner", "repurposer").

    Returns:
        Parsed dict from the JSON.

    Raises:
        json.JSONDecodeError: If no valid JSON found after all strategies.
    """
    text = raw.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: ```json ... ``` code block
    if "```json" in text:
        try:
            json_text = text.split("```json", 1)[1].split("```", 1)[0]
            return json.loads(json_text)
        except (json.JSONDecodeError, IndexError):
            pass

    # Strategy 3: generic ``` ... ``` code block
    if "```" in text:
        try:
            json_text = text.split("```", 1)[1].split("```", 1)[0]
            return json.loads(json_text)
        except (json.JSONDecodeError, IndexError):
            pass

    # Strategy 4: find outermost { ... } braces
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    # Strategy 5: strip common non-JSON prefixes/suffixes and retry
    # Some models emit "Here is the JSON:\n{...}\n\nLet me know..."
    cleaned = re.sub(r"^[^{]*", "", text, count=1)
    cleaned = re.sub(r"[^}]*$", "", cleaned, count=1)
    if cleaned:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # All strategies failed — log the raw response for debugging
    preview = text[:500] + ("..." if len(text) > 500 else "")
    logger.error(
        f"[{context}] JSON extraction failed. "
        f"Response length: {len(text)} chars. Preview:\n{preview}"
    )
    raise json.JSONDecodeError("No valid JSON found in LLM response", text, 0)
