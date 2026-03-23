"""Feedback storage and retrieval for plan quality tracking."""
import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.config import settings
from src.utils.plan_manager import find_plan_by_id


def save_feedback(reel_id: str, rating: str, comment: str = "") -> bool:
    """Save feedback for a plan.

    Args:
        reel_id: The reel/plan identifier.
        rating: One of "good", "bad", "partial".
        comment: Optional text explaining the rating.

    Returns:
        True if saved successfully, False otherwise.
    """
    if rating not in ("good", "bad", "partial"):
        logger.warning(f"Invalid feedback rating: {rating}")
        return False

    entry = find_plan_by_id(reel_id)
    if not entry:
        logger.warning(f"Cannot save feedback: plan not found for {reel_id}")
        return False

    plan_dir = settings.plans_dir / entry["plan_dir"]
    if not plan_dir.exists():
        logger.warning(f"Cannot save feedback: plan directory missing for {reel_id}")
        return False

    feedback_path = plan_dir / "feedback.json"
    feedback = {
        "reel_id": reel_id,
        "plan_title": entry.get("title", ""),
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(feedback_path, "w") as f:
        json.dump(feedback, f, indent=2)

    logger.info(f"Feedback saved for {reel_id}: {rating}")
    return True


def update_feedback_comment(reel_id: str, comment: str) -> bool:
    """Update the comment on an existing feedback entry.

    Args:
        reel_id: The reel/plan identifier.
        comment: The feedback comment text.

    Returns:
        True if updated successfully, False otherwise.
    """
    entry = find_plan_by_id(reel_id)
    if not entry:
        return False

    feedback_path = settings.plans_dir / entry["plan_dir"] / "feedback.json"
    if not feedback_path.exists():
        return False

    with open(feedback_path) as f:
        feedback = json.load(f)

    feedback["comment"] = comment
    with open(feedback_path, "w") as f:
        json.dump(feedback, f, indent=2)

    logger.info(f"Feedback comment updated for {reel_id}")
    return True


def save_auto_feedback(reel_id: str, lessons: list[str]) -> bool:
    """Save automatically generated feedback from execution results.

    Called after plan execution to record what worked and what didn't.
    These lessons get injected into future plan prompts.
    """
    if not lessons:
        return False

    entry = find_plan_by_id(reel_id)
    if not entry:
        return False

    plan_dir = settings.plans_dir / entry["plan_dir"]
    if not plan_dir.exists():
        return False

    auto_path = plan_dir / "auto_feedback.json"
    data = {
        "reel_id": reel_id,
        "plan_title": entry.get("title", ""),
        "lessons": lessons,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(auto_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Auto-feedback saved for {reel_id}: {len(lessons)} lessons")
    return True


def get_recent_feedback(limit: int = 5) -> list[dict]:
    """Return recent feedback entries across all plans, sorted newest first.

    Args:
        limit: Maximum number of entries to return.

    Returns:
        List of feedback dicts with reel_id, plan_title, rating, comment, created_at.
    """
    entries = []

    # Manual feedback
    for fp in settings.plans_dir.glob("*/feedback.json"):
        try:
            with open(fp) as f:
                data = json.load(f)
            entries.append({
                "reel_id": data.get("reel_id", ""),
                "plan_title": data.get("plan_title", ""),
                "rating": data.get("rating", ""),
                "comment": data.get("comment", ""),
                "created_at": data.get("created_at", ""),
            })
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Failed to read feedback file {fp}: {exc}")

    # Auto-feedback from execution results
    for fp in settings.plans_dir.glob("*/auto_feedback.json"):
        try:
            with open(fp) as f:
                data = json.load(f)
            # Convert lessons to feedback-like entries
            for lesson in data.get("lessons", []):
                rating = "good" if lesson.startswith("GOOD:") else "bad"
                entries.append({
                    "reel_id": data.get("reel_id", ""),
                    "plan_title": data.get("plan_title", ""),
                    "rating": rating,
                    "comment": lesson,
                    "created_at": data.get("created_at", ""),
                })
        except (json.JSONDecodeError, OSError):
            pass

    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return entries[:limit]
