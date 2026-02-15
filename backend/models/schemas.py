"""Pydantic models for Normate AI API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Impact(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Difficulty(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


# ── Request Models ───────────────────────────────────────────


class AnalysisContext(BaseModel):
    research_question: str = Field(..., min_length=10)
    product_description: str = Field(..., min_length=5)
    time_period: Optional[str] = None


# ── Response Models ──────────────────────────────────────────


class JobResponse(BaseModel):
    jobId: str = Field(default_factory=lambda: uuid4().hex[:12])
    status: JobStatus = JobStatus.PENDING
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QuantEvidence(BaseModel):
    metric: str
    value: str
    change: Optional[str] = None
    direction: Optional[Direction] = None


class QualEvidence(BaseModel):
    theme: str
    sentiment: float
    sentimentLabel: SentimentLabel
    quotes: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    title: str
    description: str
    evidence: str
    impact: Impact
    difficulty: Difficulty
    estimatedEffect: str


class ABTest(BaseModel):
    name: str
    control: str
    treatment: str
    metric: str
    duration: str


class TrackedMetric(BaseModel):
    name: str
    current: str
    target: str


class AnalysisResult(BaseModel):
    jobId: str
    status: JobStatus
    problemSummary: str = ""
    quantEvidence: list[QuantEvidence] = Field(default_factory=list)
    qualEvidence: list[QualEvidence] = Field(default_factory=list)
    actions: list[RecommendedAction] = Field(default_factory=list)
    abTests: list[ABTest] = Field(default_factory=list)
    metrics: list[TrackedMetric] = Field(default_factory=list)
    generatedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
