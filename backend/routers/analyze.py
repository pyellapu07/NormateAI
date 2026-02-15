"""Analysis router — upload files, run pipeline, retrieve results."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from models.schemas import JobResponse, JobStatus
from services.quant_processor import process_quant_files
from services.qual_processor import process_qual_files
from services.fusion_engine import fuse_findings
from services.claude_service import generate_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

# ── In-memory job store (replace with Supabase in Phase 4) ──

_jobs: dict[str, dict] = {}

# ── Allowed extensions ──────────────────────────────────────

QUANT_EXTENSIONS = {".csv", ".xlsx", ".xls"}
QUAL_EXTENSIONS = {".txt", ".docx", ".doc"}


# ── Background Analysis Pipeline ────────────────────────────


async def _run_analysis(job_id: str):
    """Run the full analysis pipeline in the background."""
    job = _jobs[job_id]
    job["status"] = JobStatus.PROCESSING
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
        logger.info("Job %s — ✅ complete", job_id)

    except Exception as e:
        logger.error("Job %s — ❌ failed: %s\n%s", job_id, e, traceback.format_exc())
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)


# ── POST /api/analyze ───────────────────────────────────────


@router.post("/analyze", response_model=JobResponse)
async def submit_analysis(
    background_tasks: BackgroundTasks,
    quant_files: list[UploadFile] = File(...),
    qual_files: list[UploadFile] = File(...),
    research_question: str = Form(...),
    product_description: str = Form(...),
    time_period: Optional[str] = Form(None),
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
        "results": None,
        "error": None,
    }

    logger.info(
        "Job %s created — quant: %s, qual: %s",
        job_id, [c[0] for c in quant_contents], [c[0] for c in qual_contents],
    )

    background_tasks.add_task(_run_analysis, job_id)

    return JobResponse(jobId=job_id, status=JobStatus.PENDING)


# ── GET /api/results/{job_id} ───────────────────────────────


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """Return analysis results (or processing status) for a job."""

    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    job = _jobs[job_id]

    if job["status"] in (JobStatus.PENDING, JobStatus.PROCESSING):
        return {
            "jobId": job_id,
            "status": job["status"].value,
            "message": "Analysis still processing.",
        }

    if job["status"] == JobStatus.FAILED:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {job.get('error', 'Unknown error')}",
        )

    rec = job["results"]["recommendations"]

    return {
        "jobId": job_id,
        "status": "completed",
        "problemSummary": rec.get("problemSummary", ""),
        "quantEvidence": rec.get("quantEvidence", []),
        "qualEvidence": rec.get("qualEvidence", []),
        "actions": rec.get("actions", []),
        "abTests": rec.get("abTests", []),
        "metrics": rec.get("metrics", []),
        "generatedAt": job.get("completed_at", datetime.utcnow().isoformat()),
        "_debug": {
            "quant_row_count": job["results"]["quant"].get("row_count"),
            "qual_sentence_count": job["results"]["qual"].get("sentence_count"),
            "fusion_summary": job["results"]["fusion"].get("summary"),
        },
    }


# ── GET /api/results/{job_id}/raw ────────────────────────────


@router.get("/results/{job_id}/raw")
async def get_raw_results(job_id: str):
    """Return full raw pipeline output for debugging."""

    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = _jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Results not ready yet.")

    return {
        "jobId": job_id,
        "quant": job["results"]["quant"],
        "qual": job["results"]["qual"],
        "fusion": job["results"]["fusion"],
        "recommendations": job["results"]["recommendations"],
    }
