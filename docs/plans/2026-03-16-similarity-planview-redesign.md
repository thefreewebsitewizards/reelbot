# Similarity + Plan View Redesign

## Problem

1. Similarity check shows arbitrary percentages and titles but never says *what* is actually similar or whether the new reel's take is better/worse than what we already have
2. HTML plan view has wrong section order — business applications and implementation levels are buried below video breakdown
3. No "comparison to current state" — user can't tell if a task is an addition, replacement, or ignorable
4. Missing social media/content response section (was good in earlier plans, got dropped)
5. HTML page is a dead end — no way to navigate back to plans list or jump between sections
6. Bloat — empty "Swipe Phrases: None extracted", redundant summary/impact overlap

## Design

### 1. Enriched Similarity Check

**File:** `src/services/planner.py` (`check_plan_similarity`)

Current prompt compares theme/category/summary against plan titles. Change to:

- For top 3 matches (score > 30), load their `plan.md` content from disk
- New prompt asks LLM to compare specific content and produce per-area verdicts
- Cost: ~1-2k extra tokens per similarity check (pennies)

New model (`src/models.py`):
```python
class ContentComparison(BaseModel):
    area: str = ""             # "sales objection handling"
    current_content: str = ""  # what existing plan says
    new_content: str = ""      # what this reel suggests
    verdict: str = ""          # better | worse | same | different_angle
    explanation: str = ""      # 1-sentence why
```

Add `comparisons: list[ContentComparison] = []` to `SimilarPlan`.

### 2. Planner Gets Comparison Context

**File:** `src/prompts/generate_plan.py`

Feed enriched similarity into the plan prompt. Each task gets a `change_type` field:
- `addition` — we don't have this yet
- `replacement` — this is better than what we have
- `reinforcement` — aligns with current approach
- `ignore` — we already have something better

Add `change_type: str = ""` to `PlanTask` model.

### 3. Social Media / Content Response Section

**File:** `src/prompts/analyze_reel.py` + `src/models.py`

Add to analysis prompt output:
```python
class ContentResponse(BaseModel):
    react_angle: str = ""       # How to respond/react to build authority
    corrections: list[str] = [] # Things the video got wrong we can correct publicly
    repurpose_ideas: list[str] = [] # How to take this content for our channels
    engagement_hook: str = ""   # Suggested comment or reply to the original post
```

Add `content_response: ContentResponse` to `AnalysisResult`.

This gets its own section in the HTML view titled "Social Media Play".

### 4. HTML Plan View Restructure

**File:** `static/plan_view.html` + `src/utils/html_renderer.py`

#### New section order:
1. **Nav bar** — back to plans list + section jump links
2. **Header** — title, theme, meta (relevance, category, creator, duration, route)
3. **Recommended Action** — green callout
4. **Comparison to Current State** — NEW section showing similarity diffs with verdicts (addition/replacement/reinforcement/ignore), actual content quoted. Only shows if similarity data exists.
5. **Business Impact** — blue callout, 1 sentence
6. **Summary** — plan summary (keep concise)
7. **Business Applications** — MOVED UP, color-coded urgency cards
8. **Implementation Levels** — MOVED UP (L1/L2/L3 one-liners, right before tasks)
9. **Tasks / Control Panel** — checkboxes, approve/skip/feedback (unchanged)
10. **Social Media Play** — NEW section with react angle, corrections, repurpose ideas
11. **Video Breakdown** — collapsed by default
12. **Key Insights** — bullet list
13. **Our Take** — collapsed
14. **Fact Checks** — only renders if non-empty
15. **Cost Breakdown**

#### Removed:
- "Swipe Phrases" section (rarely populated, not actionable)
- "DDB Content Angle" standalone section (folded into Social Media Play or L3 task)

#### Navigation additions:
- Sticky top bar: `< Back to Plans` link + plan title
- Section jump links (anchors) for: Comparison, Applications, Tasks, Social Media, Video, Insights
- Each section gets an `id` attribute for anchor linking

### 5. L3 Task Splitting Preserved

L3 can have 1-3 tasks. User already liked being able to approve one L3 task and not the other via checkbox selection. No change needed.

### 6. Telegram Similarity Message

**File:** `src/services/telegram_similarity.py`

Update the message to include actual comparison content:
```
Similar content detected

Theme: [theme]

Compared to: [existing plan title]
- Sales script objection handling: your current version covers X, this reel adds Y (verdict: replacement)
- Lead nurture: not in current plans (verdict: addition)

[Link to plan view for full comparison]

[Generate Anyway] [Skip]
```

## Files Changed

| File | Change |
|------|--------|
| `src/models.py` | Add ContentComparison, ContentResponse models; add fields to SimilarPlan, PlanTask, AnalysisResult |
| `src/services/planner.py` | Enrich similarity prompt to load plan.md content and produce comparisons |
| `src/prompts/generate_plan.py` | Feed comparison context, add change_type to task output schema |
| `src/prompts/analyze_reel.py` | Add content_response to analysis output schema |
| `src/services/analyzer.py` | Parse content_response from LLM output |
| `src/utils/html_renderer.py` | Build comparison section, social media section, nav bar, reorder sections |
| `static/plan_view.html` | New section order, nav bar, anchor IDs, remove bloat sections |
| `src/services/telegram_similarity.py` | Richer similarity message with comparison details |
| `src/utils/plan_writer.py` | Pass new data through to template |
| `tests/` | Update tests for new model fields |

## Non-Goals

- No changes to execution engine (tool_handlers, executor)
- No changes to plan approval flow (approve/skip/feedback endpoints)
- No changes to cost tracking
- No changes to download/transcribe pipeline
