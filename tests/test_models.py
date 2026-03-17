from src.models import (
    ContentComparison, ContentResponse, SimilarPlan, PlanTask, AnalysisResult,
)


class TestContentComparison:
    def test_should_have_all_fields_with_defaults(self):
        cc = ContentComparison()
        assert cc.area == ""
        assert cc.current_content == ""
        assert cc.new_content == ""
        assert cc.verdict == ""
        assert cc.explanation == ""

    def test_should_accept_all_fields(self):
        cc = ContentComparison(
            area="sales objection handling",
            current_content="We currently use the feel-felt-found method",
            new_content="This reel suggests the 3F framework instead",
            verdict="better",
            explanation="More structured approach with clear steps",
        )
        assert cc.verdict == "better"


class TestContentResponse:
    def test_should_have_all_fields_with_defaults(self):
        cr = ContentResponse()
        assert cr.react_angle == ""
        assert cr.corrections == []
        assert cr.repurpose_ideas == []
        assert cr.engagement_hook == ""

    def test_should_accept_all_fields(self):
        cr = ContentResponse(
            react_angle="Share our version",
            corrections=["Wrong stat"],
            repurpose_ideas=["Carousel", "Newsletter"],
            engagement_hook="Great point!",
        )
        assert len(cr.repurpose_ideas) == 2


class TestSimilarPlanComparisons:
    def test_should_have_comparisons_field(self):
        sp = SimilarPlan(title="Test", score=50)
        assert sp.comparisons == []

    def test_should_accept_comparisons(self):
        sp = SimilarPlan(
            title="Test", score=50,
            comparisons=[ContentComparison(area="sales", verdict="better")],
        )
        assert len(sp.comparisons) == 1


class TestPlanTaskChangeType:
    def test_should_default_to_empty_string(self):
        task = PlanTask(title="t", description="d")
        assert task.change_type == ""

    def test_should_accept_change_type(self):
        task = PlanTask(title="t", description="d", change_type="replacement")
        assert task.change_type == "replacement"


class TestAnalysisResultContentResponse:
    def test_should_have_content_response_field(self):
        ar = AnalysisResult(
            category="sales", summary="s", key_insights=["i"], relevance_score=0.8,
        )
        assert ar.content_response is not None
        assert ar.content_response.react_angle == ""

    def test_should_accept_content_response(self):
        ar = AnalysisResult(
            category="sales", summary="s", key_insights=["i"], relevance_score=0.8,
            content_response=ContentResponse(react_angle="React here"),
        )
        assert ar.content_response.react_angle == "React here"
