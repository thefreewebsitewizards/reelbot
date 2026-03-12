"""Telegram similarity flow handlers.

Handles the generate-anyway and skip-similar inline button actions,
plus saving analysis for pipeline resume.
"""
import json
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from src.config import settings
from src.models import (
    AnalysisResult, PipelineResult, PlanStatus, ReelMetadata,
    SimilarityResult, TranscriptResult, CostBreakdown,
)
from src.services.planner import generate_plan
from src.utils.plan_writer import write_plan
from src.utils.plan_manager import get_index, save_index


def _esc(text: str) -> str:
    """Escape Telegram Markdown special characters."""
    if not text:
        return text
    for ch in ("*", "_", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def save_analysis_for_resume(
    reel_id: str,
    analysis: AnalysisResult,
    metadata: ReelMetadata,
    similarity: SimilarityResult,
    costs: CostBreakdown,
    transcript: TranscriptResult,
) -> str:
    """Save analysis artifacts so the pipeline can resume from plan generation."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    plan_dir_name = f"{date_str}_{reel_id}"
    plan_dir = settings.plans_dir / plan_dir_name
    plan_dir.mkdir(parents=True, exist_ok=True)

    (plan_dir / "analysis.json").write_text(
        json.dumps(analysis.model_dump(), indent=2)
    )
    (plan_dir / "metadata.json").write_text(json.dumps({
        "reel_id": reel_id,
        "source_url": metadata.url,
        "creator": metadata.creator,
        "shortcode": metadata.shortcode,
        "caption": metadata.caption,
        "duration": metadata.duration,
        "content_type": metadata.content_type,
        "status": PlanStatus.SKIPPED.value,
        "created_at": datetime.now().isoformat(),
        "cost_breakdown": costs.model_dump() if costs else None,
    }, indent=2))
    (plan_dir / "similarity.json").write_text(
        json.dumps(similarity.model_dump(), indent=2)
    )
    (plan_dir / "transcript.txt").write_text(transcript.text)

    logger.info(f"Saved analysis for resume at {plan_dir}")
    return plan_dir_name


async def send_similarity_notification(
    update: Update,
    reel_id: str,
    analysis: AnalysisResult,
    similarity: SimilarityResult,
    costs: CostBreakdown,
) -> None:
    """Send a Telegram message about detected similarity with action buttons."""
    similar_lines = []
    for sp in similarity.similar_plans:
        overlap = ", ".join(sp.overlap_areas) if sp.overlap_areas else "general"
        similar_lines.append(
            f"  - {_esc(sp.title)} ({sp.score}% match, overlap: {_esc(overlap)})"
        )
    similar_text = "\n".join(similar_lines)
    theme_text = f"*Theme:* {_esc(analysis.theme)}\n" if analysis.theme else ""

    costs.resolve_actual_costs()
    cost_line = ""
    if costs.calls:
        actual = costs.total_actual_cost_usd
        if actual is not None:
            cost_line = f"\n\nAnalysis cost so far: ${actual:.4f} actual (${costs.total_cost_usd:.4f} est\\.)"
        else:
            cost_line = f"\n\nAnalysis cost so far: ${costs.total_cost_usd:.4f} est\\."

    message = (
        f"*Similar content detected*\n\n"
        f"{theme_text}"
        f"*Summary:* {_esc(analysis.summary[:200])}\n\n"
        f"*Similar to:*\n{similar_text}\n\n"
        f"Recommendation: {_esc(similarity.recommendation)}"
        f"{cost_line}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Generate Anyway", callback_data=f"generate_anyway:{reel_id}"),
            InlineKeyboardButton("Skip", callback_data=f"skip_similar:{reel_id}"),
        ]
    ])
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=keyboard)


async def handle_generate_anyway(reel_id: str, query) -> None:
    """Resume the pipeline from plan generation using saved analysis."""
    await query.edit_message_text("Generating plan from saved analysis...")

    try:
        plan_dir = _find_saved_analysis_dir(reel_id)
        if not plan_dir:
            await query.message.reply_text(f"Saved analysis not found for {reel_id}")
            return

        analysis, metadata, transcript, costs, similarity = _load_saved_analysis(reel_id, plan_dir)

        plan, plan_cr = generate_plan(analysis, metadata)
        costs.add(
            "plan", plan_cr.model, plan_cr.prompt_tokens,
            plan_cr.completion_tokens, plan_cr.cost_usd, plan_cr.generation_id,
        )

        result = PipelineResult(
            reel_id=reel_id, status=PlanStatus.REVIEW, metadata=metadata,
            transcript=transcript, analysis=analysis, plan=plan,
            similarity=similarity, cost_breakdown=costs,
        )

        # Remove skipped index entry before write_plan adds the real one
        index = get_index()
        index["plans"] = [
            e for e in index["plans"]
            if not (e["reel_id"] == reel_id and e["status"] == PlanStatus.SKIPPED.value)
        ]
        save_index(index)

        write_plan(result)
        costs.resolve_actual_costs()

        base_url = settings.public_url or f"http://{settings.host}:{settings.port}"
        view_url = f"{base_url}/plans/{reel_id}/view"
        action_line = plan.recommended_action or plan.summary
        await query.message.reply_text(
            f"*{_esc(plan.title)}*\n{_esc(action_line)}\n\n{view_url}",
            parse_mode="Markdown",
        )
        logger.info(f"Telegram: generated plan for {reel_id} (resumed from similarity skip)")

    except Exception as e:
        logger.error(f"Generate-anyway failed for {reel_id}: {e}")
        await query.message.reply_text(f"Failed to generate plan: {e}")


async def handle_skip_similar(reel_id: str, query) -> None:
    """Confirm skipping a similar reel."""
    await query.edit_message_text(
        f"Skipped: `{reel_id}` -- marked as too similar to existing plans.",
        parse_mode="Markdown",
    )
    logger.info(f"User confirmed skip for similar reel {reel_id}")


def _find_saved_analysis_dir(reel_id: str) -> Path | None:
    """Find the plan directory containing saved analysis for a reel_id."""
    for child in sorted(settings.plans_dir.iterdir(), reverse=True):
        if child.is_dir() and child.name.endswith(f"_{reel_id}"):
            if (child / "analysis.json").exists():
                return child
    return None


def _load_saved_analysis(reel_id: str, plan_dir: Path) -> tuple:
    """Load saved analysis artifacts from disk. Returns (analysis, metadata, transcript, costs, similarity)."""
    with open(plan_dir / "analysis.json") as f:
        analysis = AnalysisResult(**json.load(f))

    with open(plan_dir / "metadata.json") as f:
        meta_data = json.load(f)
    metadata = ReelMetadata(
        url=meta_data.get("source_url", ""),
        shortcode=meta_data.get("shortcode", reel_id),
        creator=meta_data.get("creator", ""),
        caption=meta_data.get("caption", ""),
        duration=meta_data.get("duration", 0.0),
        content_type=meta_data.get("content_type", "reel"),
    )

    transcript_path = plan_dir / "transcript.txt"
    transcript_text = transcript_path.read_text() if transcript_path.exists() else ""
    transcript = TranscriptResult(text=transcript_text, language="en")

    costs = CostBreakdown()
    if meta_data.get("cost_breakdown"):
        for call in meta_data["cost_breakdown"].get("calls", []):
            costs.add(
                call["step"], call.get("model", ""),
                call.get("prompt_tokens", 0),
                call.get("completion_tokens", 0),
                call.get("cost_usd", 0.0),
            )

    similarity = None
    similarity_path = plan_dir / "similarity.json"
    if similarity_path.exists():
        with open(similarity_path) as f:
            similarity = SimilarityResult(**json.load(f))

    return analysis, metadata, transcript, costs, similarity
