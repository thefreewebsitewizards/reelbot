import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.models import (
    PipelineResult, PlanStatus, ReelMetadata, TranscriptResult,
    AnalysisResult, ImplementationPlan, PlanTask,
)


def _make_result() -> PipelineResult:
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
    """write_plan should create a plan.json with structured task data."""
    with patch("src.utils.plan_writer.settings") as mock_settings, \
         patch("src.utils.plan_writer.route_plan", return_value="tfww"):
        mock_settings.plans_dir = tmp_path
        from src.utils.plan_writer import write_plan
        result = _make_result()
        write_plan(result)

    plan_json_path = list(tmp_path.glob("*/plan.json"))[0]
    data = json.loads(plan_json_path.read_text())

    assert data["title"] == "Test Plan"
    assert len(data["tasks"]) == 2
    assert data["tasks"][0]["title"] == "Update sales script"
    assert data["tasks"][0]["tools"] == ["sales_script"]
    assert data["tasks"][1]["requires_human"] is True
    assert data["tasks"][1]["human_reason"] == "Needs budget approval"
