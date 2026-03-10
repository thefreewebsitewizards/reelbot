import json
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
         patch("src.services.executor._notify_execution_complete"), \
         patch("src.services.executor.update_plan_status"):
        mock_settings.plans_dir = tmp_path
        result = execute_plan("TEST", "2026-03-10_TEST")

    assert result["auto_count"] == 1
    assert result["human_count"] == 1
    mock_notify.assert_called_once()


def test_execute_plan_no_plan_json(tmp_path):
    plan_dir = tmp_path / "2026-03-10_MISSING"
    plan_dir.mkdir()

    with patch("src.services.executor.settings") as mock_settings, \
         patch("src.services.executor.update_plan_status"):
        mock_settings.plans_dir = tmp_path
        result = execute_plan("MISSING", "2026-03-10_MISSING")

    assert result["auto_count"] == 0
    assert "error" in result
