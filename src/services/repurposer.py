"""Generate a content repurposing plan from a reel analysis."""

import json
from loguru import logger

from src.models import AnalysisResult, ReelMetadata, ImplementationPlan, PlanTask
from src.prompts.content_repurposing import build_repurposing_prompt
from src.services.llm import chat, ChatResult, get_model_for_step


def generate_repurposing_plan(
    analysis: AnalysisResult, metadata: ReelMetadata, transcript: str,
) -> tuple[ImplementationPlan, ChatResult]:
    """Generate a content repurposing plan from the analysis."""

    system_prompt, user_prompt = build_repurposing_prompt(analysis, metadata, transcript)

    logger.info("Generating content repurposing plan...")
    chat_result = chat(system=system_prompt, user_content=user_prompt, max_tokens=3000, model_override=get_model_for_step("repurposing"))
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
                requires_human=bool(t.get("requires_human", True)),
                human_reason=t.get("human_reason", ""),
            ))

        plan = ImplementationPlan(
            title=data.get("title", f"Repurposing: {metadata.shortcode}"),
            summary=data.get("summary", ""),
            tasks=tasks,
            total_estimated_hours=sum(t.estimated_hours for t in tasks),
        )
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Failed to parse repurposing JSON, creating single-task plan")
        plan = ImplementationPlan(
            title=f"Repurposing: {metadata.shortcode}",
            summary=raw[:500],
            tasks=[PlanTask(
                title="Create adapted content from reel",
                description=raw,
                priority="medium",
                estimated_hours=2.0,
                requires_human=True,
                human_reason="Needs filming and content approval",
            )],
            total_estimated_hours=2.0,
        )

    logger.info(f"Repurposing plan generated: {plan.title} ({len(plan.tasks)} tasks, {plan.total_estimated_hours}h)")
    return plan, chat_result
