"""Normate AI — FastAPI Backend."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.analyze import router as analyze_router

# ── Config ───────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("normate")

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Normate AI",
    description="AI-powered UX research synthesis — fuse quant + qual data into actionable recommendations.",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(analyze_router, prefix="/api")


# ── Health Check ─────────────────────────────────────────────


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "normate-ai"}


# ── Startup ──────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    logger.info("🚀 Normate AI backend starting up")
    logger.info("   CORS origins: %s", ALLOWED_ORIGINS)
