"""Prompt for generating a content repurposing plan from a reel analysis."""

from src.models import AnalysisResult, ReelMetadata

SYSTEM_PROMPT = """You are a content strategist for Lead Needle LLC / The Free Website Wizards.

You analyze successful Instagram Reels and create a content repurposing plan so we can remake similar content for our own brand.

Our brand angles (pick the most relevant for each piece):
- Business & AI automation for local service companies
- Sales psychology and objection handling
- Philosophy of entrepreneurship and systems thinking
- Developer/builder behind-the-scenes
- Lead generation and appointment setting

Our platforms: Instagram Reels, TikTok, YouTube Shorts

Respond with valid JSON only. No markdown, no explanation outside the JSON."""

USER_TEMPLATE = """Analyze this reel and create a content repurposing plan for our brand.

**Original Creator:** {creator}
**Category:** {category}
**Theme:** {theme}
**Summary:** {summary}

**Transcript:**
{transcript}

Return JSON:
{{
  "title": "Repurposing Plan: [short descriptor]",
  "summary": "What content we'll create and why it works for our brand",
  "tasks": [
    {{
      "title": "Task title (imperative verb)",
      "description": "Detailed instructions including the adapted script, shot list, or content brief. WRITE THE ACTUAL SCRIPT — don't just describe it.",
      "priority": "high|medium|low",
      "estimated_hours": 1.0,
      "deliverables": ["Concrete output — include draft scripts, captions, hashtag sets"],
      "dependencies": [],
      "tools": ["claude_code", "meta_ads"],
      "requires_human": true,
      "human_reason": "Needs filming / recording / content approval"
    }}
  ]
}}

Required tasks (generate all that apply):
1. **Adapted Script** — Rewrite the reel's hook, body, and CTA for our brand. Include:
   - The hook (first 3 seconds — what stops the scroll)
   - Body structure (how info is delivered — list, story, demonstration)
   - CTA (what the viewer should do)
   - Psychological trigger used (curiosity gap, authority, social proof, fear of missing out, etc.)
2. **Shot List / Visual Plan** — Describe what each segment looks like on camera. Face-to-cam? Screen recording? B-roll?
3. **Platform Variations** — Adjust format for each platform:
   - IG Reels: vertical, 30-90s, trending audio optional
   - TikTok: vertical, hook in first 1s, text overlays
   - YouTube Shorts: vertical, 60s max, can be more educational
4. **Captions & Hashtags** — Write the post caption and hashtag set for each platform
5. **Scheduling Note** — Suggest best posting time and any tie-in to trends or events

Rules:
- WRITE THE ACTUAL ADAPTED SCRIPT, not just "rewrite the script for our brand"
- Maximum 5 tasks
- Every task that requires filming or recording must have requires_human=true
- Include the original reel's psychological trigger and how we're adapting it
- Our brand voice: confident, helpful, slightly irreverent. "We handle it for you" energy."""


def build_repurposing_prompt(
    analysis: AnalysisResult, metadata: ReelMetadata, transcript: str,
) -> tuple[str, str]:
    user_prompt = USER_TEMPLATE.format(
        creator=metadata.creator or "Unknown",
        category=analysis.category,
        theme=analysis.theme or "Not specified",
        summary=analysis.summary,
        transcript=transcript,
    )
    return SYSTEM_PROMPT, user_prompt
