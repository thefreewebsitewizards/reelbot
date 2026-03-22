import json
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.config import settings
from src.utils.auth import require_api_key

router = APIRouter()


@router.get("/health")
async def health():
    """Basic liveness check."""
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    """Readiness check — verifies dependencies are available."""
    checks = {}

    # Check plans directory is writable
    try:
        plans_dir = Path(settings.plans_dir)
        test_file = plans_dir / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
        checks["plans_dir"] = "ok"
    except Exception as e:
        checks["plans_dir"] = f"error: {e}"

    # Check required env vars
    required_vars = ["OPENROUTER_API_KEY", "TELEGRAM_BOT_TOKEN"]
    missing = [v for v in required_vars if not os.getenv(v)]
    checks["env_vars"] = "ok" if not missing else f"missing: {', '.join(missing)}"

    # Check ffmpeg available
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5
        )
        checks["ffmpeg"] = "ok" if result.returncode == 0 else "error"
    except Exception:
        checks["ffmpeg"] = "not found"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
        },
    )


@router.get("/chat-log")
def chat_log(
    tail: int = Query(default=50, le=200),
    fmt: str = Query(default="json", pattern="^(json|txt)$"),
    _: str = Depends(require_api_key),
):
    """Read recent Telegram chat log entries (API key required).

    ?fmt=json returns JSONL entries, ?fmt=txt returns human-readable log.
    """
    if fmt == "txt":
        log_path = Path(settings.plans_dir) / "_telegramlogs.txt"
        if not log_path.exists():
            return {"messages": []}
        lines = log_path.read_text().strip().split("\n")
        return {"messages": lines[-tail:]}

    log_path = Path(settings.plans_dir) / "_chat_log.jsonl"
    if not log_path.exists():
        return {"messages": []}
    lines = log_path.read_text().strip().split("\n")
    entries = []
    for line in lines[-tail:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"messages": entries}
