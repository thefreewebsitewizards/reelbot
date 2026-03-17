from src.models import (
    PipelineResult, PlanStatus, ReelMetadata, TranscriptResult,
    AnalysisResult, ImplementationPlan, PlanTask, ContentResponse,
    SimilarityResult, SimilarPlan, ContentComparison, BusinessApplication,
)
from src.utils.html_renderer import render_plan_html


def _make_result(**overrides):
    defaults = dict(
        reel_id="TEST1",
        status=PlanStatus.REVIEW,
        metadata=ReelMetadata(url="https://instagram.com/reel/TEST1", shortcode="TEST1", creator="tester"),
        transcript=TranscriptResult(text="test"),
        analysis=AnalysisResult(
            category="sales", summary="s", key_insights=["i1"], relevance_score=0.9,
            theme="objections", business_impact="Better close rates",
            content_response=ContentResponse(
                react_angle="Share our version",
                corrections=["Wrong stat"],
                repurpose_ideas=["Carousel", "Newsletter"],
                engagement_hook="Great point!",
            ),
        ),
        plan=ImplementationPlan(
            title="Test Plan", summary="A test",
            tasks=[PlanTask(title="T1", description="D1", level=1, tools=["knowledge_base"])],
        ),
    )
    defaults.update(overrides)
    return PipelineResult(**defaults)


class TestNavBar:
    def test_should_include_back_link(self):
        html = render_plan_html(_make_result())
        assert "Plans" in html  # back link text
        assert 'href="/"' in html

    def test_should_include_section_jump_links(self):
        html = render_plan_html(_make_result())
        assert "#section-tasks" in html


class TestComparisonSection:
    def test_should_render_when_comparisons_exist(self):
        result = _make_result(
            similarity=SimilarityResult(
                similar_plans=[SimilarPlan(
                    title="Old Plan", reel_id="OLD1", score=60,
                    comparisons=[ContentComparison(
                        area="sales", current_content="old way", new_content="new way",
                        verdict="better", explanation="clearer",
                    )],
                )],
                recommendation="generate", max_score=60,
            ),
        )
        html = render_plan_html(result)
        assert "Comparison" in html
        assert "old way" in html
        assert "new way" in html

    def test_should_not_render_when_no_comparisons(self):
        result = _make_result(similarity=None)
        html = render_plan_html(result)
        assert "Comparison to Current State" not in html


class TestSocialMediaSection:
    def test_should_render_when_content_response_exists(self):
        html = render_plan_html(_make_result())
        assert "Social Media Play" in html
        assert "Share our version" in html
        assert "Wrong stat" in html

    def test_should_not_render_when_empty(self):
        result = _make_result(
            analysis=AnalysisResult(
                category="sales", summary="s", key_insights=["i"], relevance_score=0.9,
                content_response=ContentResponse(),
            ),
        )
        html = render_plan_html(result)
        assert "Social Media Play" not in html


class TestSectionOrder:
    def test_applications_before_video_breakdown(self):
        result = _make_result(
            analysis=AnalysisResult(
                category="sales", summary="s", key_insights=["i"], relevance_score=0.9,
                business_applications=[
                    BusinessApplication(area="test", recommendation="do it", target_system="ghl", urgency="high"),
                ],
            ),
        )
        html = render_plan_html(result)
        apps_pos = html.find("Business Applications")
        video_pos = html.find("Video Covers") or html.find("section-video")
        if apps_pos > -1 and video_pos > -1:
            assert apps_pos < video_pos


class TestRemovedSections:
    def test_should_not_have_swipe_phrases_section(self):
        html = render_plan_html(_make_result())
        assert "Swipe Phrases" not in html

    def test_should_not_have_standalone_content_angle(self):
        result = _make_result()
        result.plan.content_angle = "Test angle"
        html = render_plan_html(result)
        assert "DDB Content Angle" not in html
