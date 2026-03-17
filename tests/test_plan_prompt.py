from src.models import AnalysisResult, ReelMetadata
from src.prompts.generate_plan import build_plan_prompt


class TestComparisonInPlanPrompt:
    def test_should_include_comparison_context_when_provided(self):
        analysis = AnalysisResult(
            category="sales", summary="s", key_insights=["i"], relevance_score=0.9, theme="t",
        )
        metadata = ReelMetadata(url="https://instagram.com/reel/X", shortcode="X")

        comparison_context = '- sales: current="old approach", new="new approach" (verdict: better)'

        _, user_prompt = build_plan_prompt(analysis, metadata, comparison_context=comparison_context)

        assert "Comparison to Existing Plans" in user_prompt
        assert "old approach" in user_prompt

    def test_should_not_include_comparison_when_empty(self):
        analysis = AnalysisResult(
            category="sales", summary="s", key_insights=["i"], relevance_score=0.9,
        )
        metadata = ReelMetadata(url="https://instagram.com/reel/X", shortcode="X")

        _, user_prompt = build_plan_prompt(analysis, metadata, comparison_context="")

        assert "Comparison to Existing Plans" not in user_prompt

    def test_should_have_change_type_in_task_schema(self):
        analysis = AnalysisResult(
            category="sales", summary="s", key_insights=["i"], relevance_score=0.9,
        )
        metadata = ReelMetadata(url="https://instagram.com/reel/X", shortcode="X")

        _, user_prompt = build_plan_prompt(analysis, metadata)
        assert "change_type" in user_prompt
