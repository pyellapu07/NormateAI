"""Quantitative data processor — CSV/Excel analysis pipeline.

Algorithms implemented:
─────────────────────
1. Auto-detection: Pattern-match column names to types (date, metric, dimension)
2. Descriptive statistics: mean, median, std, min, max, percentiles via pandas
3. Anomaly detection:
   - Z-score method (|z| > 2.5 flagged)
   - IQR method (Q1 - 1.5*IQR ... Q3 + 1.5*IQR)
4. Time-series analysis: period-over-period change, trend direction
5. Segmentation: group-by on detected dimensions, compare segment stats
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Column Type Detection ────────────────────────────────────

DATE_PATTERNS = re.compile(
    r"(date|time|timestamp|period|month|week|day|year)", re.IGNORECASE
)
METRIC_PATTERNS = re.compile(
    r"(view|visit|session|download|click|bounce|engagement|rate|duration|"
    r"revenue|conversion|user|subscriber|score|count|total|avg|average|"
    r"time.on|page.view|impressions|ctr|open.rate|churn|retention|"
    r"signup|install|uninstall|error|latency|load.time|lcp|fcp|cls|"
    r"satisfaction|nps|csat|response)", re.IGNORECASE
)
DIMENSION_PATTERNS = re.compile(
    r"(device|platform|browser|country|region|city|channel|source|medium|"
    r"segment|category|type|group|cohort|plan|tier|os|version|campaign|"
    r"age.group|gender|language)", re.IGNORECASE
)


@dataclass
class ColumnClassification:
    date_cols: list[str] = field(default_factory=list)
    metric_cols: list[str] = field(default_factory=list)
    dimension_cols: list[str] = field(default_factory=list)
    unknown_cols: list[str] = field(default_factory=list)


def classify_columns(df: pd.DataFrame) -> ColumnClassification:
    """Auto-detect column types based on name patterns and data types."""
    result = ColumnClassification()

    for col in df.columns:
        col_str = str(col).strip()

        # Try parsing as date first
        if DATE_PATTERNS.search(col_str):
            try:
                pd.to_datetime(df[col], errors="raise", format="mixed")
                result.date_cols.append(col_str)
                continue
            except (ValueError, TypeError):
                pass

        if METRIC_PATTERNS.search(col_str):
            if pd.api.types.is_numeric_dtype(df[col]):
                result.metric_cols.append(col_str)
                continue

        if DIMENSION_PATTERNS.search(col_str):
            result.dimension_cols.append(col_str)
            continue

        # Fallback heuristics
        if pd.api.types.is_numeric_dtype(df[col]):
            result.metric_cols.append(col_str)
        elif pd.api.types.is_object_dtype(df[col]):
            nunique = df[col].nunique()
            if nunique <= max(20, len(df) * 0.3):
                result.dimension_cols.append(col_str)
            else:
                result.unknown_cols.append(col_str)
        else:
            result.unknown_cols.append(col_str)

    logger.info(
        "Columns — dates: %s, metrics: %s, dims: %s, unknown: %s",
        result.date_cols, result.metric_cols,
        result.dimension_cols, result.unknown_cols,
    )
    return result


# ── Descriptive Statistics ───────────────────────────────────


def compute_descriptive_stats(df: pd.DataFrame, metric_cols: list[str]) -> dict:
    """Compute descriptive statistics for each metric column."""
    stats = {}
    for col in metric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        desc = series.describe()
        stats[col] = {
            "mean": round(float(desc.get("mean", 0)), 4),
            "median": round(float(series.median()), 4),
            "std": round(float(desc.get("std", 0)), 4),
            "min": round(float(desc.get("min", 0)), 4),
            "max": round(float(desc.get("max", 0)), 4),
            "q25": round(float(desc.get("25%", 0)), 4),
            "q75": round(float(desc.get("75%", 0)), 4),
            "count": int(desc.get("count", 0)),
            "null_count": int(series.isna().sum()),
        }
    return stats


# ── Anomaly Detection ────────────────────────────────────────


@dataclass
class Anomaly:
    column: str
    method: str
    index: int
    value: float
    score: float
    date: Optional[str] = None


def detect_anomalies_zscore(
    df: pd.DataFrame, metric_cols: list[str], threshold: float = 2.5
) -> list[Anomaly]:
    """Z-score anomaly detection.

    Z = (x - μ) / σ  →  flag if |Z| > threshold.

    Assumes roughly normal distribution.
    Threshold 2.5 catches ~1.2% of data under normality.
    """
    anomalies = []
    for col in metric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 5:
            continue

        mean = series.mean()
        std = series.std()
        if std == 0:
            continue

        z_scores = (series - mean) / std
        for idx in z_scores.index:
            z = z_scores[idx]
            if abs(z) > threshold:
                anomalies.append(Anomaly(
                    column=col, method="zscore",
                    index=int(idx), value=round(float(series[idx]), 4),
                    score=round(float(z), 4),
                ))
    return anomalies


def detect_anomalies_iqr(
    df: pd.DataFrame, metric_cols: list[str], multiplier: float = 1.5
) -> list[Anomaly]:
    """IQR anomaly detection.

    Fences: [Q1 - k*IQR, Q3 + k*IQR]  →  points outside are anomalies.

    More robust than Z-score for skewed distributions
    (very common in web analytics data).
    """
    anomalies = []
    for col in metric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 5:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr

        for idx in series.index:
            val = series[idx]
            if val < lower:
                anomalies.append(Anomaly(
                    column=col, method="iqr",
                    index=int(idx), value=round(float(val), 4),
                    score=round(float((lower - val) / iqr), 4),
                ))
            elif val > upper:
                anomalies.append(Anomaly(
                    column=col, method="iqr",
                    index=int(idx), value=round(float(val), 4),
                    score=round(float((val - upper) / iqr), 4),
                ))
    return anomalies


# ── Time-Series Analysis ─────────────────────────────────────


def analyze_time_series(
    df: pd.DataFrame, date_col: str, metric_cols: list[str],
) -> dict:
    """Period-over-period analysis.

    Splits data into first-half vs second-half, compares means.
    Also fits a linear slope for trend direction.
    """
    results = {}
    try:
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).sort_values(date_col)
    except Exception:
        return results

    if len(df) < 4:
        return results

    mid = len(df) // 2
    first_half = df.iloc[:mid]
    second_half = df.iloc[mid:]

    for col in metric_cols:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        if series.isna().sum() > len(series) * 0.5:
            continue

        m1 = pd.to_numeric(first_half[col], errors="coerce").mean()
        m2 = pd.to_numeric(second_half[col], errors="coerce").mean()

        pct = ((m2 - m1) / abs(m1) * 100) if m1 != 0 else 0.0

        clean = series.dropna()
        slope = float(np.polyfit(np.arange(len(clean)), clean.values, 1)[0]) if len(clean) >= 3 else 0.0

        direction = "up" if pct > 5 else ("down" if pct < -5 else "flat")

        results[col] = {
            "mean_first_half": round(float(m1), 4),
            "mean_second_half": round(float(m2), 4),
            "pct_change": round(pct, 2),
            "direction": direction,
            "trend_slope": round(slope, 6),
            "date_range": {
                "start": str(df[date_col].min().date()),
                "end": str(df[date_col].max().date()),
            },
        }
    return results


# ── Segment Analysis ─────────────────────────────────────────


def analyze_segments(
    df: pd.DataFrame, dimension_cols: list[str], metric_cols: list[str],
) -> dict:
    """Group-by each dimension, compare metric means across segments."""
    results = {}
    for dim in dimension_cols:
        if dim not in df.columns or df[dim].nunique() > 20:
            continue

        dim_results = {}
        for met in metric_cols:
            if met not in df.columns:
                continue
            grouped = df.groupby(dim)[met].agg(["mean", "count"]).dropna()
            if len(grouped) < 2:
                continue

            segments = {
                str(name): {"mean": round(float(row["mean"]), 4), "count": int(row["count"])}
                for name, row in grouped.iterrows()
            }
            sorted_segs = sorted(segments.items(), key=lambda x: x[1]["mean"])
            dim_results[met] = {
                "segments": segments,
                "worst": sorted_segs[0][0],
                "best": sorted_segs[-1][0],
                "spread": round(sorted_segs[-1][1]["mean"] - sorted_segs[0][1]["mean"], 4),
            }

        if dim_results:
            results[dim] = dim_results
    return results


# ── Main Entry Point ─────────────────────────────────────────


async def process_quant_files(file_contents: list[tuple[str, bytes]]) -> dict:
    """Process uploaded quantitative data files end-to-end.

    Args:
        file_contents: List of (filename, raw_bytes) tuples.

    Returns:
        Full analysis dict with stats, anomalies, time-series, segments.
    """
    all_dfs = []

    for filename, content in file_contents:
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(content))
            else:
                continue
            df.columns = [str(c).strip() for c in df.columns]
            all_dfs.append(df)
            logger.info("Parsed %s: %d rows × %d cols", filename, len(df), len(df.columns))
        except Exception as e:
            logger.error("Failed to parse %s: %s", filename, e)

    if not all_dfs:
        return {"error": "No valid quantitative data files could be parsed."}

    df = pd.concat(all_dfs, ignore_index=True) if len(all_dfs) > 1 else all_dfs[0]
    classification = classify_columns(df)
    desc_stats = compute_descriptive_stats(df, classification.metric_cols)

    anomalies_z = detect_anomalies_zscore(df, classification.metric_cols)
    anomalies_iqr = detect_anomalies_iqr(df, classification.metric_cols)

    seen = set()
    combined_anomalies = []
    for a in anomalies_iqr + anomalies_z:
        key = (a.column, a.index)
        if key not in seen:
            seen.add(key)
            combined_anomalies.append(a)

    time_series = {}
    if classification.date_cols:
        time_series = analyze_time_series(df, classification.date_cols[0], classification.metric_cols)

    segments = analyze_segments(df, classification.dimension_cols, classification.metric_cols)

    summary_metrics = []
    for col, stats in desc_stats.items():
        ts = time_series.get(col, {})
        summary_metrics.append({
            "metric": col,
            "mean": stats["mean"],
            "median": stats["median"],
            "std": stats["std"],
            "pct_change": ts.get("pct_change"),
            "direction": ts.get("direction"),
            "anomaly_count": sum(1 for a in combined_anomalies if a.column == col),
        })

    return {
        "row_count": len(df),
        "column_classification": {
            "date_cols": classification.date_cols,
            "metric_cols": classification.metric_cols,
            "dimension_cols": classification.dimension_cols,
        },
        "descriptive_stats": desc_stats,
        "anomalies": [
            {"column": a.column, "method": a.method, "row_index": a.index,
             "value": a.value, "score": a.score}
            for a in combined_anomalies[:50]
        ],
        "anomaly_summary": {
            col: sum(1 for a in combined_anomalies if a.column == col)
            for col in classification.metric_cols
            if any(a.column == col for a in combined_anomalies)
        },
        "time_series": time_series,
        "segments": segments,
        "summary_metrics": summary_metrics,
    }
