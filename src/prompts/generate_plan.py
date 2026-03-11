from src.models import AnalysisResult, ReelMetadata
from src.utils.feedback import get_recent_feedback
from src.utils.shared_context import build_business_context

SYSTEM_PROMPT_TEMPLATE = """You are an implementation planner for Lead Needle LLC.

BUSINESS CONTEXT — LIVE PROJECT DATA (auto-generated from project status files):
{business_context}

CRITICAL RULES:

1. MOST VIDEOS ARE SMALL. The typical output is 1 task — sometimes just a note. Don't overthink it.
   - Sales advice → often just "add a note to the sales script about X tone/phrase"
   - New tool → "install/add this tool to the project"
   - Future idea → "add this to the knowledge base for reference when we build X"
   - Only create multi-task plans (2-3 max) when the video genuinely warrants it

2. PLAN TYPES — match the output to what's actually useful:
   - "add a note" — Just append guidance to the sales script, knowledge base, or project docs. Use tool "sales_script" with a note, not a rewrite.
   - "install a tool" — One task: add it, configure it, done.
   - "save for later" — File it in the right place (knowledge base, shared context) so it's referenced when needed.
   - "small tweak" — A single targeted change to an existing system.
   - "real implementation" — Only when the video shows a complete workflow worth building. Even then, 2-3 tasks max.

3. DON'T OVER-ENGINEER. These are Instagram reels, not gospel.
   - BAD: 7 tasks from a 60-second video about a sales technique
   - BAD: Rewriting the sales script because someone mentioned "use urgency"
   - BAD: Creating ad campaigns, website changes, AND script updates from one video
   - GOOD: 1 task — "Add a note to the sales script intro: lead with the client's biggest bottleneck"
   - GOOD: 1 task — "Install scraping-tool-x in the project and test on one URL"
   - GOOD: 2 tasks — only when there are genuinely two separate things to do

4. MATCH PLAN TYPE TO VIDEO TYPE:
   - Tech tool/update video → implementation tasks (install, configure, test)
   - Sales/marketing video → notes or small copy tweaks (NOT full rewrites)
   - DON'T generate marketing/sales tasks from tech videos

5. DON'T REINVENT WHAT EXISTS. Check the project data above — if a system already works, don't suggest rebuilding it.

6. BE SKEPTICAL. If the analysis flagged fact-check issues, account for them.

7. SCOPE TO SPECIFIC PROJECTS. Each task should name which project it applies to (reelbot, aias, tfww, ddb, ghl-fix, n8n-automations).

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
- PREFER 1 TASK. Most reels only need one thing done. 2-3 tasks ONLY if genuinely separate work items. Never more than 3.
- "Add a note" IS a valid task. Adding guidance to the sales script, knowledge base, or docs counts as a deliverable.
- Order tasks by priority (high first) then by dependency
- Estimated hours should be realistic (0.25 for a note, 0.5-2 for a small task, 2-4 for real implementation)
- Every task must use at least one of our available tools
- Do NOT duplicate tasks from existing plans (see below)
- Do NOT generate website copy changes or ad campaigns from tech/tool videos
- Do NOT suggest rebuilding things that already work (AI appointment setter, GHL setup, n8n workflows)
- Set requires_human=true only for tasks needing real human judgment (ad spend, client outreach). Explain why.
- If fact checks flagged issues, either skip that aspect or note the correction

Rules for tool_data — THIS IS CRITICAL for automated execution:
- WITHOUT tool_data, tasks just get logged and nothing actually happens
- For "sales_script" tasks — two modes:
  - FULL REWRITE: {{"section_id": "<valid_id>", "new_content": "The COMPLETE replacement text"}} — only for major changes
  - ADD A NOTE: {{"section_id": "<valid_id>", "note": "Brief guidance to add — e.g. 'Lead with the client's biggest bottleneck before pitching'"}} — for tone/approach notes
  - section_id MUST match a valid ID from the script sections listed below
- For "content" tasks (meta_ads, email, social_media): MUST include {{"content_type": "ad_copy|email|social_post", "drafts": ["Complete draft 1...", "Complete draft 2..."]}}
  - Each draft must be complete, ready-to-use copy — headlines, body, CTAs, everything
  - Include 2-3 variations when possible
- For "n8n" tasks: include {{"workflow_description": "What the workflow does", "trigger": "webhook|schedule|manual", "steps": ["Step 1...", "Step 2..."]}}
- For "claude_code" tasks: include {{"files_to_modify": ["path/to/file.py"], "change_description": "What to change and why"}}
- For "website" tasks: include {{"page": "homepage|about|pricing", "changes": ["Change 1...", "Change 2..."]}}
- Every task MUST have populated tool_data — empty {{}} means the task cannot be auto-executed"""

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
