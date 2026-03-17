"""Tests for the planner service — similarity checking and enrichment."""

import json
from unittest.mock import patch, MagicMock

from src.models import AnalysisResult, SimilarPlan, ContentComparison
from src.services.llm import ChatResult
from src.services.planner import check_plan_similarity


def _make_analysis(**overrides) -> AnalysisResult:
    defaults = dict(
        category="marketing",
        summary="Test summary about gift-framing",
        key_insights=["Insight 1", "Insight 2"],
        relevance_score=0.8,
        theme="Gift-framing for lead gen",
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


def _similarity_response(score: int = 60) -> str:
    """Build a JSON string mimicking the similarity LLM response."""
    return json.dumps({
        "similar_plans": [
            {
                "title": "Old Gift Plan",
                "reel_id": "ABC123",
                "score": score,
                "overlap_areas": ["ad copy", "lead gen"],
            }
        ],
        "recommendation": "generate",
    })


def _enrichment_response() -> str:
    """Build a JSON string mimicking the enrichment LLM response."""
    return json.dumps({
        "comparisons": [
            {
                "area": "Ad copy framing",
                "current_content": "Old plan uses discount framing",
                "new_content": "New reel suggests gift framing",
                "verdict": "better",
                "explanation": "Gift framing converts higher than discounts",
            },
            {
                "area": "Lead gen funnel",
                "current_content": "Old plan uses landing page",
                "new_content": "New reel adds chatbot step",
                "verdict": "different_angle",
                "explanation": "Chatbot adds conversational element",
            },
        ]
    })


@patch("src.services.planner.get_model_for_step", return_value="test-model")
@patch("src.services.planner.load_plan_content")
@patch("src.services.planner.chat")
@patch("src.services.planner.get_past_plan_summaries")
def test_similarity_enrichment_populates_comparisons(
    mock_summaries, mock_chat, mock_load_content, mock_model,
):
    """When similarity is detected with score > 30, comparisons are populated."""
    mock_summaries.return_value = "- [ABC123] Old Gift Plan: Update ad copy"

    # First call: similarity check. Second call: enrichment.
    mock_chat.side_effect = [
        ChatResult(text=_similarity_response(score=60)),
        ChatResult(text=_enrichment_response()),
    ]
    mock_load_content.return_value = "# Old Gift Plan\nSome plan content here"

    analysis = _make_analysis()
    result, chat_result = check_plan_similarity(analysis)

    assert len(result.similar_plans) == 1
    plan = result.similar_plans[0]
    assert plan.score == 60
    assert len(plan.comparisons) == 2
    assert plan.comparisons[0].area == "Ad copy framing"
    assert plan.comparisons[0].verdict == "better"
    assert plan.comparisons[1].verdict == "different_angle"

    # Two LLM calls: one for similarity, one for enrichment
    assert mock_chat.call_count == 2
    mock_load_content.assert_called_once_with("ABC123")


@patch("src.services.planner.get_model_for_step", return_value="test-model")
@patch("src.services.planner.load_plan_content")
@patch("src.services.planner.chat")
@patch("src.services.planner.get_past_plan_summaries")
def test_no_similar_plans_no_enrichment(
    mock_summaries, mock_chat, mock_load_content, mock_model,
):
    """When no similar plans exist, no enrichment call is made."""
    mock_summaries.return_value = "- [XYZ] Some other plan"

    mock_chat.return_value = ChatResult(
        text=json.dumps({
            "similar_plans": [],
            "recommendation": "generate",
        })
    )

    analysis = _make_analysis()
    result, _ = check_plan_similarity(analysis)

    assert len(result.similar_plans) == 0
    assert mock_chat.call_count == 1
    mock_load_content.assert_not_called()


@patch("src.services.planner.get_model_for_step", return_value="test-model")
@patch("src.services.planner.load_plan_content")
@patch("src.services.planner.chat")
@patch("src.services.planner.get_past_plan_summaries")
def test_enrichment_failure_does_not_crash(
    mock_summaries, mock_chat, mock_load_content, mock_model,
):
    """When enrichment fails, it doesn't crash — comparisons stay empty."""
    mock_summaries.return_value = "- [ABC123] Old Gift Plan: Update ad copy"

    # First call: similarity check succeeds. Second call: enrichment raises.
    mock_chat.side_effect = [
        ChatResult(text=_similarity_response(score=75)),
        Exception("LLM service down"),
    ]
    mock_load_content.return_value = "# Old Gift Plan\nContent"

    analysis = _make_analysis()
    result, _ = check_plan_similarity(analysis)

    assert len(result.similar_plans) == 1
    plan = result.similar_plans[0]
    assert plan.score == 75
    assert plan.comparisons == []
    assert result.recommendation == "generate"


@patch("src.services.planner.get_model_for_step", return_value="test-model")
@patch("src.services.planner.load_plan_content")
@patch("src.services.planner.chat")
@patch("src.services.planner.get_past_plan_summaries")
def test_no_existing_plans_returns_early(
    mock_summaries, mock_chat, mock_load_content, mock_model,
):
    """When get_past_plan_summaries returns empty, return early with no LLM calls."""
    mock_summaries.return_value = ""

    analysis = _make_analysis()
    result, chat_result = check_plan_similarity(analysis)

    assert result.similar_plans == []
    assert result.recommendation == "generate"
    assert chat_result is None
    mock_chat.assert_not_called()
    mock_load_content.assert_not_called()


@patch("src.services.planner.get_model_for_step", return_value="test-model")
@patch("src.services.planner.load_plan_content")
@patch("src.services.planner.chat")
@patch("src.services.planner.get_past_plan_summaries")
def test_enrichment_skipped_when_plan_content_empty(
    mock_summaries, mock_chat, mock_load_content, mock_model,
):
    """When load_plan_content returns empty, skip the enrichment LLM call."""
    mock_summaries.return_value = "- [ABC123] Old Plan: task"

    mock_chat.return_value = ChatResult(text=_similarity_response(score=50))
    mock_load_content.return_value = ""

    analysis = _make_analysis()
    result, _ = check_plan_similarity(analysis)

    assert len(result.similar_plans) == 1
    assert result.similar_plans[0].comparisons == []
    # Only the similarity call, no enrichment call
    assert mock_chat.call_count == 1
