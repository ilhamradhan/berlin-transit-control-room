"""Small, citation-preserving retrieval for the local Stage 4 demo."""

from __future__ import annotations

import re
from typing import Iterable

_TOKEN = re.compile(r"[a-z0-9]{3,}")
_FORBIDDEN = re.compile(r"(?:api[_ -]?key|secret|password|/home/|/etc/|duckdb|parquet)", re.I)
_STOPWORDS = {"the", "and", "for", "from", "what", "how", "does", "this", "that", "with"}
_ALLOWED_SECTIONS = {
    "ARCHITECTURE.md": {"Versioned publication"},
    "EVALUATION.md": {"Stage 4 static product"},
    "04-static-dashboard-rag.md": {"Red line"},
}
_APPROVED_TEXT = {
    ("ARCHITECTURE.md", "Versioned publication"): "The verified release is reopened read-only before compact public aggregates are built.",
    ("EVALUATION.md", "Stage 4 static product"): "The dashboard distinguishes prediction observations from actual arrivals and shows coverage caveats.",
    ("04-static-dashboard-rag.md", "Red line"): "Stage 4 is a finite static public evidence product, not an operational system.",
}


def build_corpus(documents: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    corpus = []
    for document in documents:
        if set(document) != {"source", "section", "text"}:
            raise ValueError("corpus entries must contain source, section, and text only")
        if not all(isinstance(value, str) and value.strip() for value in document.values()):
            raise ValueError("corpus fields must be non-empty strings")
        if document["section"] not in _ALLOWED_SECTIONS.get(document["source"], set()) or document["text"] != _APPROVED_TEXT.get((document["source"], document["section"])) or _FORBIDDEN.search(" ".join(document.values())):
            raise ValueError("corpus contains forbidden operational content")
        corpus.append(dict(document))
    return corpus


def retrieve(query: str, corpus: list[dict[str, str]], limit: int = 3) -> dict[str, object]:
    corpus = build_corpus(corpus)
    terms = {term for term in _TOKEN.findall(query.lower()) if term not in _STOPWORDS}
    ranked = []
    for passage in corpus:
        haystack = f"{passage['section']} {passage['text']}".lower()
        score = sum(term in haystack for term in terms)
        if score:
            ranked.append((score, passage))
    ranked.sort(key=lambda item: (-item[0], item[1]["source"], item[1]["section"]))
    selected = [passage for _, passage in ranked[:limit]]
    if not selected:
        return {"status": "insufficient", "citations": [], "passages": []}
    return {
        "status": "supported",
        "citations": [{"source": p["source"], "section": p["section"]} for p in selected],
        "passages": selected,
    }
