"""Generate a personal brand content plan for Dylan Does Business."""

import json
from loguru import logger

from src.models import AnalysisResult, ReelMetadata, ImplementationPlan, PlanTask
from src.prompts.personal_brand import build_personal_brand_prompt
from src.services.llm import chat, ChatResult, get_model_for_step


def generate_personal_brand_plan(
    analysis: AnalysisResult, metadata: ReelMetadata, transcript: str,
) -> tuple[ImplementationPlan, ChatResult]:
    """Generate a personal brand content plan from the analysis."""

    system_prompt, user_prompt = build_personal_brand_prompt(
        analysis, metadata, transcript,
    )

    logger.info("Generating personal brand content plan...")
    chat_result = chat(system=system_prompt, user_content=user_prompt, max_tokens=3000, model_override=get_model_for_step("personal_brand"))
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
            title=data.get("title", f"DDB Content: {metadata.shortcode}"),
            summary=data.get("summary", ""),
            tasks=tasks,
            total_estimated_hours=sum(t.estimated_hours for t in tasks),
        )
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Failed to parse personal brand JSON, creating single-task plan")
        plan = ImplementationPlan(
            title=f"DDB Content: {metadata.shortcode}",
            summary=raw[:500],
            tasks=[PlanTask(
                title="Create adapted content for Dylan Does Business",
                description=raw,
                priority="medium",
                estimated_hours=2.0,
                requires_human=True,
                human_reason="Needs filming and content approval",
            )],
            total_estimated_hours=2.0,
        )

    logger.info(
        f"Personal brand plan generated: {plan.title} "
        f"({len(plan.tasks)} tasks, {plan.total_estimated_hours}h)"
    )
    return plan, chat_result
