"""Prompt for generating a personal brand content plan for Dylan Does Business."""

from pathlib import Path
from src.models import AnalysisResult, ReelMetadata

BRAND_DIR = Path("/home/gamin/projects/openclaw/claude-code-projects/ddb/brand")

SYSTEM_PROMPT = """You are a content strategist for Dylan Does Business (@dylandoesbusiness).

Dylan's brand:
- Core: "I see how things connect and I build systems around it."
- Sits at the intersection of philosophy, AI, and entrepreneurship
- Content loop: Philosophy → Insight → System → Proof
- NOT a guru, NOT a tech bro, NOT a course seller
- Voice: direct, curious, grounded, conversational
- No hype language, no fake urgency
- Short sentences. Let ideas breathe.

Content pillars:
- How I Think (30%): philosophy, psychology, frameworks
- How I Build (25%): AI, automation, systems, tools
- How I Execute (25%): business, revenue, real plays
- How You Can Too (20%): tutorials, breakdowns, walkthroughs

Platforms: Instagram Reels, TikTok, YouTube Shorts

This is DIFFERENT from Lead Needle LLC business content. This is Dylan's personal brand:
- More philosophical, more behind-the-scenes
- Shows the thinking process, not just the result
- First person, talking to peers not clients
- Can reference the business as proof/examples but doesn't sell services

Respond with valid JSON only."""

USER_TEMPLATE = """Create a personal brand content plan for Dylan Does Business based on this reel analysis.

**Original Creator:** {creator}
**Category:** {category}
**Theme:** {theme}
**Summary:** {summary}

**Transcript excerpt:**
{transcript}

{brand_context}

Return JSON:
{{
  "title": "DDB Content Plan: [short descriptor]",
  "summary": "What Dylan should create and which content pillar it fits (Think/Build/Execute/You Can Too)",
  "tasks": [
    {{
      "title": "Task title (imperative verb)",
      "description": "Detailed instructions. WRITE THE ACTUAL SCRIPT in Dylan's voice — direct, curious, no hype. Include the philosophy-to-system connection.",
      "priority": "high|medium|low",
      "estimated_hours": 1.0,
      "deliverables": ["Draft script", "Hook variations", "Caption"],
      "dependencies": [],
      "tools": ["content_creation"],
      "requires_human": true,
      "human_reason": "Needs filming / recording"
    }}
  ]
}}

Required tasks (generate all that apply):
1. **Adapted Script for Dylan's Voice** — Rewrite for Dylan's brand:
   - Hook: question-based or pattern-interrupt (NOT hype)
   - Body: show the thinking → insight → system connection
   - CTA: one action (follow, join Discord, or watch full video)
   - Include which content pillar this fits (Think/Build/Execute/You Can Too)
2. **Visual/Format Plan** — How Dylan would film this:
   - Talking head with screen recording? Pure talking head? Carousel?
   - What to show on screen (if anything)
3. **Caption + Hashtags** — In Dylan's voice (direct, no emoji overload)

Rules:
- WRITE THE ACTUAL SCRIPT, not just "rewrite for Dylan's voice"
- Maximum 4 tasks
- Dylan's voice is direct and curious — "Here's what I noticed..." not "This INSANE hack..."
- Reference the content loop: where does this idea sit in Philosophy → Insight → System → Proof?
- Every task that requires filming must have requires_human=true"""


def _load_brand_context() -> str:
    """Load brand guide context from the DDB brand directory."""
    brand_guide = BRAND_DIR / "BRAND-GUIDE.md"
    if not brand_guide.exists():
        return ""

    content = brand_guide.read_text()
    # Extract just the voice & tone section to keep context small
    voice_section = ""
    in_section = False
    for line in content.split("\n"):
        if "## Voice & Tone" in line:
            in_section = True
        elif in_section and line.startswith("## "):
            break
        if in_section:
            voice_section += line + "\n"

    if voice_section:
        return f"**Dylan's voice reference:**\n{voice_section.strip()}"
    return ""


def build_personal_brand_prompt(
    analysis: AnalysisResult, metadata: ReelMetadata, transcript: str,
) -> tuple[str, str]:
    brand_context = _load_brand_context()
    user_prompt = USER_TEMPLATE.format(
        creator=metadata.creator or "Unknown",
        category=analysis.category,
        theme=analysis.theme or "Not specified",
        summary=analysis.summary,
        transcript=transcript[:2000],
        brand_context=brand_context,
    )
    return SYSTEM_PROMPT, user_prompt
