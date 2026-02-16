"""Supabase database integration for Normate AI.

Provides CRUD operations for the jobs table. All functions are async-compatible
and handle errors gracefully — callers should check return values.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Lazy-loaded Supabase client ──────────────────────────────

_client = None

try:
    from supabase import create_client, Client
    _HAS_SUPABASE = True
except ImportError:
    _HAS_SUPABASE = False
    logger.warning("supabase SDK not installed — database persistence disabled")


def get_client():
    """Return a Supabase client, creating one if needed."""
    global _client

    if not _HAS_SUPABASE:
        return None

    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not set — persistence disabled")
        return None

    try:
        _client = create_client(url, key)
        logger.info("Supabase client initialised")
        return _client
    except Exception as e:
        logger.error("Failed to initialise Supabase: %s", e)
        return None


# ── CRUD helpers ─────────────────────────────────────────────


async def save_job(job_id: str, data: dict) -> bool:
    """Upsert a job row. Returns True on success."""
    client = get_client()
    if not client:
        return False

    try:
        row = {
            "job_id": job_id,
            "status": data.get("status").value if hasattr(data.get("status"), "value") else str(data.get("status", "pending")),
            "research_question": data.get("research_question", ""),
            "product_description": data.get("product_description", ""),
            "time_period": data.get("time_period"),
            "arpu": data.get("arpu"),
            "results": data.get("results"),
            "error": data.get("error"),
            "created_at": data.get("created_at"),
            "completed_at": data.get("completed_at"),
        }
        client.table("jobs").upsert(row).execute()
        return True
    except Exception as e:
        logger.error("save_job(%s) failed: %s", job_id, e)
        return False


async def get_job(job_id: str) -> Optional[dict]:
    """Fetch a single job by ID. Returns None if not found."""
    client = get_client()
    if not client:
        return None

    try:
        resp = client.table("jobs").select("*").eq("job_id", job_id).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]
        return None
    except Exception as e:
        logger.error("get_job(%s) failed: %s", job_id, e)
        return None


async def get_all_jobs(limit: int = 50) -> list[dict]:
    """List jobs ordered by newest first (summary fields only)."""
    client = get_client()
    if not client:
        return []

    try:
        resp = (
            client.table("jobs")
            .select("job_id, status, research_question, product_description, created_at, completed_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.error("get_all_jobs failed: %s", e)
        return []


async def delete_job(job_id: str) -> bool:
    """Delete a single job. Returns True on success."""
    client = get_client()
    if not client:
        return False

    try:
        client.table("jobs").delete().eq("job_id", job_id).execute()
        return True
    except Exception as e:
        logger.error("delete_job(%s) failed: %s", job_id, e)
        return False


async def delete_all_jobs() -> bool:
    """Wipe every job row. Returns True on success."""
    client = get_client()
    if not client:
        return False

    try:
        # Supabase requires a filter — use a tautology to match all rows
        client.table("jobs").delete().neq("job_id", "").execute()
        return True
    except Exception as e:
        logger.error("delete_all_jobs failed: %s", e)
        return False
