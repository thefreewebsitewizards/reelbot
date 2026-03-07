from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import settings
from src.models import AnalysisResult, PipelineResult

VALID_TARGETS = {
    "claude-upgrades", "ddb", "tfww",
    "n8n-automations", "ghl-fix", "aias",
}

FALLBACK_MAP = {
    "ai_automation": "claude-upgrades",
    "social_media": "ddb",
    "marketing": "tfww",
    "sales": "tfww",
    "business_ops": "tfww",
    "mindset": "ddb",
}


def resolve_route(analysis: AnalysisResult) -> str:
    target = analysis.routing_target.strip().lower()
    if target in VALID_TARGETS:
        return target
    fallback = FALLBACK_MAP.get(analysis.category, "tfww")
    logger.warning(
        f"Invalid routing_target '{analysis.routing_target}', "
        f"falling back to '{fallback}' based on category '{analysis.category}'"
    )
    return fallback


def route_plan(result: PipelineResult) -> str | None:
    target = resolve_route(result.analysis)
    sister_dir = settings.sister_projects_dir / target / "from-reels"

    try:
        sister_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error(f"Cannot create routing dir {sister_dir}: {exc}")
        return None

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_{result.reel_id}.md"
    blurb = _format_blurb(result)

    blurb_path = sister_dir / filename
    blurb_path.write_text(blurb)
    logger.info(f"Routed blurb to {blurb_path}")
    return target


def _format_blurb(result: PipelineResult) -> str:
    a = result.analysis
    public_url = settings.public_url.rstrip("/") if settings.public_url else ""
    view_link = f"{public_url}/plans/{result.reel_id}/view" if public_url else ""

    lines = [
        f"# {result.plan.title}",
        "",
        f"> {a.theme}" if a.theme else "",
        "",
        f"**Category:** {a.category} | **Relevance:** {a.relevance_score:.0%}",
        f"**Source:** [{result.metadata.creator}]({result.metadata.url})",
        "",
        "## Summary",
        "",
        a.summary,
        "",
        "## Why This Matters",
        "",
        a.business_impact if a.business_impact else "N/A",
    ]

    if view_link:
        lines.extend(["", "## View Full Plan", "", view_link])

    return "\n".join(lines)
