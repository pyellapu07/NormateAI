"""Analysis router — upload files, run pipeline, retrieve results, history."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from models.schemas import JobResponse, JobStatus
from services.quant_processor import process_quant_files
from services.qual_processor import process_qual_files
from services.fusion_engine import fuse_findings
from services.claude_service import generate_recommendations, chat_response
from services.database import save_job, get_job, get_all_jobs, delete_job, delete_all_jobs

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

# ── In-memory cache (fast lookups for active jobs) ───────────

_jobs: dict[str, dict] = {}

# ── Allowed extensions ──────────────────────────────────────

QUANT_EXTENSIONS = {".csv", ".xlsx", ".xls"}
QUAL_EXTENSIONS = {".txt", ".docx", ".doc"}


# ── Background Analysis Pipeline ────────────────────────────


async def _run_analysis(job_id: str):
    """Run the full analysis pipeline in the background."""
    job = _jobs.get(job_id)
    if not job:
        logger.error("Job %s — not found in memory", job_id)
        return

    job["status"] = JobStatus.PROCESSING
    await save_job(job_id, _serialisable(job))
    logger.info("Job %s — starting analysis pipeline", job_id)

    try:
        # Step 1: Quantitative processing
        logger.info("Job %s — Step 1/4: Quant processing", job_id)
        quant_results = await process_quant_files(job["quant_file_contents"])

        # Step 2: Qualitative processing
        logger.info("Job %s — Step 2/4: Qual processing", job_id)
        qual_results = await process_qual_files(job["qual_file_contents"])

        # Step 3: Fuse findings
        logger.info("Job %s — Step 3/4: Data fusion", job_id)
        fusion_results = await fuse_findings(quant_results, qual_results)

        # Step 4: Generate recommendations
        logger.info("Job %s — Step 4/4: Generating recommendations", job_id)
        recommendations = await generate_recommendations(
            context={
                "research_question": job["research_question"],
                "product_description": job["product_description"],
                "time_period": job.get("time_period"),
                "arpu": job.get("arpu"),
            },
            quant_results=quant_results,
            qual_results=qual_results,
            fusion_results=fusion_results,
        )

        job["results"] = {
            "quant": quant_results,
            "qual": qual_results,
            "fusion": fusion_results,
            "recommendations": recommendations,
        }
        job["status"] = JobStatus.COMPLETED
        job["completed_at"] = datetime.utcnow().isoformat()
        logger.info("Job %s — complete", job_id)

        # Persist to database
        await save_job(job_id, _serialisable(job))

    except Exception as e:
        logger.error("Job %s — failed: %s\n%s", job_id, e, traceback.format_exc())
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)
        await save_job(job_id, _serialisable(job))


def _serialisable(job: dict) -> dict:
    """Strip non-serialisable data (raw file bytes) before saving to DB."""
    return {k: v for k, v in job.items() if k not in ("quant_file_contents", "qual_file_contents")}


# ── POST /api/analyze ───────────────────────────────────────


@router.post("/analyze", response_model=JobResponse)
async def submit_analysis(
    background_tasks: BackgroundTasks,
    quant_files: list[UploadFile] = File(...),
    qual_files: list[UploadFile] = File(...),
    research_question: str = Form(...),
    product_description: str = Form(...),
    time_period: Optional[str] = Form(None),
    arpu: Optional[float] = Form(None),
):
    """Accept uploaded files + context, kick off async analysis, return job ID."""

    if len(research_question.strip()) < 10:
        raise HTTPException(status_code=422, detail="Research question must be at least 10 characters.")
    if not quant_files or not quant_files[0].filename:
        raise HTTPException(status_code=422, detail="At least one quantitative file is required.")
    if not qual_files or not qual_files[0].filename:
        raise HTTPException(status_code=422, detail="At least one qualitative file is required.")

    # Read files into memory for the background task
    quant_contents = []
    for f in quant_files:
        content = await f.read()
        quant_contents.append((f.filename or "data.csv", content))

    qual_contents = []
    for f in qual_files:
        content = await f.read()
        qual_contents.append((f.filename or "feedback.txt", content))

    job_id = uuid4().hex[:12]
    _jobs[job_id] = {
        "status": JobStatus.PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "quant_file_contents": quant_contents,
        "qual_file_contents": qual_contents,
        "research_question": research_question,
        "product_description": product_description,
        "time_period": time_period,
        "arpu": arpu,
        "results": None,
        "error": None,
    }

    logger.info(
        "Job %s created — quant: %s, qual: %s, arpu: %s",
        job_id, [c[0] for c in quant_contents], [c[0] for c in qual_contents], arpu,
    )

    # Persist initial record
    await save_job(job_id, _serialisable(_jobs[job_id]))

    background_tasks.add_task(_run_analysis, job_id)

    return JobResponse(jobId=job_id, status=JobStatus.PENDING)


# ── GET /api/results/{job_id} ───────────────────────────────


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """Return analysis results (or processing status) for a job."""

    # Try in-memory first (fast path for active jobs)
    job = _jobs.get(job_id)

    # Fallback to database (for revisiting old reports)
    if not job:
        db_row = await get_job(job_id)
        if db_row:
            job = db_row
        else:
            raise HTTPException(status_code=404, detail="Job not found.")

    status = job.get("status")
    # Handle both enum and string
    status_val = status.value if hasattr(status, "value") else str(status)

    if status_val in ("pending", "processing"):
        return {
            "jobId": job_id,
            "status": status_val,
            "message": "Analysis still processing.",
        }

    if status_val == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {job.get('error', 'Unknown error')}",
        )

    # Completed — extract recommendations
    results = job.get("results")
    if not results:
        raise HTTPException(status_code=500, detail="Results missing from completed job.")

    rec = results.get("recommendations", results)

    return {
        "jobId": job_id,
        "status": "completed",
        "problemSummary": rec.get("problemSummary", ""),
        "quantEvidence": rec.get("quantEvidence", []),
        "qualEvidence": rec.get("qualEvidence", []),
        "actions": rec.get("actions", []),
        "abTests": rec.get("abTests", []),
        "metrics": rec.get("metrics", []),
        "suggestedQuestions": rec.get("suggestedQuestions", []),
        "financialImpact": rec.get("financialImpact"),
        "generatedAt": job.get("completed_at", datetime.utcnow().isoformat()),
        "_debug": {
            "quant_row_count": results.get("quant", {}).get("row_count") if isinstance(results.get("quant"), dict) else None,
            "qual_sentence_count": results.get("qual", {}).get("sentence_count") if isinstance(results.get("qual"), dict) else None,
            "fusion_summary": results.get("fusion", {}).get("summary") if isinstance(results.get("fusion"), dict) else None,
        },
    }


# ── GET /api/results/{job_id}/raw ────────────────────────────


@router.get("/results/{job_id}/raw")
async def get_raw_results(job_id: str):
    """Return full raw pipeline output for debugging."""

    job = _jobs.get(job_id)
    if not job:
        db_row = await get_job(job_id)
        if db_row:
            job = db_row
        else:
            raise HTTPException(status_code=404, detail="Job not found.")

    status_val = job["status"].value if hasattr(job["status"], "value") else str(job["status"])
    if status_val != "completed":
        raise HTTPException(status_code=400, detail="Results not ready yet.")

    results = job.get("results", {})
    return {
        "jobId": job_id,
        "quant": results.get("quant"),
        "qual": results.get("qual"),
        "fusion": results.get("fusion"),
        "recommendations": results.get("recommendations"),
    }


# ── History Endpoints ────────────────────────────────────────


@router.get("/history")
async def list_history():
    """Return all jobs (summary only, no full results)."""
    jobs = await get_all_jobs(limit=100)
    return {"jobs": jobs}


@router.delete("/history/{job_id}")
async def delete_history_item(job_id: str):
    """Delete a specific job from history."""
    success = await delete_job(job_id)
    # Also remove from in-memory cache
    _jobs.pop(job_id, None)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or delete failed.")
    return {"message": "Job deleted successfully."}


@router.delete("/history")
async def wipe_history():
    """Delete ALL jobs (wipe history feature)."""
    success = await delete_all_jobs()
    _jobs.clear()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to wipe history.")
    return {"message": "All history wiped successfully."}


# ── Chat Endpoint ────────────────────────────────────────────


class ChatRequest(BaseModel):
    question: str
    report_context: dict


@router.post("/chat/{job_id}")
async def chat_with_analysis(job_id: str, request: ChatRequest):
    """Answer follow-up questions about a completed report."""

    # Verify job exists and is completed
    job = _jobs.get(job_id)
    if not job:
        db_row = await get_job(job_id)
        if not db_row:
            raise HTTPException(status_code=404, detail="Job not found.")
        job = db_row

    status_val = job.get("status")
    if hasattr(status_val, "value"):
        status_val = status_val.value
    if status_val != "completed":
        raise HTTPException(status_code=400, detail="Report not ready for chat.")

    try:
        answer = await chat_response(request.question, request.report_context)
        return {"message": answer}
    except Exception as e:
        logger.error("Chat failed for job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail="Chat service unavailable.")
