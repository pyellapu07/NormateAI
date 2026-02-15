"""Data fusion engine — correlate quantitative and qualitative findings.

Algorithms implemented:
─────────────────────
1. Theme-metric alignment: match qual topics to quant metrics by keyword overlap
2. Sentiment-metric correlation: compare sentiment polarity with metric directions
3. Anomaly-theme co-occurrence: check if qual themes cluster around quant anomalies
4. Segment insight extraction: find which dimensions show the biggest discrepancies
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def _extract_keywords(text: str) -> set[str]:
    """Extract lowercase keywords from a string."""
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def align_themes_to_metrics(quant_results: dict, qual_results: dict) -> list[dict]:
    """Match qualitative topics to quantitative metrics by keyword overlap.

    For each topic, check if any of its top_words or label words appear
    in metric column names. This creates a soft alignment between the two
    data sources.
    """
    alignments = []
    topics = qual_results.get("topics", [])
    metric_cols = quant_results.get("column_classification", {}).get("metric_cols", [])
    ts = quant_results.get("time_series", {})

    for topic in topics:
        topic_keywords = set(topic.get("top_words", []))
        topic_keywords |= _extract_keywords(topic.get("label", ""))

        matched_metrics = []
        for col in metric_cols:
            col_keywords = _extract_keywords(col)
            overlap = topic_keywords & col_keywords
            if overlap:
                metric_ts = ts.get(col, {})
                matched_metrics.append({
                    "metric": col,
                    "overlap_keywords": list(overlap),
                    "pct_change": metric_ts.get("pct_change"),
                    "direction": metric_ts.get("direction"),
                })

        if matched_metrics:
            alignments.append({
                "topic": topic["label"],
                "topic_sentiment": topic["avg_sentiment"],
                "matched_metrics": matched_metrics,
            })

    return alignments


def correlate_sentiment_direction(quant_results: dict, qual_results: dict) -> list[dict]:
    """Detect sentiment-metric direction correlations.

    Logic:
    - If a topic has negative sentiment AND a related metric is trending down
      → strong negative correlation (problem confirmed by both sources)
    - If a topic has positive sentiment AND a metric is trending up
      → strong positive correlation (success confirmed by both sources)
    - Mismatches are interesting too: positive sentiment but metric declining
      → possible gap between perception and reality
    """
    correlations = []
    topics = qual_results.get("topics", [])
    ts = quant_results.get("time_series", {})

    for topic in topics:
        sentiment = topic.get("avg_sentiment", 0)
        sent_dir = "positive" if sentiment > 0.1 else ("negative" if sentiment < -0.1 else "neutral")

        for metric_name, metric_data in ts.items():
            metric_dir = metric_data.get("direction", "flat")
            pct = metric_data.get("pct_change", 0)

            # Determine correlation type
            if sent_dir == "negative" and metric_dir == "down":
                corr_type = "confirmed_problem"
                strength = "strong"
            elif sent_dir == "positive" and metric_dir == "up":
                corr_type = "confirmed_success"
                strength = "strong"
            elif sent_dir == "negative" and metric_dir == "up":
                corr_type = "divergent"
                strength = "moderate"
            elif sent_dir == "positive" and metric_dir == "down":
                corr_type = "divergent"
                strength = "moderate"
            else:
                continue

            correlations.append({
                "topic": topic["label"],
                "topic_sentiment": round(sentiment, 4),
                "sentiment_direction": sent_dir,
                "metric": metric_name,
                "metric_direction": metric_dir,
                "metric_pct_change": pct,
                "correlation_type": corr_type,
                "strength": strength,
            })

    # Sort by strength (strong first), then by sentiment magnitude
    correlations.sort(
        key=lambda c: (0 if c["strength"] == "strong" else 1, -abs(c["topic_sentiment"]))
    )
    return correlations


def extract_segment_insights(quant_results: dict) -> list[dict]:
    """Find segments with the biggest metric discrepancies.

    For each dimension × metric pair, compute the spread (best - worst)
    relative to the overall mean. Large spreads indicate segments
    worth investigating.
    """
    insights = []
    segments = quant_results.get("segments", {})
    stats = quant_results.get("descriptive_stats", {})

    for dim, metrics in segments.items():
        for metric_name, metric_data in metrics.items():
            spread = metric_data.get("spread", 0)
            overall_mean = stats.get(metric_name, {}).get("mean", 1)
            if overall_mean == 0:
                continue

            relative_spread = abs(spread / overall_mean) * 100

            if relative_spread > 15:  # At least 15% difference
                insights.append({
                    "dimension": dim,
                    "metric": metric_name,
                    "best_segment": metric_data["best"],
                    "worst_segment": metric_data["worst"],
                    "spread": spread,
                    "relative_spread_pct": round(relative_spread, 2),
                    "segment_details": metric_data["segments"],
                })

    insights.sort(key=lambda x: x["relative_spread_pct"], reverse=True)
    return insights


def detect_anomaly_theme_overlap(quant_results: dict, qual_results: dict) -> list[dict]:
    """Check if qualitative themes mention concepts related to anomalous metrics.

    Heuristic: if a metric has anomalies AND a qual topic mentions related
    keywords, users are noticing the same problems the data shows.
    """
    overlaps = []
    anomaly_summary = quant_results.get("anomaly_summary", {})
    topics = qual_results.get("topics", [])

    for col, count in anomaly_summary.items():
        if count == 0:
            continue
        col_keywords = _extract_keywords(col)

        for topic in topics:
            topic_keywords = set(topic.get("top_words", []))
            topic_keywords |= _extract_keywords(topic.get("label", ""))

            overlap = col_keywords & topic_keywords
            if overlap:
                overlaps.append({
                    "anomalous_metric": col,
                    "anomaly_count": count,
                    "related_topic": topic["label"],
                    "topic_sentiment": topic["avg_sentiment"],
                    "overlap_keywords": list(overlap),
                })

    return overlaps


# ── Main Entry Point ─────────────────────────────────────────


async def fuse_findings(quant_results: dict, qual_results: dict) -> dict:
    """Fuse quantitative and qualitative analysis results.

    Returns a structured dict with all cross-data correlations and insights.
    """
    if "error" in quant_results or "error" in qual_results:
        return {
            "error": quant_results.get("error") or qual_results.get("error"),
            "theme_metric_alignments": [],
            "sentiment_correlations": [],
            "segment_insights": [],
            "anomaly_theme_overlaps": [],
        }

    alignments = align_themes_to_metrics(quant_results, qual_results)
    correlations = correlate_sentiment_direction(quant_results, qual_results)
    segment_insights = extract_segment_insights(quant_results)
    anomaly_overlaps = detect_anomaly_theme_overlap(quant_results, qual_results)

    # Summary counts
    confirmed_problems = sum(
        1 for c in correlations if c["correlation_type"] == "confirmed_problem"
    )
    confirmed_successes = sum(
        1 for c in correlations if c["correlation_type"] == "confirmed_success"
    )

    logger.info(
        "Fusion complete — %d alignments, %d correlations (%d problems, %d successes), "
        "%d segment insights, %d anomaly-theme overlaps",
        len(alignments), len(correlations), confirmed_problems, confirmed_successes,
        len(segment_insights), len(anomaly_overlaps),
    )

    return {
        "theme_metric_alignments": alignments,
        "sentiment_correlations": correlations,
        "segment_insights": segment_insights,
        "anomaly_theme_overlaps": anomaly_overlaps,
        "summary": {
            "confirmed_problems": confirmed_problems,
            "confirmed_successes": confirmed_successes,
            "divergent_signals": len(correlations) - confirmed_problems - confirmed_successes,
            "segment_insights_count": len(segment_insights),
        },
    }
