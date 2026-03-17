# Similarity + Plan View Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich similarity checks with actual plan content comparisons, add social media section to analysis, restructure the HTML plan view for better UX, and update Telegram messages with comparison details.

**Architecture:** New `ContentComparison` and `ContentResponse` Pydantic models feed richer data through the existing pipeline. The similarity checker loads plan.md content for top matches and asks the LLM for per-area verdicts. The HTML template gets a nav bar, reordered sections, and two new sections (comparison + social media). All changes are additive — no breaking changes to the execution engine or approval flow.

**Tech Stack:** Python/FastAPI, Pydantic models, OpenRouter LLM, HTML/CSS/JS template

---

### Task 1: Add new models to `src/models.py`

**Files:**
- Modify: `src/models.py`
- Test: `tests/test_models.py` (create)

**Step 1: Write the failing tests**

```python
# tests/test_models.py
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
        from src.models import PlanTask
        task = PlanTask(title="t", description="d")
        assert task.change_type == ""


class TestAnalysisResultContentResponse:
    def test_should_have_content_response_field(self):
        ar = AnalysisResult(category="sales", summary="s", key_insights=["i"], relevance_score=0.8)
        assert ar.content_response is not None
        assert ar.content_response.react_angle == ""
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ContentComparison`, `ContentResponse` not importable, `comparisons` field missing from `SimilarPlan`, `change_type` missing from `PlanTask`, `content_response` missing from `AnalysisResult`

**Step 3: Add the models and fields**

In `src/models.py`, add after `FactCheck`:

```python
class ContentComparison(BaseModel):
    area: str = ""
    current_content: str = ""
    new_content: str = ""
    verdict: str = ""  # better | worse | same | different_angle
    explanation: str = ""


class ContentResponse(BaseModel):
    react_angle: str = ""
    corrections: list[str] = []
    repurpose_ideas: list[str] = []
    engagement_hook: str = ""
```

Add to `SimilarPlan`:
```python
comparisons: list[ContentComparison] = []
```

Add to `PlanTask`:
```python
change_type: str = ""  # addition | replacement | reinforcement | ignore
```

Add to `AnalysisResult`:
```python
content_response: ContentResponse = Field(default_factory=ContentResponse)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: All PASS

**Step 5: Run full test suite to verify no regressions**

Run: `pytest tests/ -v`
Expected: All 75+ tests PASS

**Step 6: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add ContentComparison, ContentResponse models and new fields"
```

---

### Task 2: Enrich similarity check in `src/services/planner.py`

**Files:**
- Modify: `src/services/planner.py`
- Modify: `src/utils/plan_manager.py` (add helper to load plan.md content by reel_id)
- Test: `tests/test_planner.py` (create)

**Step 1: Write the failing tests**

```python
# tests/test_planner.py
import json
from unittest.mock import patch, MagicMock
from src.models import AnalysisResult, ContentComparison, SimilarPlan


class TestEnrichedSimilarity:
    def test_should_return_comparisons_in_similar_plans(self):
        """When similarity is detected, comparisons should be populated."""
        mock_analysis = AnalysisResult(
            category="sales", summary="test", key_insights=["i"], relevance_score=0.9, theme="objections",
        )

        # Mock LLM responses: first call = basic similarity, second call = enriched comparison
        basic_response = json.dumps({
            "similar_plans": [{"title": "Old Plan", "reel_id": "OLD1", "score": 60, "overlap_areas": ["sales"]}],
            "recommendation": "generate",
        })
        enriched_response = json.dumps({
            "comparisons": [
                {"area": "objection handling", "current_content": "old approach", "new_content": "new approach", "verdict": "better", "explanation": "clearer steps"},
            ]
        })

        with patch("src.services.planner.get_past_plan_summaries", return_value="- [OLD1] Old Plan: task1"), \
             patch("src.services.planner.load_plan_content", return_value="# Old Plan\nold content"), \
             patch("src.services.planner.chat") as mock_chat, \
             patch("src.services.planner.get_model_for_step", return_value="test-model"):

            mock_chat.side_effect = [
                MagicMock(text=basic_response),
                MagicMock(text=enriched_response),
            ]

            from src.services.planner import check_plan_similarity
            result, _ = check_plan_similarity(mock_analysis)

            assert len(result.similar_plans) == 1
            assert len(result.similar_plans[0].comparisons) == 1
            assert result.similar_plans[0].comparisons[0].verdict == "better"

    def test_should_skip_enrichment_when_no_similar_plans(self):
        """No enrichment LLM call when no plans are similar."""
        mock_analysis = AnalysisResult(
            category="sales", summary="test", key_insights=["i"], relevance_score=0.9,
        )
        empty_response = json.dumps({"similar_plans": [], "recommendation": "generate"})

        with patch("src.services.planner.get_past_plan_summaries", return_value="- [X] Plan"), \
             patch("src.services.planner.chat") as mock_chat, \
             patch("src.services.planner.get_model_for_step", return_value="test"):

            mock_chat.return_value = MagicMock(text=empty_response)

            from src.services.planner import check_plan_similarity
            result, _ = check_plan_similarity(mock_analysis)

            assert result.similar_plans == []
            assert mock_chat.call_count == 1  # Only the basic call, no enrichment
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_planner.py -v`
Expected: FAIL — `load_plan_content` doesn't exist, comparisons not populated

**Step 3: Add `load_plan_content` to `src/utils/plan_manager.py`**

Add at the end of `plan_manager.py`:

```python
def load_plan_content(reel_id: str) -> str:
    """Load the plan.md content for a given reel_id. Returns empty string if not found."""
    index = get_index()
    for entry in reversed(index["plans"]):
        if entry["reel_id"] == reel_id:
            plan_md = settings.plans_dir / entry["plan_dir"] / "plan.md"
            if plan_md.exists():
                content = plan_md.read_text()
                # Truncate to ~2000 chars to keep token cost reasonable
                return content[:2000]
    return ""
```

**Step 4: Update `check_plan_similarity` in `src/services/planner.py`**

After the basic similarity call succeeds and returns plans with score > 30, add an enrichment step:

```python
from src.utils.plan_manager import get_past_plan_summaries, load_plan_content
from src.models import ContentComparison

# ... after parsing basic similarity results ...

# Enrich top matches with content comparisons
top_matches = [p for p in similar if p.score > 30]
if top_matches:
    _enrich_with_comparisons(analysis, top_matches)
```

New function `_enrich_with_comparisons`:

```python
def _enrich_with_comparisons(analysis: AnalysisResult, plans: list[SimilarPlan]) -> None:
    """Load plan.md for top matches and ask LLM for per-area comparisons."""
    for plan in plans[:3]:  # Max 3
        content = load_plan_content(plan.reel_id)
        if not content:
            continue

        system = "You compare content from two sources. Respond with valid JSON only."
        user_content = f"""Compare what we already have vs what this new reel adds.

**Existing plan content:**
{content}

**New reel analysis:**
- Theme: {analysis.theme}
- Summary: {analysis.summary}
- Key insights: {', '.join(analysis.key_insights[:5])}

Return JSON:
{{
  "comparisons": [
    {{
      "area": "specific topic area",
      "current_content": "what existing plan says (1 sentence)",
      "new_content": "what new reel adds (1 sentence)",
      "verdict": "better|worse|same|different_angle",
      "explanation": "1 sentence why"
    }}
  ]
}}

Rules:
- Maximum 3 comparisons per plan
- Only include areas where there is meaningful overlap or difference
- "better" = new reel has clearly superior approach
- "different_angle" = both valid, different perspectives"""

        try:
            cr = chat(system=system, user_content=user_content, max_tokens=500, model_override=get_model_for_step("similarity"))
            data = extract_json(cr.text, context="similarity_enrich")
            plan.comparisons = [
                ContentComparison(
                    area=c.get("area", ""),
                    current_content=c.get("current_content", ""),
                    new_content=c.get("new_content", ""),
                    verdict=c.get("verdict", ""),
                    explanation=c.get("explanation", ""),
                )
                for c in data.get("comparisons", [])
            ]
        except Exception as e:
            logger.warning(f"Enrichment failed for {plan.reel_id}: {e}")
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_planner.py -v`
Expected: All PASS

**Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/services/planner.py src/utils/plan_manager.py tests/test_planner.py
git commit -m "feat: enrich similarity check with plan.md content comparisons"
```

---

### Task 3: Add content response to analysis prompt + parser

**Files:**
- Modify: `src/prompts/analyze_reel.py`
- Modify: `src/services/analyzer.py`
- Test: `tests/test_analyzer.py` (create)

**Step 1: Write the failing test**

```python
# tests/test_analyzer.py
import json
from unittest.mock import patch, MagicMock
from src.models import TranscriptResult, ReelMetadata


class TestContentResponseParsing:
    def test_should_parse_content_response_from_llm(self):
        """analyzer should parse the content_response field from LLM output."""
        llm_output = json.dumps({
            "category": "sales",
            "theme": "objection handling",
            "summary": "How to handle price objections",
            "video_breakdown": {"hook": "h", "main_points": ["p1"], "key_quotes": ["q1"], "creator_context": ""},
            "detailed_notes": {"what_it_is": "", "how_useful": "", "how_not_useful": "", "target_audience": ""},
            "key_insights": ["insight1"],
            "business_applications": [],
            "business_impact": "Better close rates",
            "swipe_phrases": [],
            "fact_checks": [],
            "routing_target": "tfww",
            "relevance_score": 0.9,
            "web_design_insights": [],
            "content_response": {
                "react_angle": "Share our version of this technique with results",
                "corrections": ["The 3% close rate claim is outdated"],
                "repurpose_ideas": ["Turn into carousel", "Add to newsletter"],
                "engagement_hook": "Great framework! We've found step 2 works even better when..."
            }
        })

        with patch("src.services.analyzer.chat") as mock_chat, \
             patch("src.services.analyzer.get_model_for_step", return_value="test"):
            mock_chat.return_value = MagicMock(text=llm_output, finish_reason="stop", prompt_tokens=100, completion_tokens=200, total_tokens=300, cost_usd=0.01, generation_id="gen1", model="test")

            from src.services.analyzer import analyze_reel
            result, _ = analyze_reel(
                TranscriptResult(text="test transcript"),
                ReelMetadata(url="https://instagram.com/reel/X", shortcode="X"),
            )

            assert result.content_response.react_angle == "Share our version of this technique with results"
            assert len(result.content_response.corrections) == 1
            assert len(result.content_response.repurpose_ideas) == 2
            assert "Great framework" in result.content_response.engagement_hook

    def test_should_default_content_response_when_missing(self):
        """If LLM doesn't return content_response, it should default to empty."""
        llm_output = json.dumps({
            "category": "sales", "theme": "t", "summary": "s",
            "video_breakdown": {"hook": "", "main_points": [], "key_quotes": [], "creator_context": ""},
            "detailed_notes": {"what_it_is": "", "how_useful": "", "how_not_useful": "", "target_audience": ""},
            "key_insights": ["i"], "business_applications": [], "business_impact": "",
            "swipe_phrases": [], "fact_checks": [], "routing_target": "tfww",
            "relevance_score": 0.8, "web_design_insights": [],
        })

        with patch("src.services.analyzer.chat") as mock_chat, \
             patch("src.services.analyzer.get_model_for_step", return_value="test"):
            mock_chat.return_value = MagicMock(text=llm_output, finish_reason="stop", prompt_tokens=100, completion_tokens=200, total_tokens=300, cost_usd=0.01, generation_id="gen1", model="test")

            from src.services.analyzer import analyze_reel
            result, _ = analyze_reel(
                TranscriptResult(text="test"),
                ReelMetadata(url="https://instagram.com/reel/X", shortcode="X"),
            )

            assert result.content_response.react_angle == ""
            assert result.content_response.corrections == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_analyzer.py -v`
Expected: FAIL — `content_response` not parsed from LLM output

**Step 3: Add `content_response` to the analysis prompt**

In `src/prompts/analyze_reel.py`, add to the JSON schema in `USER_TEMPLATE` (after `"web_design_insights"`):

```python
  "content_response": {{
    "react_angle": "How to respond/react to build authority — frame as 'We should...' or 'Our take...'",
    "corrections": ["Things the video got wrong we can correct publicly — only include if genuinely wrong"],
    "repurpose_ideas": ["How to take this content for our channels — specific format + platform"],
    "engagement_hook": "Suggested comment or reply to the original post — natural, not salesy"
  }}
```

Add rules after the web_design_insights rules:

```
Rules for content_response:
- react_angle: How we'd publicly respond to this content. Frame as authority building, not criticism
- corrections: Only include if the creator made factually wrong claims. Empty array if nothing wrong
- repurpose_ideas: Specific format (carousel, reel, newsletter) + which platform. Max 3
- engagement_hook: A natural-sounding comment we could leave on the original post. Skip if no good angle
```

Also add the same field to the carousel prompt `CAROUSEL_USER_TEMPLATE`.

**Step 4: Parse `content_response` in `src/services/analyzer.py`**

In `analyze_reel()`, after parsing `fact_checks`, add:

```python
from src.models import ContentResponse

# Parse content response
cr_data = data.get("content_response") or {}
content_response = ContentResponse(
    react_angle=cr_data.get("react_angle") or "",
    corrections=cr_data.get("corrections") or [],
    repurpose_ideas=cr_data.get("repurpose_ideas") or [],
    engagement_hook=cr_data.get("engagement_hook") or "",
)
```

Add `content_response=content_response` to the `AnalysisResult(...)` constructor.

Do the same in `analyze_carousel()`.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_analyzer.py -v`
Expected: All PASS

**Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/prompts/analyze_reel.py src/services/analyzer.py tests/test_analyzer.py
git commit -m "feat: add content_response (social media play) to analysis pipeline"
```

---

### Task 4: Feed comparison context into plan prompt + add `change_type`

**Files:**
- Modify: `src/prompts/generate_plan.py`
- Modify: `src/services/planner.py` (`generate_plan` function)

**Step 1: Write the failing test**

```python
# tests/test_plan_prompt.py
from src.models import (
    AnalysisResult, ReelMetadata, SimilarityResult, SimilarPlan, ContentComparison,
)
from src.prompts.generate_plan import build_plan_prompt


class TestComparisonInPlanPrompt:
    def test_should_include_comparison_context_when_available(self):
        """Plan prompt should include similarity comparison data."""
        analysis = AnalysisResult(
            category="sales", summary="s", key_insights=["i"], relevance_score=0.9,
            theme="objections",
        )
        metadata = ReelMetadata(url="https://instagram.com/reel/X", shortcode="X")

        comparison_context = (
            "## Comparison to Existing Plans\n"
            "- Sales objection handling: current=feel-felt-found, new=3F framework (verdict: better)"
        )

        _, user_prompt = build_plan_prompt(
            analysis, metadata, comparison_context=comparison_context,
        )

        assert "Comparison to Existing Plans" in user_prompt
        assert "feel-felt-found" in user_prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_plan_prompt.py -v`
Expected: FAIL — `comparison_context` param doesn't exist

**Step 3: Add `comparison_context` parameter to `build_plan_prompt`**

In `src/prompts/generate_plan.py`, add `comparison_context: str = ""` to `build_plan_prompt` params.

Add a new section template:

```python
COMPARISON_SECTION = """

**Comparison to Existing Plans (use this to set change_type on tasks):**
{comparison_context}

When you see a comparison:
- verdict "better" → task change_type should be "replacement"
- verdict "different_angle" → task change_type should be "addition"
- verdict "same" → task change_type should be "reinforcement" (or skip the task)
- verdict "worse" → task change_type should be "ignore" (don't create a task for it)"""
```

Add `"change_type": "addition|replacement|reinforcement|ignore"` to the task JSON schema in `USER_TEMPLATE`.

At the end of `build_plan_prompt`, if `comparison_context`:

```python
if comparison_context:
    user_prompt += COMPARISON_SECTION.format(comparison_context=comparison_context)
```

**Step 4: Update `generate_plan` in `planner.py` to build and pass comparison context**

In `generate_plan`, add `similarity: SimilarityResult | None = None` parameter. Build comparison text from `similarity.similar_plans[*].comparisons` and pass to `build_plan_prompt`.

```python
comparison_context = ""
if similarity:
    lines = []
    for sp in similarity.similar_plans:
        if sp.comparisons:
            for c in sp.comparisons:
                lines.append(f"- {c.area}: current={c.current_content}, new={c.new_content} (verdict: {c.verdict})")
    if lines:
        comparison_context = "\n".join(lines)

system_prompt, user_prompt = build_plan_prompt(
    analysis, metadata, existing_plans, script_context, script_section_ids,
    capabilities_context=capabilities,
    user_context=user_context,
    comparison_context=comparison_context,
)
```

Parse `change_type` from task JSON in `generate_plan`:

```python
# In the task parsing loop, add:
change_type=t.get("change_type") or "",
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_plan_prompt.py tests/test_planner.py -v`
Expected: All PASS

**Step 6: Update callers of `generate_plan` to pass similarity**

In `src/services/telegram_similarity.py:handle_generate_anyway`, pass `similarity` to `generate_plan`:

```python
plan, plan_cr = generate_plan(analysis, metadata, similarity=similarity)
```

In `src/routers/reel.py` (main pipeline), pass `similarity` if available:

```python
plan, plan_cr = generate_plan(analysis, metadata, user_context=..., similarity=similarity_result)
```

**Step 7: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 8: Commit**

```bash
git add src/prompts/generate_plan.py src/services/planner.py src/services/telegram_similarity.py src/routers/reel.py tests/test_plan_prompt.py
git commit -m "feat: feed comparison context into plan prompt with change_type on tasks"
```

---

### Task 5: Restructure HTML plan view

**Files:**
- Modify: `static/plan_view.html`
- Modify: `src/utils/html_renderer.py`
- Test: `tests/test_html_renderer.py` (create)

**Step 1: Write the failing tests**

```python
# tests/test_html_renderer.py
from src.models import (
    PipelineResult, PlanStatus, ReelMetadata, TranscriptResult,
    AnalysisResult, ImplementationPlan, PlanTask, ContentResponse,
    SimilarityResult, SimilarPlan, ContentComparison,
)
from src.utils.html_renderer import render_plan_html


def _make_result(**overrides) -> PipelineResult:
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
        assert 'href="/"' in html or "Back" in html

    def test_should_include_section_jump_links(self):
        html = render_plan_html(_make_result())
        assert 'id="section-applications"' in html or 'id="section-tasks"' in html


class TestComparisonSection:
    def test_should_render_when_comparisons_exist(self):
        result = _make_result(
            similarity=SimilarityResult(
                similar_plans=[SimilarPlan(
                    title="Old Plan", reel_id="OLD1", score=60,
                    comparisons=[ContentComparison(
                        area="sales", current_content="old", new_content="new", verdict="better", explanation="clearer",
                    )],
                )],
                recommendation="generate", max_score=60,
            ),
        )
        html = render_plan_html(result)
        assert "Comparison" in html
        assert "better" in html.lower() or "BETTER" in html

    def test_should_not_render_when_no_comparisons(self):
        result = _make_result(similarity=None)
        html = render_plan_html(result)
        assert "Comparison to Current State" not in html


class TestSocialMediaSection:
    def test_should_render_when_content_response_exists(self):
        html = render_plan_html(_make_result())
        assert "Social Media Play" in html
        assert "Share our version" in html

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
        """Business applications should appear before video breakdown in HTML."""
        result = _make_result(
            analysis=AnalysisResult(
                category="sales", summary="s", key_insights=["i"], relevance_score=0.9,
                business_applications=[
                    __import__("src.models", fromlist=["BusinessApplication"]).BusinessApplication(
                        area="test", recommendation="do it", target_system="ghl", urgency="high"
                    )
                ],
            ),
        )
        html = render_plan_html(result)
        apps_pos = html.find("Business Applications")
        video_pos = html.find("What This Video Covers")
        if apps_pos > -1 and video_pos > -1:
            assert apps_pos < video_pos


class TestRemovedSections:
    def test_should_not_have_swipe_phrases_section(self):
        html = render_plan_html(_make_result())
        assert "Swipe Phrases" not in html
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_html_renderer.py -v`
Expected: FAIL — no nav bar, no comparison section, no social media section, wrong order, swipe phrases still present

**Step 3: Update `static/plan_view.html` template**

Replace the template body with the new section order. Key changes:

1. Add sticky nav bar at top with back link + section jump links
2. Move sections to new order: header → recommended action → comparison → impact → summary → applications → levels → tasks → social media → video breakdown (collapsed) → insights → our take (collapsed) → fact checks → cost
3. Remove swipe phrases section
4. Remove DDB content angle standalone section (folded into social media or tasks)
5. Add `id` attributes for anchor linking: `section-comparison`, `section-applications`, `section-tasks`, `section-social`, `section-video`, `section-insights`
6. Add new placeholders: `{{comparison_html}}`, `{{social_media_html}}`

**Step 4: Update `src/utils/html_renderer.py`**

Add new builder functions:

```python
def _build_comparison_html(result: PipelineResult) -> str:
    """Build comparison-to-current-state section from similarity data."""
    if not result.similarity:
        return ""
    comparisons = []
    for sp in result.similarity.similar_plans:
        for c in sp.comparisons:
            comparisons.append((sp.title, c))
    if not comparisons:
        return ""

    verdict_colors = {"better": "#22c55e", "worse": "#ef4444", "same": "#94a3b8", "different_angle": "#60a5fa"}
    html = ""
    for plan_title, c in comparisons:
        color = verdict_colors.get(c.verdict, "#94a3b8")
        html += (
            f'<div class="card" style="border-left: 3px solid {color};">'
            f'<strong>{html_esc(c.area)}</strong> '
            f'<span class="badge" style="background:{color};">{html_esc(c.verdict.upper())}</span>'
            f'<p><em>Current:</em> {html_esc(c.current_content)}</p>'
            f'<p><em>New:</em> {html_esc(c.new_content)}</p>'
            f'<p style="color:#94a3b8;font-size:0.85rem;">{html_esc(c.explanation)}</p>'
            f'</div>'
        )
    return html


def _build_social_media_html(analysis) -> str:
    """Build social media play section from content_response."""
    cr = analysis.content_response
    if not cr.react_angle and not cr.repurpose_ideas and not cr.corrections:
        return ""

    html = ""
    if cr.react_angle:
        html += f'<div class="card"><strong>React angle:</strong> {html_esc(cr.react_angle)}</div>'
    if cr.corrections:
        items = "".join(f"<li>{html_esc(c)}</li>" for c in cr.corrections)
        html += f'<div class="card"><strong>Corrections:</strong><ul>{items}</ul></div>'
    if cr.repurpose_ideas:
        items = "".join(f"<li>{html_esc(r)}</li>" for r in cr.repurpose_ideas)
        html += f'<div class="card"><strong>Repurpose ideas:</strong><ul>{items}</ul></div>'
    if cr.engagement_hook:
        html += f'<div class="card"><strong>Engagement hook:</strong> {html_esc(cr.engagement_hook)}</div>'
    return html
```

Update `render_plan_html` replacements dict to include the new placeholders.

Update `_build_tasks_json` to include `change_type`.

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_html_renderer.py -v`
Expected: All PASS

**Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS (some existing tests may need minor updates if they reference old template placeholders)

**Step 7: Commit**

```bash
git add static/plan_view.html src/utils/html_renderer.py tests/test_html_renderer.py
git commit -m "feat: restructure HTML plan view with nav, comparison, social media sections"
```

---

### Task 6: Update Telegram similarity message

**Files:**
- Modify: `src/services/telegram_similarity.py`

**Step 1: Write the failing test**

```python
# tests/test_telegram_similarity.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import (
    AnalysisResult, SimilarityResult, SimilarPlan, ContentComparison, CostBreakdown,
)


@pytest.mark.asyncio
async def test_should_include_comparison_details_in_message():
    """Telegram similarity message should show comparison verdicts."""
    analysis = AnalysisResult(
        category="sales", summary="test", key_insights=["i"], relevance_score=0.9, theme="objections",
    )
    similarity = SimilarityResult(
        similar_plans=[SimilarPlan(
            title="Old Plan", reel_id="OLD1", score=60, overlap_areas=["sales"],
            comparisons=[
                ContentComparison(area="objection handling", current_content="old", new_content="new", verdict="better", explanation="clearer steps"),
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
    assert "better" in message_text.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_telegram_similarity.py -v`
Expected: FAIL — message doesn't include comparison details

**Step 3: Update `send_similarity_notification` in `telegram_similarity.py`**

After building `similar_lines`, add comparison details:

```python
for sp in similarity.similar_plans:
    overlap = ", ".join(sp.overlap_areas) if sp.overlap_areas else "general"
    similar_lines.append(
        f"  _{_esc(sp.title)}_ ({sp.score}% match)"
    )
    if sp.comparisons:
        for c in sp.comparisons:
            emoji = {"better": "+", "worse": "-", "same": "=", "different_angle": "~"}.get(c.verdict, "?")
            similar_lines.append(
                f"    [{emoji}] {_esc(c.area)}: {_esc(c.explanation)}"
            )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_telegram_similarity.py -v`
Expected: All PASS

**Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/services/telegram_similarity.py tests/test_telegram_similarity.py
git commit -m "feat: enrich Telegram similarity message with comparison details"
```

---

### Task 7: Update plan_writer.py and fix callers

**Files:**
- Modify: `src/utils/plan_writer.py` — update `_format_plan_md` to include social media section, remove swipe phrases, add change_type to tasks
- Modify: `src/routers/reel.py` — pass similarity to `generate_plan`

**Step 1: Update `_format_plan_md` in `plan_writer.py`**

Remove the swipe phrases section. Add social media section after tasks. Add change_type display to task lines.

Replace the swipe phrases block:
```python
# REMOVE this block:
if analysis.swipe_phrases:
    lines.extend(["", "## Swipe Phrases", ""])
    for phrase in analysis.swipe_phrases:
        lines.append(f"- {phrase}")
```

Add social media section:
```python
# After tasks section
cr = analysis.content_response
if cr.react_angle or cr.repurpose_ideas or cr.corrections:
    lines.extend(["", "## Social Media Play", ""])
    if cr.react_angle:
        lines.append(f"**React angle:** {cr.react_angle}")
    if cr.corrections:
        lines.append("**Corrections:**")
        for c in cr.corrections:
            lines.append(f"- {c}")
    if cr.repurpose_ideas:
        lines.append("**Repurpose ideas:**")
        for r in cr.repurpose_ideas:
            lines.append(f"- {r}")
    if cr.engagement_hook:
        lines.append(f"**Engagement hook:** {cr.engagement_hook}")
```

Add change_type to task display:
```python
# In the task rendering loop, after the priority line:
if task.change_type:
    lines.append(f"**Change type:** {task.change_type}")
```

**Step 2: Check `src/routers/reel.py` for `generate_plan` call**

Read the file, find where `generate_plan` is called, add `similarity=similarity_result` parameter.

**Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/utils/plan_writer.py src/routers/reel.py
git commit -m "feat: update plan.md format with social media section, change_type, remove swipe phrases"
```

---

### Task 8: Final integration test + cleanup

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 2: Fix any import issues from re-exports**

The old `_md_to_html` and `_html_esc` re-exports in `plan_writer.py` (line 14) reference the split modules. Verify `test_plan_writer_json.py` still works since it imports `_md_to_html` and `_html_esc` from `plan_writer`.

**Step 3: Spot-check the HTML output**

```python
# Quick manual check
python -c "
from src.models import *
from src.utils.html_renderer import render_plan_html
r = PipelineResult(
    reel_id='TEST', status=PlanStatus.REVIEW,
    metadata=ReelMetadata(url='https://instagram.com/reel/X', shortcode='X'),
    transcript=TranscriptResult(text='t'),
    analysis=AnalysisResult(
        category='sales', summary='s', key_insights=['i'], relevance_score=0.9,
        content_response=ContentResponse(react_angle='React here', repurpose_ideas=['Carousel']),
    ),
    plan=ImplementationPlan(title='Test', summary='s', tasks=[PlanTask(title='T', description='D', level=1, tools=['kb'], change_type='addition')]),
)
html = render_plan_html(r)
assert 'Social Media Play' in html
assert 'addition' in html.lower() or 'ADDITION' in html
print('HTML rendering OK')
"
```

**Step 4: Commit any fixes**

```bash
git add -u
git commit -m "fix: integration fixes for similarity + plan view redesign"
```
