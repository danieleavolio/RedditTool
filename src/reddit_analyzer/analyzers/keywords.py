"""Distinctive words by TF-IDF, one document per post. Pure Python, no dependencies."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from reddit_analyzer.analyzers.base import Analyzer
from reddit_analyzer.storage import Database
from reddit_analyzer.text import post_text, words

TOP = 30


class KeywordsAnalyzer(Analyzer):
    name = "keywords"
    description = "Words that characterize the collection (TF-IDF over posts)."

    def run(self, db: Database, collection: str | None) -> dict[str, Any]:
        docs = [words(post_text(p)) for p in db.iter_posts(collection=collection)]
        docs = [d for d in docs if d]
        frequency: Counter[str] = Counter()  # in how many posts each word appears
        for doc in docs:
            frequency.update(set(doc))
        score: Counter[str] = Counter()
        for doc in docs:
            for word, n in Counter(doc).items():
                idf = math.log((1 + len(docs)) / (1 + frequency[word])) + 1  # smoothed
                score[word] += n / len(doc) * idf
        ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP]
        return {
            "documents": len(docs),
            "keywords": [
                {"term": t, "score": round(s, 4), "documents": frequency[t]} for t, s in ranked
            ],
        }

    def summary(self, data: dict[str, Any]) -> str:
        if not data["keywords"]:
            return "No keywords."
        return f"{data['documents']} posts: " + ", ".join(k["term"] for k in data["keywords"][:12])
