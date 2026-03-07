import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.models import (
    ReelMetadata, TranscriptResult, AnalysisResult,
    ImplementationPlan, PlanTask, PipelineResult, PlanStatus, PlanIndexEntry,
    DetailedNotes, BusinessApplication, FactCheck,
    SimilarPlan, SimilarityResult,
)
from src.utils.plan_writer import write_plan
from src.utils.capability_manager import get_capabilities_context


def _make_analysis(**overrides) -> AnalysisResult:
    """Helper to build an AnalysisResult with all required fields."""
    defaults = dict(
        category="marketing",
        summary="Test summary",
        key_insights=["Insight 1", "Insight 2"],
        relevance_score=0.8,
        theme="Short theme for scanning",
        detailed_notes=DetailedNotes(
            what_it_is="A test reel about marketing",
            how_useful="Demonstrates gift-framing language",
            how_not_useful="Only applies to B2C",
            target_audience="Dylan (sales)",
        ),
        business_applications=[
            BusinessApplication(
                area="Ad copy",
                recommendation="Use gift-framing in Meta ads",
                target_system="meta_ads",
                urgency="high",
            ),
        ],
        business_impact="Could increase CTR by reframing offers as gifts",
        fact_checks=[
            FactCheck(
                claim="Gift-framing increases conversions by 30%",
                verdict="unverified",
                explanation="No source cited in the reel",
            ),
        ],
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


def _make_task(**overrides) -> PlanTask:
    """Helper to build a PlanTask with all required fields."""
    defaults = dict(
        title="Task 1",
        description="Do the thing",
        priority="high",
        estimated_hours=2.0,
        deliverables=["Output 1"],
        tools=["claude_code"],
        requires_human=False,
        human_reason="",
    )
    defaults.update(overrides)
    return PlanTask(**defaults)


def test_plan_writer(tmp_path):
    """Test that plan_writer creates correct directory structure and files."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        result = PipelineResult(
            reel_id="TEST123",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/TEST123/",
                shortcode="TEST123",
                creator="testuser",
                caption="Test caption",
                duration=30.0,
            ),
            transcript=TranscriptResult(
                text="This is a test transcript",
                language="en",
                duration=30.0,
            ),
            analysis=_make_analysis(),
            plan=ImplementationPlan(
                title="Test Plan",
                summary="A test implementation plan",
                tasks=[
                    _make_task(),
                    _make_task(
                        title="Human Task",
                        requires_human=True,
                        human_reason="Needs ad spend approval",
                    ),
                ],
                total_estimated_hours=4.0,
            ),
        )

        plan_dir = write_plan(result)

        assert plan_dir.exists()
        assert (plan_dir / "plan.md").exists()
        assert (plan_dir / "notes.md").exists()
        assert (plan_dir / "metadata.json").exists()
        assert (plan_dir / "transcript.txt").exists()
        assert (plan_dir / "analysis.json").exists()

        # Check transcript content
        assert (plan_dir / "transcript.txt").read_text() == "This is a test transcript"

        # Check metadata
        meta = json.loads((plan_dir / "metadata.json").read_text())
        assert meta["reel_id"] == "TEST123"
        assert meta["creator"] == "testuser"

        # Check plan.md contains new sections
        plan_md = (plan_dir / "plan.md").read_text()
        assert "[NEEDS HUMAN]" in plan_md
        assert "Why This Matters" in plan_md
        assert "Business Applications" in plan_md
        assert "Fact Checks" in plan_md
        assert "Short theme for scanning" in plan_md

        # Check notes.md
        notes_md = (plan_dir / "notes.md").read_text()
        assert "Analysis Notes" in notes_md
        assert "Short theme for scanning" in notes_md

        # Check index has new fields
        index_path = tmp_path / "_index.json"
        assert index_path.exists()
        index = json.loads(index_path.read_text())
        assert len(index["plans"]) == 1
        entry = index["plans"][0]
        assert entry["reel_id"] == "TEST123"
        assert entry["status"] == "review"
        assert entry["theme"] == "Short theme for scanning"
        assert entry["category"] == "marketing"
        assert entry["relevance_score"] == 0.8


def test_plan_index_entry_model():
    entry = PlanIndexEntry(
        reel_id="ABC",
        title="Test",
        status=PlanStatus.REVIEW,
        plan_dir="2026-02-26_ABC",
        created_at="2026-02-26T00:00:00",
        source_url="https://instagram.com/reel/ABC/",
    )
    assert entry.reel_id == "ABC"
    assert entry.status == PlanStatus.REVIEW
    # New fields default to empty/zero
    assert entry.theme == ""
    assert entry.category == ""
    assert entry.relevance_score == 0.0


def test_plan_index_entry_with_new_fields():
    entry = PlanIndexEntry(
        reel_id="ABC",
        title="Test",
        status=PlanStatus.REVIEW,
        plan_dir="2026-02-26_ABC",
        created_at="2026-02-26T00:00:00",
        source_url="https://instagram.com/reel/ABC/",
        theme="Gift-framing for lead gen",
        category="marketing",
        relevance_score=0.9,
    )
    assert entry.theme == "Gift-framing for lead gen"
    assert entry.category == "marketing"
    assert entry.relevance_score == 0.9


def test_analysis_result_score_bounds():
    result = _make_analysis(relevance_score=0.5)
    assert 0.0 <= result.relevance_score <= 1.0

    with pytest.raises(Exception):
        _make_analysis(relevance_score=1.5)


def test_analysis_result_backward_compat():
    """Old analysis data without new fields still parses."""
    result = AnalysisResult(
        category="test",
        summary="test",
        key_insights=["insight"],
        relevance_score=0.5,
    )
    assert result.theme == ""
    assert result.business_impact == ""
    assert result.business_applications == []
    assert result.fact_checks == []
    assert result.detailed_notes.what_it_is == ""


def test_plan_task_backward_compat():
    """Old task data without requires_human still parses."""
    task = PlanTask(
        title="Old task",
        description="From before the upgrade",
    )
    assert task.requires_human is False
    assert task.human_reason == ""


def test_plan_task_human_flag():
    task = _make_task(requires_human=True, human_reason="Needs budget approval")
    assert task.requires_human is True
    assert task.human_reason == "Needs budget approval"


def test_pipeline_result_repurposing_plan_optional():
    """PipelineResult works without repurposing_plan (backward compat)."""
    result = PipelineResult(
        reel_id="X",
        metadata=ReelMetadata(url="https://instagram.com/reel/X/", shortcode="X"),
        transcript=TranscriptResult(text="test"),
        analysis=_make_analysis(),
        plan=ImplementationPlan(title="T", summary="S", tasks=[_make_task()]),
    )
    assert result.repurposing_plan is None


def test_pipeline_result_with_repurposing_plan():
    """PipelineResult accepts a repurposing_plan."""
    rp = ImplementationPlan(
        title="Repurposing: X",
        summary="Content plan",
        tasks=[_make_task(title="Adapted Script", requires_human=True, human_reason="Needs filming")],
        total_estimated_hours=2.0,
    )
    result = PipelineResult(
        reel_id="X",
        metadata=ReelMetadata(url="https://instagram.com/reel/X/", shortcode="X"),
        transcript=TranscriptResult(text="test"),
        analysis=_make_analysis(),
        plan=ImplementationPlan(title="T", summary="S", tasks=[_make_task()]),
        repurposing_plan=rp,
    )
    assert result.repurposing_plan is not None
    assert result.repurposing_plan.title == "Repurposing: X"


def test_capability_manager_loads_json():
    """get_capabilities_context returns formatted text from the real capabilities.json."""
    context = get_capabilities_context()
    assert "ghl" in context
    assert "n8n" in context
    assert "MCP Servers" in context
    assert "Active Integrations" in context


def test_capability_manager_missing_file():
    """get_capabilities_context returns empty string if file doesn't exist."""
    with patch("src.utils.capability_manager.CAPABILITIES_PATH", Path("/nonexistent/capabilities.json")):
        context = get_capabilities_context()
        assert context == ""


def test_plan_writer_creates_view_html(tmp_path):
    """write_plan generates a view.html file."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        result = PipelineResult(
            reel_id="HTML1",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/HTML1/",
                shortcode="HTML1",
                creator="htmluser",
                caption="Test",
                duration=30.0,
            ),
            transcript=TranscriptResult(text="Test transcript", language="en", duration=30.0),
            analysis=_make_analysis(),
            plan=ImplementationPlan(
                title="HTML Test Plan",
                summary="Testing HTML generation",
                tasks=[_make_task()],
                total_estimated_hours=2.0,
            ),
        )

        plan_dir = write_plan(result)

        assert (plan_dir / "view.html").exists()
        html = (plan_dir / "view.html").read_text()
        assert "HTML Test Plan" in html
        assert "Short theme for scanning" in html
        assert "htmluser" in html


def test_plan_writer_creates_repurposing_md(tmp_path):
    """write_plan generates repurposing_plan.md when repurposing_plan is set."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        rp = ImplementationPlan(
            title="Repurposing: RP1",
            summary="Content repurposing plan",
            tasks=[_make_task(title="Write adapted script", requires_human=True, human_reason="Needs filming")],
            total_estimated_hours=1.0,
        )

        result = PipelineResult(
            reel_id="RP1",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/RP1/",
                shortcode="RP1",
                creator="rpuser",
            ),
            transcript=TranscriptResult(text="Test"),
            analysis=_make_analysis(),
            plan=ImplementationPlan(
                title="Test Plan", summary="S", tasks=[_make_task()], total_estimated_hours=2.0,
            ),
            repurposing_plan=rp,
        )

        plan_dir = write_plan(result)

        assert (plan_dir / "repurposing_plan.md").exists()
        rp_md = (plan_dir / "repurposing_plan.md").read_text()
        assert "Repurposing: RP1" in rp_md
        assert "Write adapted script" in rp_md
        assert "[NEEDS HUMAN]" in rp_md

        # HTML should also include repurposing section
        html = (plan_dir / "view.html").read_text()
        assert "Content Repurposing Guide" in html


def test_reel_metadata_content_type_default():
    """ReelMetadata defaults to content_type='reel'."""
    meta = ReelMetadata(url="https://instagram.com/reel/X/", shortcode="X")
    assert meta.content_type == "reel"


def test_reel_metadata_carousel():
    """ReelMetadata accepts content_type='carousel'."""
    meta = ReelMetadata(
        url="https://instagram.com/p/X/", shortcode="X", content_type="carousel",
    )
    assert meta.content_type == "carousel"


def test_pipeline_result_personal_brand_plan_optional():
    """PipelineResult works without personal_brand_plan."""
    result = PipelineResult(
        reel_id="X",
        metadata=ReelMetadata(url="https://instagram.com/reel/X/", shortcode="X"),
        transcript=TranscriptResult(text="test"),
        analysis=_make_analysis(),
        plan=ImplementationPlan(title="T", summary="S", tasks=[_make_task()]),
    )
    assert result.personal_brand_plan is None
    assert result.similarity is None


def test_pipeline_result_with_personal_brand_plan():
    """PipelineResult accepts a personal_brand_plan."""
    pb = ImplementationPlan(
        title="DDB Content: X",
        summary="Personal brand plan",
        tasks=[_make_task(title="Record DDB reel", requires_human=True, human_reason="Needs filming")],
        total_estimated_hours=1.5,
    )
    result = PipelineResult(
        reel_id="X",
        metadata=ReelMetadata(url="https://instagram.com/reel/X/", shortcode="X"),
        transcript=TranscriptResult(text="test"),
        analysis=_make_analysis(),
        plan=ImplementationPlan(title="T", summary="S", tasks=[_make_task()]),
        personal_brand_plan=pb,
    )
    assert result.personal_brand_plan is not None
    assert result.personal_brand_plan.title == "DDB Content: X"


def test_similarity_result_model():
    """SimilarityResult and SimilarPlan models work correctly."""
    sim = SimilarityResult(
        similar_plans=[
            SimilarPlan(title="Existing Plan", reel_id="ABC", score=75, overlap_areas=["ad copy"]),
        ],
        recommendation="merge",
        max_score=75,
    )
    assert sim.max_score == 75
    assert sim.recommendation == "merge"
    assert len(sim.similar_plans) == 1
    assert sim.similar_plans[0].score == 75


def test_similarity_result_empty():
    """SimilarityResult defaults to empty."""
    sim = SimilarityResult()
    assert sim.similar_plans == []
    assert sim.recommendation == "generate"
    assert sim.max_score == 0


def test_pipeline_result_with_similarity():
    """PipelineResult accepts a similarity result."""
    sim = SimilarityResult(
        similar_plans=[SimilarPlan(title="Old Plan", reel_id="OLD", score=60)],
        recommendation="generate",
        max_score=60,
    )
    result = PipelineResult(
        reel_id="X",
        metadata=ReelMetadata(url="https://instagram.com/reel/X/", shortcode="X"),
        transcript=TranscriptResult(text="test"),
        analysis=_make_analysis(),
        plan=ImplementationPlan(title="T", summary="S", tasks=[_make_task()]),
        similarity=sim,
    )
    assert result.similarity is not None
    assert result.similarity.max_score == 60


def test_plan_writer_hides_empty_fact_checks(tmp_path):
    """view.html should not show Fact Checks heading when empty."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        result = PipelineResult(
            reel_id="NOFACT",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/NOFACT/",
                shortcode="NOFACT",
                creator="user",
                duration=30.0,
            ),
            transcript=TranscriptResult(text="Test", language="en", duration=30.0),
            analysis=_make_analysis(fact_checks=[]),
            plan=ImplementationPlan(
                title="Empty Checks Plan",
                summary="Test",
                tasks=[_make_task()],
                total_estimated_hours=2.0,
            ),
        )

        plan_dir = write_plan(result)
        html = (plan_dir / "view.html").read_text()
        # The <h2>Fact Checks</h2> heading should not appear
        assert "<h2>Fact Checks</h2>" not in html


def test_plan_writer_shows_fact_checks_expanded(tmp_path):
    """view.html should show Fact Checks expanded (not collapsible) when populated."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        result = PipelineResult(
            reel_id="HASFACT",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/HASFACT/",
                shortcode="HASFACT",
                creator="user",
                duration=30.0,
            ),
            transcript=TranscriptResult(text="Test", language="en", duration=30.0),
            analysis=_make_analysis(),
            plan=ImplementationPlan(
                title="With Checks Plan",
                summary="Test",
                tasks=[_make_task()],
                total_estimated_hours=2.0,
            ),
        )

        plan_dir = write_plan(result)
        html = (plan_dir / "view.html").read_text()
        assert "<h2>Fact Checks</h2>" in html
        # Should NOT be collapsible (no onclick toggle)
        assert 'collapsible" onclick="toggle(this)">Fact Checks' not in html


def test_plan_writer_creates_personal_brand_md(tmp_path):
    """write_plan generates personal_brand_plan.md when set."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        pb = ImplementationPlan(
            title="DDB Content: PB1",
            summary="Personal brand content plan",
            tasks=[_make_task(title="Record DDB reel", requires_human=True, human_reason="Needs filming")],
            total_estimated_hours=1.0,
        )

        result = PipelineResult(
            reel_id="PB1",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/PB1/",
                shortcode="PB1",
                creator="pbuser",
            ),
            transcript=TranscriptResult(text="Test"),
            analysis=_make_analysis(),
            plan=ImplementationPlan(
                title="Test Plan", summary="S", tasks=[_make_task()], total_estimated_hours=2.0,
            ),
            personal_brand_plan=pb,
        )

        plan_dir = write_plan(result)

        assert (plan_dir / "personal_brand_plan.md").exists()
        pb_md = (plan_dir / "personal_brand_plan.md").read_text()
        assert "DDB Content: PB1" in pb_md
        assert "Record DDB reel" in pb_md

        # HTML should include personal brand section
        html = (plan_dir / "view.html").read_text()
        assert "Dylan Does Business" in html


def test_plan_writer_similarity_in_html(tmp_path):
    """view.html should include similarity callout when present."""
    with patch("src.utils.plan_writer.settings") as mock_settings:
        mock_settings.plans_dir = tmp_path

        sim = SimilarityResult(
            similar_plans=[SimilarPlan(title="Old Plan", reel_id="OLD", score=72, overlap_areas=["ad copy"])],
            recommendation="merge",
            max_score=72,
        )

        result = PipelineResult(
            reel_id="SIM1",
            status=PlanStatus.REVIEW,
            metadata=ReelMetadata(
                url="https://instagram.com/reel/SIM1/",
                shortcode="SIM1",
                creator="simuser",
                duration=30.0,
            ),
            transcript=TranscriptResult(text="Test", language="en", duration=30.0),
            analysis=_make_analysis(),
            plan=ImplementationPlan(
                title="Similar Plan", summary="Test", tasks=[_make_task()], total_estimated_hours=2.0,
            ),
            similarity=sim,
        )

        plan_dir = write_plan(result)
        html = (plan_dir / "view.html").read_text()
        assert "Similar to:" in html
        assert "Old Plan" in html
        assert "72%" in html
