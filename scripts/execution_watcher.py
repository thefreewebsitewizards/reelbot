#!/usr/bin/env python3
"""Poll the approved-plan queue and kick off execution.

Run standalone:
    python scripts/execution_watcher.py

Or inside Docker:
    docker compose exec app python scripts/execution_watcher.py

The watcher checks ``plans/_approved_queue.json`` every 60 seconds.
When an approved plan is found it:
  1. Updates the plan status to ``in_progress``
  2. Sends a Telegram notification (if configured)
  3. Removes the item from the queue

Graceful shutdown on SIGINT / SIGTERM.
"""

import json
import signal
import sys
import time
from pathlib import Path

# Ensure project root is importable when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.config import settings
from src.models import PlanStatus
from src.utils.plan_manager import update_plan_status

POLL_INTERVAL_SECONDS = 60

_shutdown_requested = False


def _request_shutdown(signum: int, _frame) -> None:
    """Signal handler -- set flag so the main loop exits cleanly."""
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, shutting down gracefully...")
    _shutdown_requested = True


def _read_queue() -> list[dict]:
    """Read the approved-plan queue from disk."""
    queue_path = settings.plans_dir / "_approved_queue.json"
    if not queue_path.exists():
        return []
    try:
        with open(queue_path) as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            logger.warning("Queue file is not a JSON array, resetting")
            return []
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(f"Failed to read queue: {exc}")
        return []


def _write_queue(queue: list[dict]) -> None:
    """Persist the queue back to disk."""
    queue_path = settings.plans_dir / "_approved_queue.json"
    with open(queue_path, "w") as fh:
        json.dump(queue, fh, indent=2)


def _send_telegram_notification(reel_id: str, plan_title: str) -> None:
    """Best-effort Telegram message that execution is starting."""
    if not settings.telegram_bot_token:
        return
    try:
        import httpx

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        # We don't know the chat_id here, so we log instead.
        # A future enhancement could store the originating chat_id in the queue.
        logger.info(
            f"Telegram notification skipped (no chat_id in queue). "
            f"Plan '{plan_title}' ({reel_id}) is now in_progress."
        )
    except Exception as exc:
        logger.warning(f"Telegram notification failed: {exc}")


def _read_plan_title(plan_dir_name: str) -> str:
    """Extract the plan title from its plan.md file (first heading)."""
    plan_md = settings.plans_dir / plan_dir_name / "plan.md"
    if not plan_md.exists():
        return "(unknown)"
    try:
        for line in plan_md.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped.lstrip("# ").strip()
        return "(untitled)"
    except OSError:
        return "(unreadable)"


def _process_queue_item(item: dict) -> None:
    """Execute a single approved plan."""
    reel_id = item.get("reel_id", "")
    plan_dir_name = item.get("plan_dir", "")

    if not reel_id:
        logger.warning(f"Queue item missing reel_id, skipping: {item}")
        return

    plan_title = _read_plan_title(plan_dir_name) if plan_dir_name else "(no plan_dir)"
    logger.info(f"Executing approved plan: {reel_id} (title={plan_title})")

    from src.services.executor import execute_plan
    try:
        result = execute_plan(reel_id, plan_dir_name)
        logger.info(
            f"Plan {reel_id} execution done: "
            f"{result.get('auto_count', 0)} auto, {result.get('human_count', 0)} human"
        )
    except Exception as e:
        logger.error(f"Execution failed for {reel_id}: {e}")
        update_plan_status(reel_id, PlanStatus.FAILED)


def run_poll_loop() -> None:
    """Main polling loop. Runs until a shutdown signal is received."""
    logger.info(
        f"Execution watcher started. "
        f"Polling every {POLL_INTERVAL_SECONDS}s. "
        f"Plans dir: {settings.plans_dir.resolve()}"
    )

    while not _shutdown_requested:
        queue = _read_queue()

        if queue:
            logger.info(f"Found {len(queue)} item(s) in approved queue")
            processed_ids: list[str] = []

            for item in queue:
                if _shutdown_requested:
                    break
                _process_queue_item(item)
                processed_ids.append(item.get("reel_id", ""))

            # Remove processed items from the queue
            remaining = [
                item for item in _read_queue()
                if item.get("reel_id", "") not in processed_ids
            ]
            _write_queue(remaining)

        # Sleep in short increments so shutdown is responsive
        for _ in range(POLL_INTERVAL_SECONDS):
            if _shutdown_requested:
                break
            time.sleep(1)

    logger.info("Execution watcher stopped")


def main() -> None:
    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)

    run_poll_loop()


if __name__ == "__main__":
    main()
