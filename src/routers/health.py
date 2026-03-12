import os
import subprocess
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config import settings

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
