import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import (
    AnalysisResult, SimilarityResult, SimilarPlan, ContentComparison, CostBreakdown,
)


@pytest.mark.asyncio
async def test_should_include_comparison_details_in_message():
    analysis = AnalysisResult(
        category="sales", summary="test summary", key_insights=["i"], relevance_score=0.9, theme="objections",
    )
    similarity = SimilarityResult(
        similar_plans=[SimilarPlan(
            title="Old Plan", reel_id="OLD1", score=60, overlap_areas=["sales"],
            comparisons=[
                ContentComparison(
                    area="objection handling",
                    current_content="old approach",
                    new_content="new approach",
                    verdict="better",
                    explanation="clearer steps",
                ),
            ],
        )],
        recommendation="generate", max_score=60,
    )
    costs = CostBreakdown()

    update = MagicMock()
    update.message.reply_text = AsyncMock()

    from src.services.telegram_similarity import send_similarity_notification
    await send_similarity_notification(update, "TEST1", analysis, similarity, costs)

    call_args = update.message.reply_text.call_args
    message_text = call_args[0][0]
    assert "objection handling" in message_text
    assert "clearer steps" in message_text


@pytest.mark.asyncio
async def test_should_show_overlap_when_no_comparisons():
    analysis = AnalysisResult(
        category="sales", summary="test", key_insights=["i"], relevance_score=0.9, theme="t",
    )
    similarity = SimilarityResult(
        similar_plans=[SimilarPlan(
            title="Old Plan", reel_id="OLD1", score=50, overlap_areas=["sales", "marketing"],
        )],
        recommendation="generate", max_score=50,
    )
    costs = CostBreakdown()

    update = MagicMock()
    update.message.reply_text = AsyncMock()

    from src.services.telegram_similarity import send_similarity_notification
    await send_similarity_notification(update, "TEST1", analysis, similarity, costs)

    call_args = update.message.reply_text.call_args
    message_text = call_args[0][0]
    assert "Overlap" in message_text or "sales" in message_text
