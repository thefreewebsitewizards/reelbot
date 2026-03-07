"""Load and format the capability registry for prompt injection."""

import json
from pathlib import Path
from loguru import logger

CAPABILITIES_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "capabilities.json"


def get_capabilities_context() -> str:
    """Load capabilities.json and return human-readable text for the planner prompt."""
    if not CAPABILITIES_PATH.exists():
        logger.warning(f"Capabilities file not found: {CAPABILITIES_PATH}")
        return ""

    try:
        with open(CAPABILITIES_PATH) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load capabilities: {e}")
        return ""

    lines = []

    mcps = data.get("mcps", [])
    if mcps:
        lines.append("MCP Servers (already built):")
        for mcp in mcps:
            caps = ", ".join(mcp.get("capabilities", []))
            lines.append(f"  - {mcp['name']} [{mcp.get('status', 'unknown')}]: {caps}")

    integrations = data.get("integrations", [])
    if integrations:
        lines.append("Active Integrations:")
        for integ in integrations:
            details = []
            if integ.get("host"):
                details.append(f"host: {integ['host']}")
            if integ.get("url"):
                details.append(f"url: {integ['url']}")
            if integ.get("features"):
                details.append(f"features: {', '.join(integ['features'])}")
            suffix = f" ({', '.join(details)})" if details else ""
            lines.append(f"  - {integ['name']} [{integ.get('status', 'unknown')}]{suffix}")

    return "\n".join(lines)
