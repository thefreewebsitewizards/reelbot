from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config import settings
from src.models import PlanStatus
from src.services.executor import (
    get_approved_plans,
    load_plan,
    get_execution_summary,
)
from src.utils.plan_manager import update_plan_status, get_plans_by_status, find_plan_by_id

router = APIRouter(prefix="/plans")


class StatusUpdate(BaseModel):
    status: PlanStatus


@router.get("/")
def list_plans():
    """List all plans grouped by status."""
    result = {}
    for status in PlanStatus:
        plans = get_plans_by_status(status)
        if plans:
            result[status.value] = plans
    return result


@router.get("/approved")
def list_approved():
    """Get all approved plans ready for execution."""
    return get_approved_plans()


@router.get("/{reel_id}/view", response_class=HTMLResponse)
def view_plan(reel_id: str):
    """Serve the pre-rendered HTML view of a plan."""
    entry = find_plan_by_id(reel_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Plan not found: {reel_id}")
    html_path = settings.plans_dir / entry["plan_dir"] / "view.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="HTML view not generated for this plan")
    return HTMLResponse(html_path.read_text())


@router.get("/{reel_id}")
def get_plan(reel_id: str):
    """Get full plan data for a specific reel."""
    entry = find_plan_by_id(reel_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Plan not found: {reel_id}")
    return load_plan(entry["plan_dir"])


@router.patch("/{reel_id}/status")
def update_status(reel_id: str, body: StatusUpdate):
    """Update a plan's status."""
    updated = update_plan_status(reel_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Plan not found: {reel_id}")
    return {"reel_id": reel_id, "status": body.status.value}


@router.get("/summary/all")
def summary():
    """Get a text summary of all plans."""
    return {"summary": get_execution_summary()}


@router.post("/{reel_id}/execute")
def execute_plan_endpoint(reel_id: str):
    """Manually trigger execution of an approved plan."""
    entry = find_plan_by_id(reel_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Plan {reel_id} not found")
    if entry["status"] != PlanStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail=f"Plan is {entry['status']}, must be approved")

    from src.services.executor import execute_plan
    import threading

    thread = threading.Thread(
        target=execute_plan,
        args=(reel_id, entry["plan_dir"]),
        daemon=True,
    )
    thread.start()

    return {"status": "executing", "reel_id": reel_id}
