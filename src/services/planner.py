import json
from loguru import logger

from src.config import settings
from src.models import (
    AnalysisResult, ReelMetadata, ImplementationPlan, PlanTask,
    SimilarityResult, SimilarPlan,
)
from src.prompts.generate_plan import build_plan_prompt
from src.utils.plan_manager import get_past_plan_summaries
from src.utils.capability_manager import get_capabilities_context
from src.services.llm import chat, ChatResult, get_model_for_step


def check_plan_similarity(analysis: AnalysisResult) -> tuple[SimilarityResult, ChatResult | None]:
    """Check if new analysis overlaps with existing plans."""
    existing_plans = get_past_plan_summaries(limit=15)
    if not existing_plans:
        return SimilarityResult(), None

    system = (
        "You compare a new content analysis against existing plans to detect overlap. "
        "Respond with valid JSON only."
    )
    user_content = f"""Compare this new analysis against our existing plans and score similarity.

**New analysis:**
- Theme: {analysis.theme}
- Category: {analysis.category}
- Summary: {analysis.summary}
- Key insights: {', '.join(analysis.key_insights[:5])}

**Existing plans:**
{existing_plans}

Return JSON:
{{
  "similar_plans": [
    {{
      "title": "Title of the existing plan",
      "reel_id": "ID from the brackets",
      "score": 0-100,
      "overlap_areas": ["area1", "area2"]
    }}
  ],
  "recommendation": "generate|skip|merge"
}}

Rules:
- Only include plans with score > 30
- score 70+ means very similar (consider skipping)
- score 40-69 means some overlap (generate but note it)
- score <40 means different enough (generate freely)
- recommendation: "skip" if max score > 85, "merge" if 70-85, "generate" otherwise
- Maximum 3 similar plans in the list"""

    try:
        chat_result = chat(system=system, user_content=user_content, max_tokens=500, model_override=get_model_for_step("similarity"))
        raw = chat_result.text
        json_text = raw
        if "```json" in raw:
            json_text = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            json_text = raw.split("```")[1].split("```")[0]

        data = json.loads(json_text)
        similar = [
            SimilarPlan(
                title=p.get("title", ""),
                reel_id=p.get("reel_id", ""),
                score=int(p.get("score", 0)),
                overlap_areas=p.get("overlap_areas", []),
            )
            for p in data.get("similar_plans", [])
        ]
        max_score = max((p.score for p in similar), default=0)
        return SimilarityResult(
            similar_plans=similar,
            recommendation=data.get("recommendation", "generate"),
            max_score=max_score,
        ), chat_result
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.warning(f"Similarity check failed to parse: {e}")
        return SimilarityResult(), chat_result


def generate_plan(analysis: AnalysisResult, metadata: ReelMetadata) -> tuple[ImplementationPlan, ChatResult]:
    """Generate an implementation plan from the analysis using an LLM."""

    existing_plans = get_past_plan_summaries(limit=10)
    capabilities = get_capabilities_context()

    script_context = ""
    script_section_ids = ""
    if analysis.category == "sales":
        from src.utils.script_manager import get_script_content, get_script_summary
        script_context = get_script_content()
        if script_context:
            script_section_ids = get_script_summary()
            logger.info("Injecting sales script context into plan prompt")

    system_prompt, user_prompt = build_plan_prompt(
        analysis, metadata, existing_plans, script_context, script_section_ids,
        capabilities_context=capabilities,
    )

    logger.info("Generating implementation plan...")
    chat_result = chat(system=system_prompt, user_content=user_prompt, max_tokens=3000, model_override=get_model_for_step("plan"))
    raw = chat_result.text

    try:
        json_text = raw
        if "```json" in raw:
            json_text = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            json_text = raw.split("```")[1].split("```")[0]

        data = json.loads(json_text)

        tasks = []
        for t in data.get("tasks", []):
            tasks.append(PlanTask(
                title=t.get("title", ""),
                description=t.get("description", ""),
                priority=t.get("priority", "medium"),
                estimated_hours=float(t.get("estimated_hours", 1.0)),
                deliverables=t.get("deliverables", []),
                dependencies=t.get("dependencies", []),
                tools=t.get("tools", []),
                requires_human=bool(t.get("requires_human", False)),
                human_reason=t.get("human_reason", ""),
            ))

        plan = ImplementationPlan(
            title=data.get("title", f"Plan: {metadata.shortcode}"),
            summary=data.get("summary", ""),
            tasks=tasks,
            total_estimated_hours=sum(t.estimated_hours for t in tasks),
        )
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Failed to parse plan JSON, creating single-task plan")
        plan = ImplementationPlan(
            title=f"Plan: {metadata.shortcode}",
            summary=raw[:500],
            tasks=[PlanTask(
                title="Review and implement insights",
                description=raw,
                priority="medium",
                estimated_hours=2.0,
            )],
            total_estimated_hours=2.0,
        )

    logger.info(f"Plan generated: {plan.title} ({len(plan.tasks)} tasks, {plan.total_estimated_hours}h)")
    return plan, chat_result
