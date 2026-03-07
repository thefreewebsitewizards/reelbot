from fastapi import APIRouter, HTTPException
from loguru import logger

from src.models import ReelRequest, PipelineResult, PlanStatus, TranscriptResult, CostBreakdown
from src.services.downloader import download_reel, extract_shortcode
from src.services.audio import extract_audio
from src.services.frames import extract_keyframes
from src.services.transcriber import transcribe
from src.services.analyzer import analyze_reel, analyze_carousel
from src.services.ocr import extract_text_from_images
from src.services.planner import generate_plan, check_plan_similarity
from src.services.repurposer import generate_repurposing_plan
from src.services.personal_brand import generate_personal_brand_plan
from src.utils.file_ops import create_temp_dir, cleanup_temp_dir
from src.utils.plan_writer import write_plan
from src.utils.plan_manager import is_duplicate

router = APIRouter()


@router.post("/process-reel")
def process_reel(request: ReelRequest) -> dict:
    """Full pipeline: download → extract audio/frames → transcribe → analyze → plan → store."""
    reel_id = ""
    try:
        reel_id = extract_shortcode(request.reel_url)

        if is_duplicate(reel_id):
            raise HTTPException(
                status_code=409,
                detail=f"Reel {reel_id} has already been processed. Check /plans/{reel_id} for its status.",
            )

        logger.info(f"Processing reel: {reel_id}")

        # Setup
        temp_dir = create_temp_dir(reel_id)

        # Pipeline — branch for carousel vs reel
        download_result, metadata = download_reel(request.reel_url, temp_dir)

        costs = CostBreakdown()

        if metadata.content_type == "carousel":
            image_paths = download_result
            ocr_text = extract_text_from_images(image_paths)
            transcript = TranscriptResult(text=ocr_text, language="en")
            analysis, analysis_cr = analyze_carousel(ocr_text, metadata, image_paths)
        else:
            video_path = download_result
            audio_path = extract_audio(video_path, temp_dir)
            frame_paths = extract_keyframes(video_path, temp_dir)
            transcript = transcribe(audio_path)
            analysis, analysis_cr = analyze_reel(transcript, metadata, frame_paths)
        costs.add("analysis", analysis_cr.model, analysis_cr.prompt_tokens, analysis_cr.completion_tokens, analysis_cr.cost_usd)

        similarity, sim_cr = check_plan_similarity(analysis)
        if sim_cr:
            costs.add("similarity", sim_cr.model, sim_cr.prompt_tokens, sim_cr.completion_tokens, sim_cr.cost_usd)

        plan, plan_cr = generate_plan(analysis, metadata)
        costs.add("plan", plan_cr.model, plan_cr.prompt_tokens, plan_cr.completion_tokens, plan_cr.cost_usd)

        repurposing_plan, rep_cr = generate_repurposing_plan(analysis, metadata, transcript.text)
        costs.add("repurposing", rep_cr.model, rep_cr.prompt_tokens, rep_cr.completion_tokens, rep_cr.cost_usd)

        personal_brand_plan, pb_cr = generate_personal_brand_plan(analysis, metadata, transcript.text)
        costs.add("personal_brand", pb_cr.model, pb_cr.prompt_tokens, pb_cr.completion_tokens, pb_cr.cost_usd)

        # Store results
        result = PipelineResult(
            reel_id=reel_id,
            status=PlanStatus.REVIEW,
            metadata=metadata,
            transcript=transcript,
            analysis=analysis,
            plan=plan,
            repurposing_plan=repurposing_plan,
            personal_brand_plan=personal_brand_plan,
            similarity=similarity,
            cost_breakdown=costs,
        )
        plan_dir = write_plan(result)

        # Read back the full plan markdown for review
        plan_md = (plan_dir / "plan.md").read_text()

        # Cleanup temp files
        cleanup_temp_dir(reel_id)

        logger.info(f"Pipeline complete for {reel_id}")
        response = {
            "status": "success",
            "reel_id": reel_id,
            "plan_title": plan.title,
            "plan_summary": plan.summary,
            "tasks_count": len(plan.tasks),
            "total_hours": plan.total_estimated_hours,
            "plan_dir": str(plan_dir),
            "relevance_score": analysis.relevance_score,
            "plan_markdown": plan_md,
        }
        if repurposing_plan:
            response["repurposing_tasks_count"] = len(repurposing_plan.tasks)
            response["repurposing_total_hours"] = repurposing_plan.total_estimated_hours
        if personal_brand_plan:
            response["personal_brand_tasks_count"] = len(personal_brand_plan.tasks)
            response["personal_brand_total_hours"] = personal_brand_plan.total_estimated_hours
        if similarity and similarity.similar_plans:
            response["similarity"] = {
                "max_score": similarity.max_score,
                "recommendation": similarity.recommendation,
                "similar_plans": [
                    {"title": p.title, "score": p.score}
                    for p in similarity.similar_plans
                ],
            }
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline failed for {reel_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
