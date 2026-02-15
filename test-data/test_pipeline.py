#!/usr/bin/env python3
"""End-to-end test of the Normate AI analysis pipeline.

Runs: Quant Processor → Qual Processor → Fusion Engine → Recommendations
On the test data files, with full output.
"""

import asyncio
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.quant_processor import process_quant_files
from services.qual_processor import process_qual_files
from services.fusion_engine import fuse_findings
from services.claude_service import generate_recommendations


def section(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


async def main():
    test_dir = os.path.dirname(__file__)

    # ── Load test files ──────────────────────────────────────

    csv_path = os.path.join(test_dir, "bulletin_analytics.csv")
    txt_path = os.path.join(test_dir, "user_feedback.txt")

    with open(csv_path, "rb") as f:
        csv_bytes = f.read()
    with open(txt_path, "rb") as f:
        txt_bytes = f.read()

    # ── Step 1: Quant Processing ─────────────────────────────

    section("STEP 1: QUANTITATIVE PROCESSING")
    quant = await process_quant_files([("bulletin_analytics.csv", csv_bytes)])

    print(f"\nRows: {quant['row_count']}")
    print(f"Columns detected:")
    cc = quant["column_classification"]
    print(f"  Dates:      {cc['date_cols']}")
    print(f"  Metrics:    {cc['metric_cols']}")
    print(f"  Dimensions: {cc['dimension_cols']}")

    print(f"\nDescriptive Statistics:")
    for col, stats in quant["descriptive_stats"].items():
        print(f"  {col}: mean={stats['mean']:.2f}, median={stats['median']:.2f}, "
              f"std={stats['std']:.2f}, range=[{stats['min']:.2f}, {stats['max']:.2f}]")

    print(f"\nAnomalies Detected: {len(quant['anomalies'])}")
    for a in quant["anomalies"][:8]:
        print(f"  [{a['method'].upper()}] {a['column']} row {a['row_index']}: "
              f"value={a['value']}, score={a['score']:.2f}")

    if quant["time_series"]:
        print(f"\nTime-Series Analysis:")
        for col, ts in quant["time_series"].items():
            print(f"  {col}: {ts['pct_change']:+.1f}% ({ts['direction']}) "
                  f"| 1st half mean={ts['mean_first_half']:.2f}, "
                  f"2nd half mean={ts['mean_second_half']:.2f}")

    if quant["segments"]:
        print(f"\nSegment Analysis:")
        for dim, metrics in quant["segments"].items():
            for met, data in metrics.items():
                print(f"  {dim} × {met}: best={data['best']}, worst={data['worst']}, "
                      f"spread={data['spread']:.2f}")

    # ── Step 2: Qual Processing ──────────────────────────────

    section("STEP 2: QUALITATIVE PROCESSING")
    qual = await process_qual_files([("user_feedback.txt", txt_bytes)])

    print(f"\nSentences analyzed: {qual['sentence_count']}")
    doc_sent = qual["document_sentiment"]
    print(f"Document sentiment: {doc_sent['compound']:.4f} ({doc_sent['label']})")
    dist = doc_sent["distribution"]
    print(f"Distribution: {dist['positive']} positive, {dist['negative']} negative, "
          f"{dist['neutral']} neutral")

    print(f"\nTopics Extracted: {len(qual['topics'])}")
    for t in qual["topics"]:
        print(f"\n  Topic: {t['label']}")
        print(f"  Sentiment: {t['avg_sentiment']:.4f} ({t['sentiment_label']})")
        print(f"  Sentences: {t['sentence_count']}")
        print(f"  Top words: {', '.join(t['top_words'][:5])}")
        for q in t["representative_quotes"][:2]:
            print(f"    → \"{q[:90]}{'...' if len(q) > 90 else ''}\"")

    # ── Step 3: Fusion ───────────────────────────────────────

    section("STEP 3: DATA FUSION")
    fusion = await fuse_findings(quant, qual)

    print(f"\nFusion Summary:")
    s = fusion["summary"]
    print(f"  Confirmed problems: {s['confirmed_problems']}")
    print(f"  Confirmed successes: {s['confirmed_successes']}")
    print(f"  Divergent signals: {s['divergent_signals']}")
    print(f"  Segment insights: {s['segment_insights_count']}")

    if fusion["sentiment_correlations"]:
        print(f"\nSentiment-Metric Correlations:")
        for c in fusion["sentiment_correlations"][:5]:
            print(f"  [{c['strength'].upper()}] {c['correlation_type']}: "
                  f"'{c['topic']}' (sent={c['topic_sentiment']:.2f}) ↔ "
                  f"{c['metric']} ({c['metric_pct_change']:+.1f}%)")

    if fusion["segment_insights"]:
        print(f"\nSegment Insights:")
        for si in fusion["segment_insights"][:3]:
            print(f"  {si['dimension']}: {si['worst_segment']} underperforms "
                  f"{si['best_segment']} on {si['metric']} by {si['relative_spread_pct']:.0f}%")

    # ── Step 4: Recommendations ──────────────────────────────

    section("STEP 4: RECOMMENDATIONS")
    recs = await generate_recommendations(
        context={
            "research_question": "Why did mobile engagement drop after the Q1 redesign?",
            "product_description": "Agricultural bulletin web platform for East African crop forecasting",
            "time_period": "Jan-Mar 2025",
        },
        quant_results=quant,
        qual_results=qual,
        fusion_results=fusion,
    )

    print(f"\nProblem Summary:\n  {recs['problemSummary']}")

    print(f"\nQuant Evidence ({len(recs['quantEvidence'])} items):")
    for e in recs["quantEvidence"]:
        change = f" ({e['change']})" if e.get("change") else ""
        print(f"  • {e['metric']}: {e['value']}{change}")

    print(f"\nQual Evidence ({len(recs['qualEvidence'])} items):")
    for e in recs["qualEvidence"]:
        print(f"  • {e['theme']}: sentiment={e['sentiment']:.2f} ({e['sentimentLabel']})")

    print(f"\nActions ({len(recs['actions'])}):")
    for i, a in enumerate(recs["actions"], 1):
        print(f"\n  {i}. {a['title']}")
        print(f"     Impact: {a['impact']} | Difficulty: {a['difficulty']}")
        print(f"     Effect: {a['estimatedEffect']}")
        print(f"     Evidence: {a['evidence']}")

    if recs["abTests"]:
        print(f"\nA/B Tests:")
        for ab in recs["abTests"]:
            print(f"  • {ab['name']}")

    print(f"\nMetrics to Track:")
    for m in recs["metrics"]:
        print(f"  • {m['name']}: {m['current']} → {m['target']}")

    section("PIPELINE COMPLETE ✅")
    print(f"\nTotal output size: {len(json.dumps(recs)):,} chars")
    print("All 4 pipeline stages executed successfully.\n")


if __name__ == "__main__":
    asyncio.run(main())
