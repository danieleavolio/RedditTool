"""The recipe: a validated, versionable description of one dataset.

Example (see ``recipes/examples/``)::

    name: ai-italia-2026
    collection: ai-italia
    search: "intelligenza artificiale"
    filters: {min_score: 5, lang: it, min_chars: 40}
    transform: {strip: [urls, markdown], dedup: exact}
    split: {parts: {a: 0.8, b: 0.2}, seed: 42}
    output: {format: jsonl}

A recipe only *selects and shapes* what is already in the local database. It never touches
the network.
"""

from __future__ import annotations

import string
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, ValidationError, field_validator, model_validator

from reddit_analyzer.datasets.fields import DEFAULT_FIELDS, DERIVED, UNIT_FIELDS, Unit
from reddit_analyzer.errors import DatasetError
from reddit_analyzer.models import Model

Strip = Literal["urls", "markdown", "usernames"]
Dedup = Literal["none", "exact", "near"]
Format = Literal["csv", "jsonl", "parquet", "hf"]


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class Filters(Model):
    min_score: int | None = None
    max_score: int | None = None
    after: datetime | None = None  # inclusive; a bare date means 00:00 UTC
    before: datetime | None = None  # exclusive
    subreddits: list[str] = Field(default_factory=list)  # empty = any
    lang: list[str] = Field(default_factory=list)  # empty = any; needs the [nlp] extra
    exclude_removed: bool = True  # drops removed/deleted content: "[removed]" is never data
    nsfw: Literal["include", "exclude", "only"] = "include"
    min_chars: int | None = Field(None, ge=0)  # measured on the cleaned text
    max_chars: int | None = Field(None, ge=1)
    exclude_bots: bool = False  # AutoModerator and authors named like *bot / *_bot
    exclude_authors: list[str] = Field(default_factory=list)

    @field_validator("after", "before", mode="before")
    @classmethod
    def _dates(cls, value: Any) -> Any:
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime(value.year, value.month, value.day)
        return value

    @field_validator("after", "before")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("lang", "subreddits", "exclude_authors", mode="before")
    @classmethod
    def _one_or_many(cls, value: Any) -> Any:
        return [value] if isinstance(value, str) else value

    @field_validator("subreddits", "lang", "exclude_authors")
    @classmethod
    def _lower(cls, value: list[str]) -> list[str]:
        return [v.strip().removeprefix("/").removeprefix("r/").lower() for v in value]

    @model_validator(mode="after")
    def _ranges(self) -> Filters:
        if self.after and self.before and self.after >= self.before:
            raise ValueError("'after' must be earlier than 'before'")
        if None not in (self.min_score, self.max_score) and self.min_score > self.max_score:
            raise ValueError("'min_score' cannot be greater than 'max_score'")
        if None not in (self.min_chars, self.max_chars) and self.min_chars > self.max_chars:
            raise ValueError("'min_chars' cannot be greater than 'max_chars'")
        return self


class Transform(Model):
    text: str | None = None  # template; default depends on the unit
    strip: list[Strip] = Field(default_factory=list)
    normalize_whitespace: bool = True
    dedup: Dedup = "none"
    near_threshold: float = Field(0.8, gt=0, le=1)  # estimated Jaccard similarity


class Split(Model):
    parts: dict[str, float]
    seed: int = 0
    by: Literal["post"] = "post"  # a thread's comments always stay together

    @field_validator("parts")
    @classmethod
    def _parts(cls, parts: dict[str, float]) -> dict[str, float]:
        if len(parts) < 2:
            raise ValueError("a split needs at least two parts")
        for name, share in parts.items():
            if not name or not all(c.isalnum() or c in "_-" for c in name):
                raise ValueError(f"part name {name!r} may only contain letters, digits, _ and -")
            if share <= 0:
                raise ValueError(f"part {name!r} must have a positive share")
        if abs(sum(parts.values()) - 1) > 1e-6:
            raise ValueError(f"part shares must sum to 1, got {sum(parts.values()):g}")
        return parts


class Output(Model):
    format: Format = "jsonl"
    fields: list[str] | None = None  # default depends on the unit


class Recipe(Model):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    collection: str
    search: str | None = None  # local full-text filter on title and selftext
    unit: Unit = "post"
    filters: Filters = Field(default_factory=Filters)
    transform: Transform = Field(default_factory=Transform)
    split: Split | None = None
    output: Output = Field(default_factory=Output)

    @model_validator(mode="after")
    def _against_unit(self) -> Recipe:
        available = UNIT_FIELDS[self.unit]
        for name in self.output.fields or []:
            if name not in available:
                raise ValueError(
                    f"output.fields: unknown field {name!r} for unit {self.unit!r}; "
                    f"available: {', '.join(available)}"
                )
        if self.transform.text is not None:
            usable = set(available) - DERIVED
            try:
                names = {n for _, n, _, _ in string.Formatter().parse(self.transform.text) if n}
            except ValueError as exc:
                raise ValueError(f"transform.text is not a valid template: {exc}") from exc
            unknown = sorted(n for n in names if n not in usable)
            if unknown:
                raise ValueError(
                    f"transform.text: unknown placeholder {{{unknown[0]}}} for unit "
                    f"{self.unit!r}; available: {', '.join(sorted(usable))}"
                )
        return self

    @property
    def fields(self) -> list[str]:
        return list(self.output.fields or DEFAULT_FIELDS[self.unit])


def _format_errors(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        where = ".".join(str(p) for p in err["loc"]) or "recipe"
        message = err["msg"].removeprefix("Value error, ")
        if err["type"] == "extra_forbidden":
            message = "unknown option"
        lines.append(f"  {where}: {message}")
    return "\n".join(lines)


def parse_recipe(data: Any) -> Recipe:
    if not isinstance(data, dict):
        raise DatasetError("A recipe must be a YAML mapping (key: value pairs).")
    try:
        return Recipe.model_validate(data)
    except ValidationError as exc:
        raise DatasetError(f"Invalid recipe:\n{_format_errors(exc)}") from exc


def load_recipe(path: Path | str) -> Recipe:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DatasetError(f"Cannot read recipe {path}: {exc.strerror or exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DatasetError(f"{path} is not valid YAML: {exc}") from exc
    return parse_recipe(data)


def recipe_to_yaml(recipe: Recipe) -> str:
    """The recipe as it was understood, defaults included, for the dataset card."""
    data = recipe.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
