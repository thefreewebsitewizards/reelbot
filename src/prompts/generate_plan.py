from src.models import AnalysisResult, ReelMetadata
from src.utils.feedback import get_recent_feedback
from src.utils.shared_context import build_business_context

SYSTEM_PROMPT_TEMPLATE = """You are an implementation planner for Lead Needle LLC.

BUSINESS CONTEXT — LIVE PROJECT DATA (auto-generated from project status files):
{business_context}

CRITICAL RULES:

1. KEEP PLANS SHORT AND PRACTICAL. 2-4 tasks max. Prefer 1-2 for simple things. Focus on "set it up and use it."
   - BAD: 7 tasks including website rewrites, ad campaigns, and sales script changes from a tech demo video
   - BAD: 3 tasks with deep analysis for "install this Claude Code skill" — that's 1 task
   - GOOD: 1 task — "Add the skill to Claude Code" (when that's literally all there is to do)
   - GOOD: 2 tasks — "Install/configure the tool" + "Test it on a real workflow"

2. MATCH PLAN TYPE TO VIDEO TYPE:
   - Tech tool/update video → implementation tasks (install, configure, test)
   - Sales/marketing video → copy/strategy tasks (only then include ad copy, scripts)
   - DON'T generate marketing/sales tasks from tech videos

3. DON'T REINVENT WHAT EXISTS. Check the project data above — if a system already works, don't suggest rebuilding it.
   Only suggest changes to existing systems if the video shows something specifically better.

4. BE SKEPTICAL. If the analysis flagged fact-check issues, account for them. Don't build a plan around an unverified claim.

5. NO PADDING. Don't add tasks just to fill the plan. If there's only one thing to do, make it one task.

6. SCOPE TO SPECIFIC PROJECTS. Each task should name which project it applies to (reelbot, aias, tfww, ddb, ghl-fix, n8n-automations). Use the routing_target from analysis as a guide.

Available tools: n8n, GHL, Claude Code, Meta Ads, Website (thefreewebsitewizards.com), Telegram bot, sales_script API

7. WEB DESIGN TASKS: When generating tasks that involve website changes, web design, or UI/UX:
   - Reference the web design knowledge base at tfww/web-design/ (design-system.md, patterns.md, principles.md)
   - Use our established design tokens (colors, typography, spacing) — don't invent new ones
   - Include specific CSS/Tailwind classes, color codes, and measurements in task descriptions
   - New design insights from the reel should be applied using our existing Tailwind v4 + static HTML stack
   - Quality bar: sites must load sub-3s on 3G, use WebP images, be fully responsive

Respond with valid JSON only."""


def _get_system_prompt() -> str:
    """Build system prompt with live business context."""
    context = build_business_context()
    if not context:
        context = "(No shared context files found — check ~/projects/openclaw/.shared-context/)"
    return SYSTEM_PROMPT_TEMPLATE.format(business_context=context)

USER_TEMPLATE = """Convert this reel analysis into an implementation plan.

**Source Reel:** {url} (by {creator})
**Category:** {category}
**Theme:** {theme}
**Summary:** {summary}
**Business Impact:** {business_impact}
**Relevance:** {relevance_score}

**Key Insights:**
{insights_formatted}

**Business Applications:**
{applications_formatted}

**Swipe Phrases (ready-to-use copy from the reel):**
{phrases_formatted}

**Fact Checks:**
{fact_checks_formatted}

Return JSON:
{{
  "title": "Concise plan title",
  "summary": "What this plan achieves in 2-3 sentences",
  "tasks": [
    {{
      "title": "Task title (imperative verb)",
      "description": "Step by step what to do. For copy tasks, include the EXACT text to use — headlines, email subject lines, CTAs, scripts. Don't just describe the approach, write the actual words.",
      "priority": "high|medium|low",
      "estimated_hours": 1.0,
      "deliverables": ["Concrete output — for copy deliverables, include the draft text"],
      "dependencies": ["Other task title if needed — state what output is used"],
      "tools": ["n8n", "ghl", "claude_code", "meta_ads", "website"],
      "requires_human": false,
      "human_reason": "",
      "tool_data": {{}}
    }}
  ]
}}

Rules:
- MAXIMUM 4 tasks. Prefer 2-3. Only include what's actually worth doing.
- Order tasks by priority (high first) then by dependency
- Each task must have at least one concrete deliverable
- Estimated hours should be realistic (0.5 - 4 hours per task)
- Every task must use at least one of our available tools
- Do NOT duplicate tasks from existing plans (see below)
- Do NOT generate website copy changes or ad campaigns from tech/tool videos
- Do NOT suggest rebuilding things that already work (AI appointment setter, GHL setup, n8n workflows)
- Set requires_human=true only for tasks needing real human judgment (ad spend, client outreach). Explain why.
- If fact checks flagged issues, either skip that aspect or note the correction

Rules for tool_data (structured data for automated execution):
- For "sales_script" tasks: include {{"section_id": "intro", "new_content": "The exact replacement text..."}}
  - section_id MUST match a valid ID from the script sections listed below
  - new_content must be the COMPLETE replacement text, ready to apply as-is
- For "content" tasks (meta_ads, email, social posts): include {{"content_type": "ad_copy|email|social_post", "drafts": ["Draft 1 text...", "Draft 2 text..."]}}
- For other tools: leave tool_data as empty {{}}
- tool_data enables automated execution — without it, tasks just get logged"""

EXISTING_PLANS_SECTION = """

**Existing plans (avoid duplicating these tasks):**
{existing_plans}"""

CAPABILITIES_SECTION = """

**Existing Capabilities (DO NOT suggest rebuilding these — reference them for new use cases instead):**
{capabilities}"""

FEEDBACK_SECTION = """

## Past Feedback (learn from these):
{feedback_lines}

Use this feedback to improve the quality of your plan. Repeat what worked, avoid what didn't."""


def get_feedback_context() -> str:
    """Format recent feedback entries for inclusion in prompts."""
    entries = get_recent_feedback(5)
    if not entries:
        return ""

    rating_labels = {"good": "GOOD", "bad": "BAD", "partial": "PARTIAL"}
    lines = []
    for entry in entries:
        label = rating_labels.get(entry["rating"], entry["rating"].upper())
        title = entry["plan_title"] or entry["reel_id"]
        comment_part = f': "{entry["comment"]}"' if entry["comment"] else ""
        lines.append(f'- Plan "{title}" was rated {label}{comment_part}')

    return "\n".join(lines)


SCRIPT_CONTEXT_SECTION = """

**Current Sales Script (modify sections via API):**
{script_content}

**Valid section IDs for PUT /api/script/sections/{{id}}:**
{section_ids}

When tasks involve script changes:
- Reference the EXACT section ID (e.g., "price_objection")
- Show the current text AND the replacement text
- Use tool "sales_script" with the section ID for script edit tasks"""


def build_plan_prompt(
    analysis: AnalysisResult, metadata: ReelMetadata,
    existing_plans_summary: str = "",
    script_context: str = "",
    script_section_ids: str = "",
    capabilities_context: str = "",
    user_context: str = "",
) -> tuple[str, str]:
    insights_formatted = "\n".join(f"- {i}" for i in analysis.key_insights)
    phrases_formatted = "\n".join(f"- {p}" for p in analysis.swipe_phrases) if analysis.swipe_phrases else "- None extracted"

    applications_formatted = "- None identified"
    if analysis.business_applications:
        applications_formatted = "\n".join(
            f"- [{ba.urgency.upper()}] {ba.area}: {ba.recommendation} (target: {ba.target_system})"
            for ba in analysis.business_applications
        )

    fact_checks_formatted = "- No claims flagged"
    if analysis.fact_checks:
        fact_checks_formatted = "\n".join(
            f"- [{fc.verdict}] \"{fc.claim}\" — {fc.explanation}"
            + (f" Better: {fc.better_alternative}" if fc.better_alternative else "")
            for fc in analysis.fact_checks
        )

    user_prompt = USER_TEMPLATE.format(
        url=metadata.url,
        creator=metadata.creator or "Unknown",
        category=analysis.category,
        theme=analysis.theme or "Not specified",
        summary=analysis.summary,
        business_impact=analysis.business_impact or "Not assessed",
        relevance_score=analysis.relevance_score,
        insights_formatted=insights_formatted,
        applications_formatted=applications_formatted,
        phrases_formatted=phrases_formatted,
        fact_checks_formatted=fact_checks_formatted,
    )

    if capabilities_context:
        user_prompt += CAPABILITIES_SECTION.format(
            capabilities=capabilities_context,
        )

    if existing_plans_summary:
        user_prompt += EXISTING_PLANS_SECTION.format(
            existing_plans=existing_plans_summary,
        )

    if script_context:
        user_prompt += SCRIPT_CONTEXT_SECTION.format(
            script_content=script_context,
            section_ids=script_section_ids,
        )

    if user_context:
        user_prompt += f"\n\n**User notes (prioritize this direction):**\n{user_context}"

    feedback_context = get_feedback_context()
    if feedback_context:
        user_prompt += FEEDBACK_SECTION.format(feedback_lines=feedback_context)

    return _get_system_prompt(), user_prompt
