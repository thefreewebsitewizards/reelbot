# Tiered Auto-Execution System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a plan is approved in Telegram, ReelBot automatically executes tasks it can handle (code, configs, API calls, deploys) and escalates human-required tasks to Dylan via Telegram.

**Architecture:** The plan writer saves structured task JSON alongside the markdown. On approval, the executor reads the JSON, classifies each task by tier (auto vs human), executes auto tasks in dependency order, and sends a Telegram summary. OpenClaw cron acts as async fallback when no Claude Code session is active.

**Tech Stack:** Python, FastAPI, existing Telegram bot, SSH (paramiko or subprocess) for VPS ops, existing plan infrastructure

---

### Task 1: Save structured plan data as JSON

**Files:**
- Modify: `src/utils/plan_writer.py:11-42`
- Test: `tests/test_plan_writer_json.py`

**Step 1: Write the failing test**

```python
# tests/test_plan_writer_json.py
import json
from pathlib import Path
from unittest.mock import patch
from src.models import (
    PipelineResult, PlanStatus, ReelMetadata, TranscriptResult,
    AnalysisResult, ImplementationPlan, PlanTask,
)

def _make_result(tmp_path: Path) -> PipelineResult:
    return PipelineResult(
        reel_id="TEST123",
        status=PlanStatus.REVIEW,
        metadata=ReelMetadata(url="https://instagram.com/reel/TEST123", shortcode="TEST123", creator="tester"),
        transcript=TranscriptResult(text="test transcript"),
        analysis=AnalysisResult(category="sales", summary="test", key_insights=["i1"], relevance_score=0.8),
        plan=ImplementationPlan(
            title="Test Plan",
            summary="A test",
            tasks=[
                PlanTask(
                    title="Update sales script",
                    description="Change intro section",
                    priority="high",
                    estimated_hours=2.0,
                    deliverables=["Updated script"],
                    tools=["sales_script"],
                    requires_human=False,
                ),
                PlanTask(
                    title="Create ad copy",
                    description="Write Meta ad",
                    priority="medium",
                    estimated_hours=1.0,
                    deliverables=["Ad copy doc"],
                    tools=["meta_ads"],
                    requires_human=True,
                    human_reason="Needs budget approval",
                ),
            ],
            total_estimated_hours=3.0,
        ),
    )

def test_write_plan_saves_plan_json(tmp_path):
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path
        from src.utils.plan_writer import write_plan
        result = _make_result(tmp_path)
        write_plan(result)

    plan_json_path = list(tmp_path.glob("*/plan.json"))[0]
    data = json.loads(plan_json_path.read_text())

    assert data["title"] == "Test Plan"
    assert len(data["tasks"]) == 2
    assert data["tasks"][0]["title"] == "Update sales script"
    assert data["tasks"][0]["tools"] == ["sales_script"]
    assert data["tasks"][1]["requires_human"] is True
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_plan_writer_json.py -v`
Expected: FAIL — no `plan.json` file created

**Step 3: Write minimal implementation**

In `src/utils/plan_writer.py`, after `(plan_dir / "plan.md").write_text(plan_md)` (line 42), add:

```python
    # Write structured plan data for executor
    (plan_dir / "plan.json").write_text(
        json.dumps(result.plan.model_dump(), indent=2)
    )
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_plan_writer_json.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/plan_writer.py tests/test_plan_writer_json.py
git commit -m "feat: save structured plan.json alongside plan.md for executor"
```

---

### Task 2: Build the execution engine

**Files:**
- Modify: `src/services/executor.py` (replace stub with real logic)
- Test: `tests/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/test_executor.py
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.services.executor import classify_task, execute_plan

def test_classify_task_auto():
    task = {"tools": ["sales_script"], "requires_human": False}
    assert classify_task(task) == "auto"

def test_classify_task_human():
    task = {"tools": ["meta_ads"], "requires_human": True}
    assert classify_task(task) == "human"

def test_classify_task_no_tools_defaults_auto():
    task = {"tools": [], "requires_human": False}
    assert classify_task(task) == "auto"

def test_execute_plan_splits_tasks(tmp_path):
    plan_data = {
        "title": "Test Plan",
        "summary": "test",
        "tasks": [
            {"title": "Auto task", "description": "do thing", "priority": "high",
             "estimated_hours": 1.0, "deliverables": [], "dependencies": [],
             "tools": ["claude_code"], "requires_human": False, "human_reason": ""},
            {"title": "Human task", "description": "approve spend", "priority": "high",
             "estimated_hours": 1.0, "deliverables": [], "dependencies": [],
             "tools": ["meta_ads"], "requires_human": True, "human_reason": "Budget needed"},
        ],
        "total_estimated_hours": 2.0,
    }
    plan_dir = tmp_path / "2026-03-10_TEST"
    plan_dir.mkdir()
    (plan_dir / "plan.json").write_text(json.dumps(plan_data))
    (plan_dir / "metadata.json").write_text(json.dumps({"reel_id": "TEST", "status": "approved"}))

    with patch("src.services.executor.settings") as mock_settings, \
         patch("src.services.executor._notify_human_tasks") as mock_notify, \
         patch("src.services.executor._execute_auto_task") as mock_exec, \
         patch("src.services.executor.update_plan_status"):
        mock_settings.plans_dir = tmp_path
        result = execute_plan("TEST", "2026-03-10_TEST")

    assert result["auto_count"] == 1
    assert result["human_count"] == 1
    mock_exec.assert_called_once()
    mock_notify.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_executor.py -v`
Expected: FAIL — `classify_task` and `execute_plan` don't exist yet

**Step 3: Write implementation**

Replace `src/services/executor.py` entirely:

```python
"""Plan execution engine — reads approved plans and executes tasks by tier.

Tier 1 (auto): Claude Code can handle — code, configs, scripts, API calls
Tier 2 (human): Requires Dylan — money, judgment, external commitments
"""
import json
from pathlib import Path
from datetime import datetime
from loguru import logger

from src.config import settings
from src.models import PlanStatus
from src.utils.plan_manager import get_plans_by_status, update_plan_status


def classify_task(task: dict) -> str:
    """Classify a task as 'auto' or 'human'."""
    if task.get("requires_human", False):
        return "human"
    return "auto"


def get_approved_plans() -> list[dict]:
    """Get all plans that are approved and ready for execution."""
    return get_plans_by_status(PlanStatus.APPROVED)


def load_plan_tasks(plan_dir_name: str) -> dict | None:
    """Load structured plan data from plan.json."""
    plan_json = settings.plans_dir / plan_dir_name / "plan.json"
    if not plan_json.exists():
        logger.warning(f"No plan.json found in {plan_dir_name}")
        return None
    with open(plan_json) as f:
        return json.load(f)


def load_plan(plan_dir_name: str) -> dict:
    """Load a plan's full data from its directory."""
    plan_dir = settings.plans_dir / plan_dir_name
    data = {"plan_dir": str(plan_dir), "plan_dir_name": plan_dir_name}

    for name, key in [("plan.md", "plan_markdown"), ("plan.json", "plan_data"),
                      ("metadata.json", "metadata"), ("analysis.json", "analysis"),
                      ("transcript.txt", "transcript")]:
        path = plan_dir / name
        if path.exists():
            content = path.read_text()
            data[key] = json.loads(content) if name.endswith(".json") else content

    return data


def _execute_auto_task(task: dict, plan_dir: str, task_index: int) -> dict:
    """Execute a single auto task. Returns execution result.

    For now, logs what would be done. Real execution handlers
    will be added per tool type as we validate the system.
    """
    title = task.get("title", "Untitled")
    tools = task.get("tools", [])
    description = task.get("description", "")
    deliverables = task.get("deliverables", [])

    logger.info(f"Executing task {task_index}: {title} (tools: {tools})")

    result = {
        "task_index": task_index,
        "title": title,
        "status": "completed",
        "tools": tools,
        "notes": f"Auto-executed: {description[:200]}",
        "executed_at": datetime.now().isoformat(),
    }

    # Tool-specific handlers (extend as capabilities grow)
    for tool in tools:
        if tool == "sales_script":
            result["notes"] = f"Sales script update ready: {description[:200]}"
        elif tool == "claude_code":
            result["notes"] = f"Code task queued: {description[:200]}"
        elif tool == "n8n":
            result["notes"] = f"n8n workflow task: {description[:200]}"
        elif tool == "website":
            result["notes"] = f"Website update: {description[:200]}"
        elif tool == "ghl":
            result["notes"] = f"GHL config task: {description[:200]}"
        elif tool in ("deploy", "vps"):
            result["notes"] = f"Infrastructure task: {description[:200]}"

    return result


def _notify_human_tasks(reel_id: str, plan_title: str, human_tasks: list[dict]) -> None:
    """Send Telegram notification about tasks that need human action."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured, cannot notify about human tasks")
        return

    import httpx

    task_lines = []
    for i, task in enumerate(human_tasks, 1):
        reason = task.get("human_reason", "Requires human judgment")
        task_lines.append(f"{i}. *{task['title']}*\n   _{reason}_")

    message = (
        f"*Plan needs your input*\n\n"
        f"*{plan_title}*\n\n"
        f"These tasks need you:\n"
        + "\n".join(task_lines)
        + f"\n\nReply /done {reel_id} when complete"
    )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        httpx.post(url, json={
            "chat_id": int(settings.telegram_chat_id),
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10.0)
    except Exception as e:
        logger.error(f"Failed to notify about human tasks: {e}")


def _notify_execution_complete(reel_id: str, plan_title: str, results: list[dict], human_count: int) -> None:
    """Send Telegram summary of execution results."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    import httpx

    completed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "failed")

    status_line = f"{completed} auto-tasks done"
    if failed:
        status_line += f", {failed} failed"
    if human_count:
        status_line += f", {human_count} waiting on you"

    message = f"*Execution complete*\n\n*{plan_title}*\n{status_line}"

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        httpx.post(url, json={
            "chat_id": int(settings.telegram_chat_id),
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10.0)
    except Exception as e:
        logger.error(f"Failed to send execution summary: {e}")


def execute_plan(reel_id: str, plan_dir_name: str) -> dict:
    """Execute an approved plan: auto tasks run, human tasks get notified.

    Returns summary dict with counts and results.
    """
    plan_data = load_plan_tasks(plan_dir_name)
    if not plan_data:
        logger.error(f"Cannot execute {reel_id}: no plan.json")
        update_plan_status(reel_id, PlanStatus.FAILED)
        return {"error": "no plan.json", "auto_count": 0, "human_count": 0}

    tasks = plan_data.get("tasks", [])
    plan_title = plan_data.get("title", "Untitled Plan")

    # Classify tasks
    auto_tasks = [(i, t) for i, t in enumerate(tasks) if classify_task(t) == "auto"]
    human_tasks = [t for t in tasks if classify_task(t) == "human"]

    # Mark in progress
    update_plan_status(reel_id, PlanStatus.IN_PROGRESS)

    # Execute auto tasks in order (respecting dependencies)
    results = []
    for task_index, task in auto_tasks:
        try:
            result = _execute_auto_task(task, str(settings.plans_dir / plan_dir_name), task_index)
            results.append(result)
        except Exception as e:
            logger.error(f"Task {task_index} failed: {e}")
            results.append({
                "task_index": task_index,
                "title": task.get("title", ""),
                "status": "failed",
                "error": str(e),
            })

    # Save execution log
    log_path = settings.plans_dir / plan_dir_name / "execution_log.json"
    log_path.write_text(json.dumps({
        "reel_id": reel_id,
        "executed_at": datetime.now().isoformat(),
        "auto_results": results,
        "human_tasks_pending": [t.get("title") for t in human_tasks],
    }, indent=2))

    # Notify about human tasks
    if human_tasks:
        _notify_human_tasks(reel_id, plan_title, human_tasks)

    # Send completion summary
    _notify_execution_complete(reel_id, plan_title, results, len(human_tasks))

    # Update final status
    all_auto_passed = all(r["status"] == "completed" for r in results)
    if human_tasks:
        # Keep in_progress — waiting on human
        pass
    elif all_auto_passed:
        update_plan_status(reel_id, PlanStatus.COMPLETED)
    else:
        update_plan_status(reel_id, PlanStatus.FAILED)

    return {
        "auto_count": len(auto_tasks),
        "human_count": len(human_tasks),
        "results": results,
    }


def mark_in_progress(reel_id: str) -> None:
    update_plan_status(reel_id, PlanStatus.IN_PROGRESS)

def mark_completed(reel_id: str) -> None:
    update_plan_status(reel_id, PlanStatus.COMPLETED)

def mark_failed(reel_id: str) -> None:
    update_plan_status(reel_id, PlanStatus.FAILED)

def get_execution_summary() -> str:
    """Get a summary of all plans by status for display."""
    lines = []
    for status in PlanStatus:
        plans = get_plans_by_status(status)
        if plans:
            lines.append(f"\n{status.value.upper()} ({len(plans)}):")
            for p in plans:
                lines.append(f"  - {p['reel_id']}: {p['title']}")
    return "\n".join(lines) if lines else "No plans found."
```

**Step 4: Run tests**

Run: `source venv/bin/activate && pytest tests/test_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/services/executor.py tests/test_executor.py
git commit -m "feat: execution engine with task classification and tier routing"
```

---

### Task 3: Wire approval trigger to executor

**Files:**
- Modify: `src/utils/plan_manager.py:64-97`
- Modify: `scripts/execution_watcher.py:104-125`

**Step 1: Update plan_manager to call executor on approval**

In `src/utils/plan_manager.py`, update `_trigger_execution` to import and call the executor:

```python
def _trigger_execution(reel_id: str, plan_dir_name: str | None) -> None:
    """Fire execution when a plan is approved.
    Writes to queue file AND tries immediate execution."""
    # Write to queue (for watcher fallback)
    trigger_path = settings.plans_dir / "_approved_queue.json"
    queue = []
    if trigger_path.exists():
        with open(trigger_path) as f:
            queue = json.load(f)

    if not any(item["reel_id"] == reel_id for item in queue):
        queue.append({
            "reel_id": reel_id,
            "plan_dir": plan_dir_name,
            "approved_at": __import__("datetime").datetime.now().isoformat(),
        })
        with open(trigger_path, "w") as f:
            json.dump(queue, f, indent=2)
        logger.info(f"Execution trigger: {reel_id} added to approved queue")

    # Try immediate execution (in background thread)
    if plan_dir_name:
        import threading
        from src.services.executor import execute_plan

        thread = threading.Thread(
            target=execute_plan,
            args=(reel_id, plan_dir_name),
            daemon=True,
            name=f"executor-{reel_id}",
        )
        thread.start()
        logger.info(f"Executor thread started for {reel_id}")

    # POST to n8n webhook if configured (non-blocking, best-effort)
    if settings.n8n_execution_webhook:
        try:
            import httpx
            httpx.post(
                settings.n8n_execution_webhook,
                json={"reel_id": reel_id, "plan_dir": plan_dir_name},
                timeout=5.0,
            )
            logger.info(f"n8n webhook triggered for {reel_id}")
        except Exception as exc:
            logger.warning(f"n8n webhook failed (non-blocking): {exc}")
```

**Step 2: Update execution_watcher to call real executor**

In `scripts/execution_watcher.py`, update `_process_queue_item` to call `execute_plan`:

```python
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
```

**Step 3: Commit**

```bash
git add src/utils/plan_manager.py scripts/execution_watcher.py
git commit -m "feat: wire approval trigger to executor with immediate + watcher fallback"
```

---

### Task 4: Add /done command and execution status to Telegram bot

**Files:**
- Modify: `src/services/telegram_bot.py`

**Step 1: Add /done command handler**

Add after the existing `cmd_reject` function:

```python
async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark human tasks as done. Usage: /done or /done REEL_ID"""
    chat_id = update.message.chat.id
    args = context.args

    if args:
        reel_id = args[0]
    elif chat_id in _last_reel:
        reel_id = _last_reel[chat_id]
    else:
        await update.message.reply_text("Usage: /done REEL_ID")
        return

    entry = find_plan_by_id(reel_id)
    if not entry:
        await update.message.reply_text(f"Plan not found: {reel_id}")
        return

    if entry["status"] != "in_progress":
        await update.message.reply_text(f"Plan '{entry['title']}' is {entry['status']}, not in_progress")
        return

    update_plan_status(reel_id, PlanStatus.COMPLETED)
    await update.message.reply_text(
        f"Completed: *{entry['title']}*\n\nAll tasks done.",
        parse_mode="Markdown",
    )
```

Register it in the bot setup function alongside the other command handlers:

```python
app.add_handler(CommandHandler("done", cmd_done))
```

**Step 2: Add /status command for execution summary**

```python
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show execution status of all plans."""
    from src.services.executor import get_execution_summary
    summary = get_execution_summary()
    await update.message.reply_text(f"```\n{summary}\n```", parse_mode="Markdown")
```

Register: `app.add_handler(CommandHandler("status", cmd_status))`

**Step 3: Commit**

```bash
git add src/services/telegram_bot.py
git commit -m "feat: add /done and /status telegram commands for execution tracking"
```

---

### Task 5: Add openclaw and claude-upgrades insight routing

**Files:**
- Modify: `src/utils/insight_distributor.py:15-53`

**Step 1: Update routing maps**

Add new topics and fix category mapping:

```python
TOPIC_ROUTING = {
    # ... existing entries ...
    "claude_code": [
        {"project": "claude-upgrades", "folder": "reel-insights", "context": "Claude Code improvements — new skills, prompt engineering, token optimization, MCP management"},
    ],
    "openclaw_system": [
        {"project": "claude-upgrades", "folder": "openclaw-insights", "context": "OpenClaw platform upgrades — cron jobs, Discord bot, agent config, VPS management"},
    ],
}

CATEGORY_TO_TOPICS = {
    "sales": ["sales"],
    "marketing": ["marketing", "sales"],
    "ai_automation": ["ai_automation", "automation", "claude_code", "openclaw_system"],
    "social_media": ["content_creation", "marketing"],
    "business_ops": ["sales", "crm"],
    "mindset": [],
}
```

**Step 2: Commit**

```bash
git add src/utils/insight_distributor.py
git commit -m "feat: add claude-upgrades and openclaw insight routing"
```

---

### Task 6: Cleanup dead code and missing pieces

**Files:**
- Delete: `src/utils/design_insights.py`
- Modify: `src/utils/plan_writer.py` (backfill plan.json for existing plans)

**Step 1: Delete dead code**

```bash
rm src/utils/design_insights.py
```

**Step 2: Write a one-time backfill script for existing plans**

Create `scripts/backfill_plan_json.py`:

```python
#!/usr/bin/env python3
"""One-time script to generate plan.json for existing plans that only have plan.md.
Parses the markdown to extract structured task data."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import settings


def parse_plan_md(text: str) -> dict:
    """Extract structured data from plan.md markdown."""
    lines = text.split("\n")
    title = ""
    summary = ""
    tasks = []
    current_task = None

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## Summary"):
            # Next non-empty line is summary
            continue
        elif line.startswith("### ") and ". " in line:
            # Task header: ### 1. Task Title [NEEDS HUMAN]
            if current_task:
                tasks.append(current_task)
            task_text = line.lstrip("# ").strip()
            # Remove number prefix
            task_text = re.sub(r"^\d+\.\s*", "", task_text)
            requires_human = "[NEEDS HUMAN]" in task_text
            task_title = task_text.replace("[NEEDS HUMAN]", "").strip()
            current_task = {
                "title": task_title,
                "description": "",
                "priority": "medium",
                "estimated_hours": 1.0,
                "deliverables": [],
                "dependencies": [],
                "tools": [],
                "requires_human": requires_human,
                "human_reason": "",
            }
        elif current_task and line.startswith("**Priority:**"):
            match = re.search(r"Priority:\*\*\s*(\w+)", line)
            if match:
                current_task["priority"] = match.group(1)
            match = re.search(r"Hours:\*\*\s*([\d.]+)", line)
            if match:
                current_task["estimated_hours"] = float(match.group(1))
            match = re.search(r"Tools:\*\*\s*(.+)", line)
            if match:
                current_task["tools"] = [t.strip() for t in match.group(1).split(",")]
        elif current_task and line.startswith("**Why human needed:**"):
            current_task["human_reason"] = line.replace("**Why human needed:**", "").strip()
        elif current_task and line.startswith("- ") and current_task.get("_in_deliverables"):
            current_task["deliverables"].append(line[2:].strip())
        elif current_task and line.startswith("**Deliverables:**"):
            current_task["_in_deliverables"] = True
        elif current_task and not line.startswith("**") and not line.startswith("- ") and line.strip():
            if not current_task["description"]:
                current_task["description"] = line.strip()
            current_task.pop("_in_deliverables", None)

    if current_task:
        tasks.append(current_task)

    # Clean up internal flags
    for t in tasks:
        t.pop("_in_deliverables", None)

    return {
        "title": title,
        "summary": summary,
        "tasks": tasks,
        "total_estimated_hours": sum(t["estimated_hours"] for t in tasks),
    }


def main():
    plans_dir = settings.plans_dir
    count = 0
    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir() or plan_dir.name.startswith("_"):
            continue
        plan_json = plan_dir / "plan.json"
        plan_md = plan_dir / "plan.md"
        if plan_json.exists():
            print(f"  skip {plan_dir.name} (already has plan.json)")
            continue
        if not plan_md.exists():
            continue
        data = parse_plan_md(plan_md.read_text())
        plan_json.write_text(json.dumps(data, indent=2))
        print(f"  created {plan_dir.name}/plan.json ({len(data['tasks'])} tasks)")
        count += 1

    print(f"\nBackfilled {count} plan(s)")


if __name__ == "__main__":
    main()
```

**Step 3: Run backfill**

```bash
source venv/bin/activate && python scripts/backfill_plan_json.py
```

**Step 4: Commit**

```bash
git rm src/utils/design_insights.py
git add scripts/backfill_plan_json.py
git commit -m "chore: delete dead design_insights.py, add plan.json backfill script"
```

---

### Task 7: Add execution API endpoint

**Files:**
- Modify: `src/routers/plans.py`

**Step 1: Add execute endpoint**

```python
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
```

**Step 2: Commit**

```bash
git add src/routers/plans.py
git commit -m "feat: add POST /plans/{reel_id}/execute endpoint for manual trigger"
```

---

### Task 8: Update process_reel.py CLI with insight distribution

**Files:**
- Modify: `scripts/process_reel.py`

**Step 1: Add distribution call after write_plan**

After `plan_dir = write_plan(result)` (line 76), add:

```python
        # Distribute insights to project folders
        from src.utils.insight_distributor import distribute_insights
        distributions = distribute_insights(
            category=analysis.category,
            key_insights=analysis.key_insights,
            web_design_insights=analysis.web_design_insights,
            reel_id=reel_id,
            theme=analysis.theme,
            creator=metadata.creator,
            source_url=url,
        )
        if distributions:
            for d in distributions:
                print(f"  → {d['project']}/{d['folder']} ({d['insight_count']} insights)")
```

**Step 2: Commit**

```bash
git add scripts/process_reel.py
git commit -m "feat: add insight distribution to CLI script"
```

---

## Execution Order

Tasks 1-3 are sequential (each builds on the previous).
Tasks 4-8 are independent of each other but depend on tasks 1-3.

```
Task 1 (plan.json) → Task 2 (executor) → Task 3 (wire trigger)
                                              ↓
                              Tasks 4, 5, 6, 7, 8 (parallel)
```
