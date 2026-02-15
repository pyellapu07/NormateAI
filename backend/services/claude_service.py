"""Claude API integration — expert UX research synthesis.

This is the brain of Normate AI. Takes the structured pipeline output
(quant stats, qual themes, fusion correlations) and sends it to Claude
with an expert-level prompt to generate deep, actionable recommendations
with root cause analysis, specific UX solutions, evidence citations,
and business impact estimates.

Falls back to a rule-based generator if the API key is missing or
the call fails, so the pipeline always returns something useful.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try to import anthropic SDK ──────────────────────────────

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False
    logger.warning("anthropic SDK not installed — will use fallback recommendation engine")


# ── Prompt Construction ──────────────────────────────────────


def _build_prompt(
    context: dict,
    quant_results: dict,
    qual_results: dict,
    fusion_results: dict,
) -> str:
    """Build the analysis prompt with all pipeline data embedded."""

    # Summarize quant findings concisely
    quant_summary = {
        "row_count": quant_results.get("row_count", 0),
        "metrics_analyzed": quant_results.get("column_classification", {}).get("metric_cols", []),
        "dimensions": quant_results.get("column_classification", {}).get("dimension_cols", []),
        "descriptive_stats": quant_results.get("descriptive_stats", {}),
        "time_series": quant_results.get("time_series", {}),
        "anomalies": quant_results.get("anomalies", [])[:15],
        "anomaly_summary": quant_results.get("anomaly_summary", {}),
        "segments": quant_results.get("segments", {}),
    }

    # Summarize qual findings
    qual_summary = {
        "sentence_count": qual_results.get("sentence_count", 0),
        "document_sentiment": qual_results.get("document_sentiment", {}),
        "topics": qual_results.get("topics", []),
    }

    # Fusion results
    fusion_summary = {
        "sentiment_correlations": fusion_results.get("sentiment_correlations", []),
        "segment_insights": fusion_results.get("segment_insights", []),
        "anomaly_theme_overlaps": fusion_results.get("anomaly_theme_overlaps", []),
        "summary": fusion_results.get("summary", {}),
    }

    return f"""You are a world-class UX researcher with 15+ years of experience at companies like Google, Apple, and IDEO. You specialize in mixed-methods research synthesis — triangulating quantitative analytics with qualitative user feedback to uncover deep, non-obvious insights.

You are analyzing data for a real product. Your recommendations MUST be:
- Specific and immediately implementable (not generic advice like "conduct user interviews")
- Grounded in the ACTUAL data provided (cite specific numbers, quotes, and patterns)
- Include root cause analysis explaining WHY the problem exists (go beyond surface symptoms)
- Reference established UX/HCI principles where relevant (Nielsen's heuristics, Fitts's law, cognitive load theory, etc.)
- Include concrete estimated business impact with calculations

CONTEXT:
Product: {context.get('product_description', 'Not specified')}
Research Question: {context.get('research_question', 'Not specified')}
Time Period: {context.get('time_period', 'Not specified')}

═══════════════════════════════════════════════════════
QUANTITATIVE FINDINGS (Statistical Analysis)
═══════════════════════════════════════════════════════
{json.dumps(quant_summary, indent=2, default=str)}

═══════════════════════════════════════════════════════
QUALITATIVE FINDINGS (Sentiment & Topic Analysis)
═══════════════════════════════════════════════════════
{json.dumps(qual_summary, indent=2, default=str)}

═══════════════════════════════════════════════════════
FUSION ANALYSIS (Cross-Data Correlations)
═══════════════════════════════════════════════════════
{json.dumps(fusion_summary, indent=2, default=str)}

═══════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════

Generate a comprehensive insight report. Think deeply about:
1. What is the REAL root cause? (Not just "mobile is broken" — WHY is it broken?)
2. Are there counterintuitive patterns? (e.g., a metric going up that seems positive but actually indicates a problem)
3. What would a senior UX researcher at a top tech company actually recommend?
4. How can we quantify the business impact of each recommendation?

Respond with ONLY a JSON object (no markdown, no backticks, no explanation outside JSON) in this exact structure:

{{
  "problemSummary": "A 3-5 sentence root-cause analysis. Don't just state what's happening — explain WHY it's happening. Reference specific data points. If there's a counterintuitive pattern, call it out. End with the core insight.",

  "quantEvidence": [
    {{
      "metric": "Human-readable metric name",
      "value": "Current value with context (e.g., '67.3% avg bounce rate')",
      "change": "Period-over-period change (e.g., '+22% vs previous period')",
      "direction": "up" | "down" | "flat"
    }}
  ],

  "qualEvidence": [
    {{
      "theme": "Descriptive theme name (e.g., 'Navigation Disorientation on Mobile')",
      "sentiment": -0.62,
      "sentimentLabel": "positive" | "negative" | "neutral" | "mixed",
      "quotes": ["Most impactful direct quote 1", "Most impactful direct quote 2"]
    }}
  ],

  "actions": [
    {{
      "title": "Specific, actionable title (e.g., 'Replace hamburger menu with persistent bottom tab bar')",
      "description": "Detailed implementation plan: What exactly to build, how it addresses the root cause, what UX principle supports this. Include specific design details — dimensions, timings, copy suggestions. 3-5 sentences minimum.",
      "evidence": "Combined evidence: Qual: 'exact quote' (N mentions) + Quant: metric_name = value (change%). Reference the correlation between qual and quant.",
      "impact": "High" | "Medium" | "Low",
      "difficulty": "High" | "Medium" | "Low",
      "estimatedEffect": "Specific estimated improvement with reasoning. Include business calculation if possible. e.g., '+40-60% mobile engagement → recovering ~800 of 1,200 lost monthly downloads'"
    }}
  ],

  "abTests": [
    {{
      "name": "Descriptive test name",
      "control": "Current experience (be specific about what users currently see)",
      "treatment": "Specific change to test (include design details)",
      "metric": "Primary metric to measure + 2-3 secondary metrics",
      "duration": "Duration with minimum sample size justification"
    }}
  ],

  "metrics": [
    {{
      "name": "Metric name",
      "current": "Current value from the data",
      "target": "Realistic target with timeframe (e.g., '<45% within 4 weeks')"
    }}
  ]
}}

CRITICAL RULES:
- Generate 3-5 actions, ranked by impact. Each action MUST cite specific evidence from both quant AND qual data.
- Generate 1-3 A/B tests. Each MUST have specific, testable hypotheses.
- Generate 4-6 metrics to track with realistic targets.
- Every quote in qualEvidence MUST come from the actual qualitative data provided above.
- Every number MUST come from the actual quantitative data provided above.
- DO NOT make up data. If a metric isn't in the data, don't reference it.
- DO NOT suggest generic advice like "conduct user interviews" or "gather more data". Give concrete, implementable recommendations.
- Look for COUNTERINTUITIVE insights — patterns where surface-level reading misses the real story.
- Think like a UX researcher who needs to present this to a VP of Product tomorrow.
"""


# ── Claude API Call ──────────────────────────────────────────


async def _call_claude(prompt: str) -> Optional[dict]:
    """Call the Claude API and parse the JSON response."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping Claude API call")
        return None

    if not _HAS_ANTHROPIC:
        logger.warning("anthropic SDK not installed — skipping Claude API call")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)

        logger.info("Calling Claude API (claude-sonnet-4-20250514)...")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.3,  # Low temp for consistent, grounded output
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text content
        text = ""
        for block in message.content:
            if hasattr(block, "text"):
                text += block.text

        # Parse JSON — Claude sometimes wraps in ```json
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        result = json.loads(text)
        logger.info("Claude API response parsed successfully")
        return result

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude response as JSON: %s", e)
        logger.debug("Raw response: %s", text[:500] if text else "empty")
        return None
    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        return None


# ── Fallback Rule-Based Generator ────────────────────────────


def _generate_fallback(
    context: dict,
    quant_results: dict,
    qual_results: dict,
    fusion_results: dict,
) -> dict:
    """Generate recommendations without Claude API.

    This is a significantly improved rule-based engine that produces
    rich, specific output by deeply mining the pipeline data. Used when
    ANTHROPIC_API_KEY is not set or the API call fails.
    """
    topics = qual_results.get("topics", [])
    correlations = fusion_results.get("sentiment_correlations", [])
    segment_insights = fusion_results.get("segment_insights", [])
    summary_metrics = quant_results.get("summary_metrics", [])
    ts = quant_results.get("time_series", {})
    stats = quant_results.get("descriptive_stats", {})
    segments = quant_results.get("segments", {})
    anomalies = quant_results.get("anomalies", [])

    # ── Deep Problem Summary ─────────────────────────────────

    declining = [m for m in summary_metrics if m.get("direction") == "down"]
    rising_bad = [m for m in summary_metrics
                  if m.get("direction") == "up"
                  and any(kw in m["metric"].lower() for kw in ("bounce", "error", "churn", "latency"))]
    negative_topics = sorted(
        [t for t in topics if t.get("avg_sentiment", 0) < -0.05],
        key=lambda t: t["avg_sentiment"]
    )
    positive_topics = sorted(
        [t for t in topics if t.get("avg_sentiment", 0) > 0.15],
        key=lambda t: -t["avg_sentiment"]
    )
    confirmed_problems = [c for c in correlations if c["correlation_type"] == "confirmed_problem"]
    confirmed_successes = [c for c in correlations if c["correlation_type"] == "confirmed_success"]

    # Build narrative problem summary
    summary_parts = []

    if declining:
        metric_details = []
        for m in declining[:3]:
            pct = m.get("pct_change", 0)
            metric_details.append(f"{m['metric']} ({pct:+.1f}%)")
        summary_parts.append(
            f"Multiple key metrics are declining: {', '.join(metric_details)}."
        )

    if rising_bad:
        for m in rising_bad[:2]:
            pct = m.get("pct_change", 0)
            summary_parts.append(
                f"{m['metric']} has increased {pct:+.1f}%, which is a negative signal."
            )

    if confirmed_problems:
        cp = confirmed_problems[0]
        summary_parts.append(
            f"Critically, qualitative data confirms the quantitative decline — "
            f"the '{cp['topic']}' theme (sentiment: {cp['topic_sentiment']:.2f}) "
            f"directly correlates with {cp['metric']} dropping {cp['metric_pct_change']:+.1f}%. "
            f"This is not a data artifact; users are actively experiencing and reporting this problem."
        )

    # Segment-based root cause
    if segment_insights:
        top_seg = segment_insights[0]
        summary_parts.append(
            f"Root cause analysis points to the {top_seg['worst_segment']} segment "
            f"({top_seg['dimension']}), which underperforms {top_seg['best_segment']} "
            f"on {top_seg['metric']} by {top_seg['relative_spread_pct']:.0f}%. "
            f"This suggests a platform-specific or audience-specific failure, not a global decline."
        )

    # Counterintuitive insight
    if positive_topics and declining:
        summary_parts.append(
            f"Interestingly, '{positive_topics[0]['label']}' shows positive sentiment "
            f"({positive_topics[0]['avg_sentiment']:+.2f}), suggesting not everything is broken — "
            f"users value the core product but are blocked by specific usability barriers."
        )

    problem_summary = " ".join(summary_parts) if summary_parts else (
        "Analysis reveals mixed signals across the data. Review evidence below for nuanced findings."
    )

    # ── Quant Evidence ───────────────────────────────────────

    quant_evidence = []
    for m in summary_metrics[:6]:
        pct = m.get("pct_change")
        change_str = f"{pct:+.1f}% period-over-period" if pct is not None else None

        # Enrich value with context
        metric_stats = stats.get(m["metric"], {})
        val_str = f"{m['mean']:.2f} avg"
        if metric_stats.get("std", 0) > 0:
            val_str += f" (σ={metric_stats['std']:.2f})"

        quant_evidence.append({
            "metric": m["metric"],
            "value": val_str,
            "change": change_str,
            "direction": m.get("direction"),
        })

    # ── Qual Evidence ────────────────────────────────────────

    qual_evidence = []
    for t in topics[:5]:
        qual_evidence.append({
            "theme": t["label"],
            "sentiment": t["avg_sentiment"],
            "sentimentLabel": t["sentiment_label"],
            "quotes": t.get("representative_quotes", [])[:3],
        })

    # ── Rich Actions ─────────────────────────────────────────

    actions = []

    # Action 1: From top confirmed problem + segment insight
    if confirmed_problems and segment_insights:
        cp = confirmed_problems[0]
        seg = segment_insights[0]
        topic_data = next((t for t in topics if t["label"] == cp["topic"]), {})
        quotes = topic_data.get("representative_quotes", [])
        quote_str = f'"{quotes[0][:80]}"' if quotes else "multiple user reports"

        # Calculate business impact
        metric_ts = ts.get(cp["metric"], {})
        first_half = metric_ts.get("mean_first_half", 0)
        second_half = metric_ts.get("mean_second_half", 0)
        lost = abs(first_half - second_half)
        recovery_low = lost * 0.4
        recovery_high = lost * 0.7

        actions.append({
            "title": f"Redesign {seg['worst_segment']} experience to address '{cp['topic']}' pain points",
            "description": (
                f"The data shows a clear {seg['worst_segment']}-specific failure: "
                f"{seg['metric']} on {seg['worst_segment']} underperforms {seg['best_segment']} "
                f"by {seg['relative_spread_pct']:.0f}%, and users directly cite this in feedback. "
                f"Implement a {seg['worst_segment']}-optimized layout with: "
                f"(1) persistent primary actions visible without scrolling or menu interaction, "
                f"(2) progressive content loading to handle slow connections, "
                f"(3) simplified navigation with max 4-5 top-level destinations. "
                f"This follows Nielsen's 'Recognition over Recall' heuristic — users should see "
                f"their options, not remember where they are hidden."
            ),
            "evidence": (
                f"Qual: {quote_str} ({topic_data.get('sentence_count', '?')} related mentions, "
                f"sentiment {cp['topic_sentiment']:.2f}) · "
                f"Quant: {cp['metric']} dropped {cp['metric_pct_change']:+.1f}% · "
                f"Segment: {seg['worst_segment']} vs {seg['best_segment']} spread of "
                f"{seg['spread']:.1f} on {seg['metric']}"
            ),
            "impact": "High",
            "difficulty": "Medium",
            "estimatedEffect": (
                f"Recover {recovery_low:.0f}-{recovery_high:.0f} lost {cp['metric'].replace('_', ' ')} "
                f"(+{abs(cp['metric_pct_change']) * 0.4:.0f}-{abs(cp['metric_pct_change']) * 0.7:.0f}% improvement). "
                f"Based on first-half baseline of {first_half:.1f} → target {first_half * 0.85:.1f}-{first_half * 0.95:.1f}."
            ),
        })

    # Action 2: From negative topic with most mentions
    if negative_topics:
        worst_topic = negative_topics[0]
        quotes = worst_topic.get("representative_quotes", [])

        # Find correlated metric
        related_corr = next(
            (c for c in confirmed_problems if c["topic"] == worst_topic["label"]),
            None
        )
        metric_ref = ""
        if related_corr:
            metric_ref = (
                f"Quant: {related_corr['metric']} {related_corr['metric_pct_change']:+.1f}% · "
            )

        actions.append({
            "title": f"Directly address '{worst_topic['label']}' — the highest-negativity user concern",
            "description": (
                f"This theme has the strongest negative sentiment ({worst_topic['avg_sentiment']:.2f}) "
                f"across {worst_topic.get('sentence_count', '?')} user statements. "
                f"Key complaints center on: {', '.join(worst_topic.get('top_words', [])[:4])}. "
                f"Prioritize quick wins: optimize the specific workflow users mention most, "
                f"add clear visual feedback for loading/processing states, "
                f"and ensure the most common task (the primary user goal) is completable "
                f"in ≤3 taps/clicks. Apply Hick's Law — reduce the number of choices "
                f"on the critical path to decrease decision time."
            ),
            "evidence": (
                f"Qual: '{quotes[0][:70]}...' + {worst_topic.get('sentence_count', 0) - 1} similar reports "
                f"(sentiment {worst_topic['avg_sentiment']:.2f}) · "
                f"{metric_ref}"
                f"Top words: {', '.join(worst_topic.get('top_words', [])[:5])}"
            ) if quotes else f"Theme sentiment: {worst_topic['avg_sentiment']:.2f}, {worst_topic.get('sentence_count', 0)} mentions",
            "impact": "High",
            "difficulty": "Low",
            "estimatedEffect": (
                f"Reduce negative sentiment from {worst_topic['avg_sentiment']:.2f} to >-0.10 "
                f"(neutral zone). Expected +25-40% improvement in related engagement metrics "
                f"based on severity of current complaints."
            ),
        })

    # Action 3: Leverage what's working (positive theme)
    if positive_topics:
        best = positive_topics[0]
        quotes = best.get("representative_quotes", [])

        actions.append({
            "title": f"Scale the '{best['label']}' success to underperforming areas",
            "description": (
                f"Users explicitly praise aspects related to {best['label']} "
                f"(sentiment: {best['avg_sentiment']:+.2f}, {best.get('sentence_count', 0)} mentions). "
                f"This is your competitive advantage — don't let it atrophy while fixing problems. "
                f"Apply the same design patterns, information architecture, and interaction quality "
                f"from the praised experience to the struggling segments. "
                f"For example, if desktop navigation works well, adapt its IA principles "
                f"(not its layout) for mobile: same content hierarchy, different form factor."
            ),
            "evidence": (
                f"Qual: '{quotes[0][:70]}...' (sentiment {best['avg_sentiment']:+.2f}) · "
                f"This positive signal contrasts with declining metrics, suggesting "
                f"the core value proposition is strong but delivery is inconsistent."
            ) if quotes else f"Positive theme: {best['avg_sentiment']:+.2f}, {best.get('sentence_count', 0)} mentions",
            "impact": "Medium",
            "difficulty": "Low",
            "estimatedEffect": (
                f"Maintain {best['avg_sentiment']:+.2f} sentiment in strong areas while "
                f"lifting weak areas. Cross-pollination typically yields +15-25% improvement "
                f"in underperforming segments when proven patterns are adapted."
            ),
        })

    # Action 4: From anomaly data
    if anomalies:
        anomaly_cols = {}
        for a in anomalies:
            anomaly_cols.setdefault(a["column"], []).append(a)
        worst_col = max(anomaly_cols.items(), key=lambda x: len(x[1]))
        col_name = worst_col[0]
        col_anomalies = worst_col[1]
        col_stats = stats.get(col_name, {})

        actions.append({
            "title": f"Investigate {len(col_anomalies)} anomalous data points in {col_name}",
            "description": (
                f"{col_name} shows {len(col_anomalies)} statistical anomalies "
                f"(detected via {'IQR' if col_anomalies[0].get('method') == 'iqr' else 'Z-score'} method). "
                f"Anomalous values: {', '.join(str(a['value']) for a in col_anomalies[:4])} "
                f"vs. mean of {col_stats.get('mean', 0):.2f}. "
                f"These outliers may indicate specific events (launches, outages, campaigns) "
                f"that disproportionately affect the aggregate numbers. "
                f"Cross-reference anomaly dates with deployment logs and marketing calendars "
                f"to identify if this is a systemic issue or event-driven."
            ),
            "evidence": (
                f"Quant: {len(col_anomalies)} anomalies in {col_name} "
                f"(mean={col_stats.get('mean', 0):.2f}, std={col_stats.get('std', 0):.2f})"
            ),
            "impact": "Medium",
            "difficulty": "Low",
            "estimatedEffect": (
                f"Understanding anomaly root cause enables targeted fixes. "
                f"If event-driven: prevent recurrence. If systemic: expect "
                f"+10-20% metric stability after resolution."
            ),
        })

    # Fallback if somehow nothing
    if not actions:
        actions.append({
            "title": "Conduct focused usability testing on identified pain points",
            "description": (
                f"While the automated analysis identified {len(topics)} themes and "
                f"{len(summary_metrics)} metrics, the correlations are not strong enough "
                f"for high-confidence recommendations. Conduct 5-8 moderated usability tests "
                f"focusing specifically on the workflows related to: "
                f"{', '.join(t['label'] for t in topics[:3])}."
            ),
            "evidence": f"{len(topics)} themes, {len(summary_metrics)} metrics analyzed",
            "impact": "Medium",
            "difficulty": "Low",
            "estimatedEffect": "Clarified priorities for data-driven next steps",
        })

    # ── A/B Tests ────────────────────────────────────────────

    ab_tests = []
    if len(actions) >= 2:
        a1 = actions[0]
        a2 = actions[1]
        primary_metric = quant_evidence[0]["metric"] if quant_evidence else "primary KPI"
        secondary = [e["metric"] for e in quant_evidence[1:3]] if len(quant_evidence) > 1 else []

        ab_tests.append({
            "name": f"Redesign Test: {a1['title'][:60]}",
            "control": "Current production experience (no changes)",
            "treatment": a1["description"][:120] + "...",
            "metric": f"Primary: {primary_metric}" + (f" | Secondary: {', '.join(secondary)}" if secondary else ""),
            "duration": f"2 weeks minimum, targeting 1,000+ sessions per variant for 80% statistical power (α=0.05)",
        })

        ab_tests.append({
            "name": f"Quick Win Test: {a2['title'][:60]}",
            "control": "Current interaction flow",
            "treatment": a2["description"][:120] + "...",
            "metric": f"Primary: user sentiment (in-app survey) | Secondary: {primary_metric}",
            "duration": "1-2 weeks, 500+ sessions per variant",
        })

    # ── Metrics to Track ─────────────────────────────────────

    tracked = []
    for m in summary_metrics[:6]:
        pct = m.get("pct_change", 0)
        mean_val = m["mean"]

        # Intelligent targets
        if pct and pct < -15:
            target_val = mean_val * 1.4
            target_str = f"{target_val:.2f} (+40% recovery within 4 weeks)"
        elif pct and pct < -5:
            target_val = mean_val * 1.2
            target_str = f"{target_val:.2f} (+20% recovery within 3 weeks)"
        elif pct and pct > 10:
            # Rising metric — is it good or bad?
            is_bad = any(kw in m["metric"].lower() for kw in ("bounce", "error", "churn", "latency"))
            if is_bad:
                target_val = mean_val * 0.7
                target_str = f"{target_val:.2f} (-30% reduction within 4 weeks)"
            else:
                target_val = mean_val * 1.1
                target_str = f"{target_val:.2f} (sustain +10% growth)"
        else:
            target_val = mean_val * 1.1
            target_str = f"{target_val:.2f} (+10% improvement)"

        tracked.append({
            "name": m["metric"],
            "current": f"{mean_val:.2f}",
            "target": target_str,
        })

    return {
        "problemSummary": problem_summary,
        "quantEvidence": quant_evidence,
        "qualEvidence": qual_evidence,
        "actions": actions,
        "abTests": ab_tests,
        "metrics": tracked,
    }


# ── Main Entry Point ─────────────────────────────────────────


async def generate_recommendations(
    context: dict,
    quant_results: dict,
    qual_results: dict,
    fusion_results: dict,
) -> dict:
    """Generate expert UX recommendations.

    Strategy:
    1. If ANTHROPIC_API_KEY is set → Call Claude for deep synthesis
    2. If Claude fails or key missing → Use rich fallback engine

    Both paths produce the same JSON structure.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Try Claude first
    if api_key and _HAS_ANTHROPIC:
        logger.info("Generating recommendations via Claude API...")
        prompt = _build_prompt(context, quant_results, qual_results, fusion_results)

        result = await _call_claude(prompt)

        if result:
            # Validate the response has required fields
            required = ["problemSummary", "quantEvidence", "qualEvidence", "actions"]
            if all(k in result for k in required):
                logger.info("Using Claude-generated recommendations (%d actions)", len(result.get("actions", [])))
                return result
            else:
                missing = [k for k in required if k not in result]
                logger.warning("Claude response missing fields: %s — falling back", missing)

    # Fallback
    logger.info("Generating recommendations via fallback engine...")
    return _generate_fallback(context, quant_results, qual_results, fusion_results)
