"""Qualitative data processor — text analysis pipeline.

Algorithms implemented:
─────────────────────
1. Text parsing: TXT and DOCX file reading
2. Preprocessing: sentence tokenization, cleaning, stopword removal
3. Sentiment analysis:
   - VADER (Valence Aware Dictionary and sEntiment Reasoner)
   - Sentence-level + document-level scoring
4. Topic extraction:
   - TF-IDF vectorization + NMF (Non-negative Matrix Factorization)
   - Lighter alternative to BERTopic — no GPU needed, runs in <5s
5. Theme clustering: group sentences by topic, extract representative quotes
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


# ── Lightweight Sentiment Analyzer (VADER-compatible) ────────
# When vaderSentiment is installed, we use it. Otherwise, fall back
# to a lexicon-based approach using the same scoring methodology.

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as _VaderAnalyzer
    _USE_VADER = True
except ImportError:
    _USE_VADER = False
    logger.info("vaderSentiment not installed — using built-in lexicon fallback")


# Curated sentiment lexicon: word → valence score [-4, +4]
# Based on the same methodology as VADER's human-rated lexicon.
_LEXICON: dict[str, float] = {
    # Strong negative
    "broken": -2.8, "unusable": -3.2, "terrible": -3.4, "horrible": -3.1,
    "worst": -3.0, "frustrating": -2.6, "frustrated": -2.6, "unbearable": -3.0,
    "impossible": -2.5, "failure": -2.8, "failed": -2.5, "bug": -2.2,
    "crash": -2.8, "crashed": -2.8, "angry": -2.5, "hate": -3.2,
    "awful": -3.1, "poor": -2.0, "slow": -1.8, "confusing": -2.2,
    "confused": -2.0, "difficult": -1.8, "problem": -2.0, "problems": -2.0,
    "issue": -1.5, "issues": -1.5, "concern": -1.3, "concerns": -1.3,
    "complaint": -1.8, "complaints": -1.8, "dropped": -1.5, "decline": -1.5,
    "declined": -1.5, "decrease": -1.2, "lost": -1.5, "worse": -2.2,
    "bad": -2.5, "wrong": -2.0, "error": -2.2, "errors": -2.2,
    "ugly": -2.5, "boring": -2.0, "annoying": -2.2, "disappointed": -2.3,
    "stopped": -1.5, "defeats": -1.8, "buried": -1.5, "hidden": -1.3,
    "blank": -1.8, "heavy": -1.2, "heavier": -1.3, "urgent": -1.0,
    # Mild negative
    "hard": -1.2, "complicated": -1.5, "lacking": -1.2, "missing": -1.3,
    "negative": -1.5, "tiny": -1.0, "small": -0.5,
    # Strong positive
    "excellent": 3.2, "fantastic": 3.2, "wonderful": 3.2, "amazing": 3.1,
    "outstanding": 3.0, "brilliant": 3.0, "perfect": 3.0, "perfectly": 3.0,
    "love": 2.8, "loved": 2.8, "great": 2.5, "beautiful": 2.8,
    "impressive": 2.5, "impressed": 2.5, "best": 2.8, "superior": 2.2,
    "essential": 1.8, "valuable": 2.0, "intuitive": 2.2,
    # Moderate positive
    "good": 1.8, "nice": 1.5, "fine": 1.0, "clean": 1.5, "professional": 1.8,
    "improved": 1.8, "improvements": 1.5, "improvement": 1.5,
    "easy": 1.5, "easier": 1.8, "simple": 1.2, "simpler": 1.5,
    "fast": 1.5, "faster": 1.8, "quick": 1.3, "smooth": 1.5,
    "helpful": 2.0, "useful": 1.8, "informative": 1.8, "comprehensive": 1.5,
    "reliable": 1.8, "solid": 1.3, "appreciate": 2.0, "appreciated": 2.0,
    "positive": 1.5, "well": 1.2, "works": 1.0, "sound": 1.2,
    # Boosters & negators
    "very": 0.0, "extremely": 0.0, "really": 0.0, "much": 0.0,
    "not": 0.0, "no": 0.0, "never": 0.0, "cannot": 0.0,
}

_NEGATORS = {"not", "no", "never", "cannot", "cant", "don", "doesn", "didn",
             "won", "wouldn", "shouldn", "couldn", "isn", "aren", "wasn"}
_BOOSTERS = {"very", "extremely", "really", "incredibly", "absolutely",
             "particularly", "especially", "significantly", "definitely", "much"}


class _BuiltinSentimentAnalyzer:
    """Lightweight VADER-style sentiment analyzer using curated lexicon."""

    def polarity_scores(self, text: str) -> dict:
        words = re.findall(r"[a-z']+", text.lower())
        if not words:
            return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}

        sentiments = []
        for i, word in enumerate(words):
            val = _LEXICON.get(word, 0.0)
            if val == 0.0:
                continue

            # Check for negation in preceding 3 words
            prev_words = words[max(0, i - 3):i]
            if any(w in _NEGATORS for w in prev_words):
                val *= -0.75

            # Check for boosters
            if any(w in _BOOSTERS for w in prev_words):
                val *= 1.25 if val > 0 else 1.15

            sentiments.append(val)

        if not sentiments:
            return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}

        # Normalize compound: same formula as VADER
        raw_sum = sum(sentiments)
        compound = raw_sum / ((raw_sum ** 2 + 15) ** 0.5)
        compound = max(-1.0, min(1.0, compound))

        pos_sum = sum(s for s in sentiments if s > 0)
        neg_sum = sum(abs(s) for s in sentiments if s < 0)
        total = pos_sum + neg_sum + 1e-6

        pos = round(pos_sum / total, 3)
        neg = round(neg_sum / total, 3)
        neu = round(1.0 - pos - neg, 3)

        return {"compound": round(compound, 4), "pos": pos, "neg": neg, "neu": max(0, neu)}


def _get_analyzer():
    """Return VADER if available, else built-in fallback."""
    if _USE_VADER:
        return _VaderAnalyzer()
    return _BuiltinSentimentAnalyzer()

# ── Text Parsing ─────────────────────────────────────────────


def parse_txt(content: bytes) -> str:
    """Parse plain text file."""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def parse_docx(content: bytes) -> str:
    """Parse DOCX file by extracting text from XML paragraphs.

    Uses zipfile + XML parsing — no external docx library needed.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            with zf.open("word/document.xml") as doc:
                tree = ET.parse(doc)
                root = tree.getroot()

                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = []
                for para in root.iter(f"{{{ns['w']}}}p"):
                    texts = [t.text for t in para.iter(f"{{{ns['w']}}}t") if t.text]
                    if texts:
                        paragraphs.append("".join(texts))

                return "\n".join(paragraphs)
    except Exception as e:
        logger.error("DOCX parse error: %s", e)
        return ""


# ── Text Preprocessing ───────────────────────────────────────

# Simple sentence splitter (avoids NLTK download dependency)
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'(])')

STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she",
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that",
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an",
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of",
    "at", "by", "for", "with", "about", "against", "between", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will",
    "just", "don", "should", "now", "also", "would", "could", "might",
}


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, filtering out very short fragments."""
    raw = SENTENCE_SPLIT.split(text.strip())
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 15:  # ignore fragments < 15 chars
            sentences.append(s)
    return sentences


def clean_text(text: str) -> str:
    """Lowercase, strip extra whitespace, remove special chars for TF-IDF."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── VADER Sentiment Analysis ─────────────────────────────────


@dataclass
class SentimentResult:
    text: str
    compound: float   # -1.0 to +1.0
    pos: float
    neg: float
    neu: float


def analyze_sentiment(sentences: list[str]) -> list[SentimentResult]:
    """Run sentiment analysis on each sentence.

    Uses VADER if installed, otherwise a built-in lexicon analyzer
    with the same scoring methodology (compound score [-1, +1]).
    """
    analyzer = _get_analyzer()
    results = []
    for sent in sentences:
        scores = analyzer.polarity_scores(sent)
        results.append(SentimentResult(
            text=sent,
            compound=scores["compound"],
            pos=scores["pos"],
            neg=scores["neg"],
            neu=scores["neu"],
        ))
    return results


def classify_sentiment(compound: float) -> str:
    """Map compound score to label."""
    if compound >= 0.3:
        return "positive"
    elif compound <= -0.3:
        return "negative"
    elif abs(compound) <= 0.1:
        return "neutral"
    else:
        return "mixed"


# ── Topic Extraction (TF-IDF + NMF) ─────────────────────────


@dataclass
class Topic:
    topic_id: int
    label: str               # auto-generated from top words
    top_words: list[str]
    sentence_indices: list[int]
    representative_quotes: list[str]
    avg_sentiment: float
    sentiment_label: str


def extract_topics(
    sentences: list[str],
    sentiment_results: list[SentimentResult],
    n_topics: int = 5,
    top_n_words: int = 6,
    max_quotes_per_topic: int = 3,
) -> list[Topic]:
    """Extract topics using TF-IDF + NMF.

    Algorithm:
    1. TF-IDF: Convert sentences to term frequency–inverse document frequency
       vectors. High TF-IDF = word is important in this sentence but rare overall.
    2. NMF (Non-negative Matrix Factorization): Factorize the TF-IDF matrix
       V ≈ W × H where:
       - W = document-topic matrix (which topics each sentence belongs to)
       - H = topic-term matrix (which words define each topic)
    3. Assign each sentence to its strongest topic.
    4. Pick representative quotes: highest-sentiment-magnitude sentences per topic.

    NMF vs BERTopic tradeoff:
    - NMF: ~0.5s, no GPU, good enough for <1000 sentences
    - BERTopic: ~15-30s, better semantic understanding, needs more RAM
    We use NMF for MVP speed; BERTopic can be swapped in later.
    """
    if len(sentences) < 3:
        # Not enough data for topic modeling
        return [Topic(
            topic_id=0, label="General Feedback",
            top_words=[], sentence_indices=list(range(len(sentences))),
            representative_quotes=[s.text for s in sentiment_results[:max_quotes_per_topic]],
            avg_sentiment=np.mean([s.compound for s in sentiment_results]) if sentiment_results else 0,
            sentiment_label=classify_sentiment(
                np.mean([s.compound for s in sentiment_results]) if sentiment_results else 0
            ),
        )]

    # Adjust n_topics to data size
    n_topics = min(n_topics, max(2, len(sentences) // 3))

    # TF-IDF vectorization
    cleaned = [clean_text(s) for s in sentences]
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words=list(STOPWORDS),
        min_df=1,
        max_df=0.9,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(cleaned)
    except ValueError:
        # All documents are empty after preprocessing
        return []

    if tfidf_matrix.shape[1] < n_topics:
        n_topics = max(2, tfidf_matrix.shape[1])

    # NMF decomposition
    nmf = NMF(n_components=n_topics, random_state=42, max_iter=300)
    W = nmf.fit_transform(tfidf_matrix)  # (n_sentences, n_topics)
    H = nmf.components_                   # (n_topics, n_features)

    feature_names = vectorizer.get_feature_names_out()

    # Assign each sentence to its dominant topic
    topic_assignments = W.argmax(axis=1)

    topics = []
    for topic_idx in range(n_topics):
        # Top words for this topic
        top_word_indices = H[topic_idx].argsort()[-top_n_words:][::-1]
        top_words = [feature_names[i] for i in top_word_indices]

        # Sentences in this topic
        sent_indices = [i for i, t in enumerate(topic_assignments) if t == topic_idx]
        if not sent_indices:
            continue

        # Sentiment for this topic
        topic_sentiments = [sentiment_results[i].compound for i in sent_indices]
        avg_sent = float(np.mean(topic_sentiments))

        # Representative quotes: pick most extreme sentiment sentences
        sorted_by_magnitude = sorted(
            sent_indices, key=lambda i: abs(sentiment_results[i].compound), reverse=True
        )
        quotes = [sentences[i] for i in sorted_by_magnitude[:max_quotes_per_topic]]

        # Auto-label from top 2-3 words
        label_words = [w.replace("_", " ").title() for w in top_words[:3]]
        label = " / ".join(label_words)

        topics.append(Topic(
            topic_id=topic_idx,
            label=label,
            top_words=top_words,
            sentence_indices=sent_indices,
            representative_quotes=quotes,
            avg_sentiment=round(avg_sent, 4),
            sentiment_label=classify_sentiment(avg_sent),
        ))

    # Sort by absolute sentiment (most polarized first = most actionable)
    topics.sort(key=lambda t: abs(t.avg_sentiment), reverse=True)
    return topics


# ── Main Entry Point ─────────────────────────────────────────


async def process_qual_files(file_contents: list[tuple[str, bytes]]) -> dict:
    """Process uploaded qualitative data files end-to-end.

    Args:
        file_contents: List of (filename, raw_bytes) tuples.

    Returns:
        Structured dict with sentences, sentiment, topics, and document stats.
    """
    all_text = []

    for filename, content in file_contents:
        try:
            if filename.endswith(".txt"):
                text = parse_txt(content)
            elif filename.endswith((".docx", ".doc")):
                text = parse_docx(content)
            else:
                continue
            all_text.append(text)
            logger.info("Parsed %s: %d chars", filename, len(text))
        except Exception as e:
            logger.error("Failed to parse %s: %s", filename, e)

    if not all_text:
        return {"error": "No valid qualitative data files could be parsed."}

    combined = "\n\n".join(all_text)
    sentences = split_sentences(combined)

    if not sentences:
        return {"error": "No analyzable sentences found in the uploaded text."}

    logger.info("Extracted %d sentences for analysis", len(sentences))

    # Sentiment analysis
    sentiment_results = analyze_sentiment(sentences)

    # Document-level sentiment
    all_compounds = [s.compound for s in sentiment_results]
    doc_sentiment = float(np.mean(all_compounds))

    # Sentiment distribution
    positive_count = sum(1 for c in all_compounds if c >= 0.3)
    negative_count = sum(1 for c in all_compounds if c <= -0.3)
    neutral_count = len(all_compounds) - positive_count - negative_count

    # Topic extraction
    topics = extract_topics(sentences, sentiment_results)

    # Build output
    return {
        "sentence_count": len(sentences),
        "document_sentiment": {
            "compound": round(doc_sentiment, 4),
            "label": classify_sentiment(doc_sentiment),
            "distribution": {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count,
            },
        },
        "topics": [
            {
                "topic_id": t.topic_id,
                "label": t.label,
                "top_words": t.top_words,
                "sentence_count": len(t.sentence_indices),
                "representative_quotes": t.representative_quotes,
                "avg_sentiment": t.avg_sentiment,
                "sentiment_label": t.sentiment_label,
            }
            for t in topics
        ],
        "all_sentiments": [
            {
                "text": sr.text,
                "compound": round(sr.compound, 4),
                "label": classify_sentiment(sr.compound),
            }
            for sr in sentiment_results
        ],
    }
