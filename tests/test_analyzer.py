import json
from unittest.mock import patch, MagicMock

from src.models import ReelMetadata, TranscriptResult, ContentResponse
from src.services.analyzer import analyze_reel
from src.services.llm import ChatResult


def _make_chat_result(data: dict) -> ChatResult:
    """Build a ChatResult whose text is the JSON-encoded data."""
    return ChatResult(
        text=json.dumps(data),
        finish_reason="stop",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        cost_usd=0.01,
        generation_id="gen-test-123",
        model="test/model",
    )


def _base_llm_response(**overrides) -> dict:
    """Minimal valid LLM JSON response for the analyzer."""
    base = {
        "category": "marketing",
        "theme": "Test theme",
        "summary": "A test summary of the reel.",
        "video_breakdown": {
            "hook": "A bold opening",
            "main_points": ["Point 1", "Point 2", "Point 3"],
            "key_quotes": ["Quote one", "Quote two"],
            "creator_context": "Known marketing expert",
        },
        "detailed_notes": {
            "what_it_is": "A marketing tip",
            "how_useful": "Directly applicable",
            "how_not_useful": "Not for B2B",
            "target_audience": "Dylan",
        },
        "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
        "business_applications": [
            {
                "area": "Ad copy",
                "recommendation": "Use gift framing",
                "target_system": "meta_ads",
                "urgency": "high",
            }
        ],
        "business_impact": "Could increase CTR",
        "swipe_phrases": ["Use this phrase"],
        "fact_checks": [],
        "routing_target": "tfww",
        "relevance_score": 0.9,
        "web_design_insights": [],
    }
    base.update(overrides)
    return base


def _make_metadata() -> ReelMetadata:
    return ReelMetadata(
        url="https://instagram.com/reel/TEST/",
        shortcode="TEST",
        creator="testuser",
        caption="Test caption",
        duration=30.0,
    )


def _make_transcript() -> TranscriptResult:
    return TranscriptResult(text="This is a test transcript.", language="en", duration=30.0)


@patch("src.services.analyzer.get_model_for_step", return_value="test/model")
@patch("src.services.analyzer.chat")
def test_content_response_parsed_correctly(mock_chat, mock_model):
    """When LLM returns content_response, it should be parsed into ContentResponse."""
    llm_data = _base_llm_response(
        content_response={
            "react_angle": "We should highlight our approach to AI-first automation",
            "corrections": ["The creator claimed X costs $500/mo but it actually starts at $200"],
            "repurpose_ideas": [
                "Carousel on Instagram: 5 slides breaking down the technique",
                "Short reel showing our implementation",
            ],
            "engagement_hook": "Great breakdown! We've been doing something similar with our clients.",
        }
    )
    mock_chat.return_value = _make_chat_result(llm_data)

    result, chat_res = analyze_reel(_make_transcript(), _make_metadata())

    assert result.content_response.react_angle == "We should highlight our approach to AI-first automation"
    assert len(result.content_response.corrections) == 1
    assert "X costs $500/mo" in result.content_response.corrections[0]
    assert len(result.content_response.repurpose_ideas) == 2
    assert "Carousel on Instagram" in result.content_response.repurpose_ideas[0]
    assert result.content_response.engagement_hook == "Great breakdown! We've been doing something similar with our clients."


@patch("src.services.analyzer.get_model_for_step", return_value="test/model")
@patch("src.services.analyzer.chat")
def test_content_response_defaults_when_missing(mock_chat, mock_model):
    """When LLM does not return content_response, defaults should be used."""
    llm_data = _base_llm_response()
    # Ensure no content_response key
    llm_data.pop("content_response", None)
    mock_chat.return_value = _make_chat_result(llm_data)

    result, chat_res = analyze_reel(_make_transcript(), _make_metadata())

    assert result.content_response.react_angle == ""
    assert result.content_response.corrections == []
    assert result.content_response.repurpose_ideas == []
    assert result.content_response.engagement_hook == ""


@patch("src.services.analyzer.get_model_for_step", return_value="test/model")
@patch("src.services.analyzer.chat")
def test_content_response_with_empty_fields(mock_chat, mock_model):
    """When LLM returns content_response with null/empty fields, defaults are used."""
    llm_data = _base_llm_response(
        content_response={
            "react_angle": None,
            "corrections": None,
            "repurpose_ideas": [],
            "engagement_hook": "",
        }
    )
    mock_chat.return_value = _make_chat_result(llm_data)

    result, chat_res = analyze_reel(_make_transcript(), _make_metadata())

    assert result.content_response.react_angle == ""
    assert result.content_response.corrections == []
    assert result.content_response.repurpose_ideas == []
    assert result.content_response.engagement_hook == ""


@patch("src.services.analyzer.get_model_for_step", return_value="test/model")
@patch("src.services.analyzer.chat")
def test_content_response_partial_fields(mock_chat, mock_model):
    """When LLM returns content_response with only some fields, missing ones default."""
    llm_data = _base_llm_response(
        content_response={
            "react_angle": "Our take: this is spot on",
        }
    )
    mock_chat.return_value = _make_chat_result(llm_data)

    result, chat_res = analyze_reel(_make_transcript(), _make_metadata())

    assert result.content_response.react_angle == "Our take: this is spot on"
    assert result.content_response.corrections == []
    assert result.content_response.repurpose_ideas == []
    assert result.content_response.engagement_hook == ""
