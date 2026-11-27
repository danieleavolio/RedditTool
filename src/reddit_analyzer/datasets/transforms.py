"""Text cleaning and de-duplication. Everything here is deterministic."""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Sequence

from reddit_analyzer.datasets.recipe import Transform

# -- cleaning ---------------------------------------------------------------------------

_PAREN_URL = re.compile(r"\((?:https?://|www\.)[^\s()]*\)")
_URL = re.compile(
    r"(?:https?://|www\.)[^\s<>\[\]()]*[^\s<>\[\]().,;:!?'\"]"
)  # keeps trailing punctuation
_USERNAME = re.compile(r"(?<![\w/])/?u/[A-Za-z0-9_-]{3,20}")

_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_FENCE = re.compile(r"^\s*(?:```|~~~)[^\n]*$", re.MULTILINE)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_QUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)
_RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
_SPOILER = re.compile(r">!(.+?)!<", re.DOTALL)
_BOLD_ITALIC = re.compile(r"(?<![\w*])(\*{1,3})(?=\S)(.+?)(?<=\S)\1(?![\w*])", re.DOTALL)
_UNDERSCORE = re.compile(r"(?<![\w_])(_{1,3})(?=\S)(.+?)(?<=\S)\1(?![\w_])", re.DOTALL)
_STRIKE = re.compile(r"~~(.+?)~~", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>~|])")

_SPACES = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")


def strip_urls(text: str) -> str:
    return _URL.sub("", _PAREN_URL.sub("", text))


def strip_usernames(text: str) -> str:
    return _USERNAME.sub("", text)


def strip_markdown(text: str) -> str:
    """Remove Reddit markdown but keep the words: links keep their label, code its content."""
    text = _IMAGE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _FENCE.sub("", text)
    text = _HEADING.sub("", text)
    text = _QUOTE.sub("", text)
    text = _RULE.sub("", text)
    text = _BULLET.sub("", text)
    text = _SPOILER.sub(r"\1", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _STRIKE.sub(r"\1", text)
    text = _BOLD_ITALIC.sub(r"\2", text)
    text = _UNDERSCORE.sub(r"\2", text)
    return _ESCAPE.sub(r"\1", text)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANKS.sub("\n\n", text).strip()


class Cleaner:
    def __init__(self, transform: Transform):
        self._steps = []
        # markdown first: it unwraps [label](url), so the url step finds nothing half-eaten
        if "markdown" in transform.strip:
            self._steps.append(strip_markdown)
        if "urls" in transform.strip:
            self._steps.append(strip_urls)
        if "usernames" in transform.strip:
            self._steps.append(strip_usernames)
        if transform.normalize_whitespace:
            self._steps.append(normalize_whitespace)

    def __call__(self, text: str) -> str:
        for step in self._steps:
            text = step(text)
        return text


# -- de-duplication ---------------------------------------------------------------------


def _canonical(text: str) -> str:
    return " ".join(text.lower().split())


class ExactDeduper:
    """Keeps the first row of every distinct text (case and spacing do not matter)."""

    def __init__(self) -> None:
        self._seen: set[bytes] = set()

    def is_duplicate(self, text: str) -> bool:
        digest = hashlib.blake2b(_canonical(text).encode(), digest_size=16).digest()
        if digest in self._seen:
            return True
        self._seen.add(digest)
        return False


_PRIME = (1 << 61) - 1
_SHINGLE = 5  # words per shingle
_PERMS = 64
_BANDS = 16  # 16 bands x 4 rows: texts ~80% similar collide in some band most of the time


class NearDeduper:
    """MinHash + LSH. Two texts are near-duplicates when the estimated Jaccard similarity of
    their word 5-grams reaches ``threshold``. Pure Python: fine for a local tool."""

    def __init__(self, threshold: float):
        self._threshold = threshold
        rng = random.Random(0x5EED)
        self._coeffs = [(rng.randrange(1, _PRIME), rng.randrange(_PRIME)) for _ in range(_PERMS)]
        self._rows = _PERMS // _BANDS
        self._buckets: list[dict[tuple[int, ...], list[Sequence[int]]]] = [
            {} for _ in range(_BANDS)
        ]

    def _signature(self, tokens: list[str]) -> list[int]:
        grams = {
            " ".join(tokens[i : i + _SHINGLE]) for i in range(max(len(tokens) - _SHINGLE + 1, 1))
        }
        hashes = [
            int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
            for g in grams
        ]
        return [min((a * h + b) % _PRIME for h in hashes) for a, b in self._coeffs]

    def is_duplicate(self, text: str) -> bool:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return False
        sig = self._signature(tokens)
        keys = [tuple(sig[i * self._rows : (i + 1) * self._rows]) for i in range(_BANDS)]
        for bucket, key in zip(self._buckets, keys, strict=True):
            for other in bucket.get(key, ()):
                same = sum(x == y for x, y in zip(sig, other, strict=True))
                if same / _PERMS >= self._threshold:
                    return True
        for bucket, key in zip(self._buckets, keys, strict=True):
            bucket.setdefault(key, []).append(sig)
        return False


def make_deduper(transform: Transform) -> ExactDeduper | NearDeduper | None:
    if transform.dedup == "exact":
        return ExactDeduper()
    if transform.dedup == "near":
        return NearDeduper(transform.near_threshold)
    return None
