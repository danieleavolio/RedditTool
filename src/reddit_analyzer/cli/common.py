"""Shared plumbing for every `rpa` command: output modes, error handling and exit codes.

Exit codes: 0 ok, 1 other error, 2 usage error (click), 3 credentials missing/rejected,
4 Reddit unreachable or rate limited, 130 interrupted.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Literal, get_args

import typer
from rich.console import Console
from rich.table import Table

from reddit_analyzer.errors import (
    AuthError,
    ForbiddenError,
    RateLimitedError,
    RedditError,
    ServerError,
)
from reddit_analyzer.models import ListingSort, Sort, TimeFilter

EXIT_ERROR = 1
EXIT_AUTH = 3
EXIT_NETWORK = 4
EXIT_INTERRUPTED = 130

JsonOption = Annotated[
    bool, typer.Option("--json", help="Print machine-readable JSON on stdout instead of text.")
]


def _choices(name: str, literal: Any) -> type[Enum]:
    return Enum(name, {v: v for v in get_args(literal)}, type=str)  # type: ignore[return-value]


SortChoice = _choices("SortChoice", Sort)
ListingSortChoice = _choices("ListingSortChoice", ListingSort)
TimeChoice = _choices("TimeChoice", TimeFilter)
UnitChoice = _choices("UnitChoice", Literal["post", "comment", "pair"])
FormatChoice = _choices("FormatChoice", Literal["csv", "jsonl", "parquet", "hf"])


@dataclass
class Ui:
    """What the user asked for: how chatty to be and whether stdout carries JSON."""

    quiet: bool = False
    verbose: bool = False
    json: bool = False
    hint: str | None = None  # printed under the next error, e.g. how to resume a run

    @property
    def talkative(self) -> bool:
        return not (self.quiet or self.json)

    def info(self, message: str = "") -> None:
        """Progress and summaries. Hidden by --quiet and --json."""
        if self.talkative:
            typer.echo(message)

    def result(self, message: str = "") -> None:
        """The answer the user asked for. Hidden only by --json."""
        if not self.json:
            typer.echo(message)

    def emit(self, data: Any) -> None:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def table(self, table: Table) -> None:
        Console().print(table)


_ui = Ui()  # replaced by the root callback on every invocation (see setup_logging)


def get_ui(json_output: bool = False) -> Ui:
    _ui.json = json_output
    return _ui


def setup_logging(quiet: bool, verbose: bool) -> Ui:
    global _ui
    if quiet and verbose:
        raise typer.BadParameter("--quiet and --verbose cannot be used together.")
    log = logging.getLogger("reddit_analyzer")
    for handler in [h for h in log.handlers if getattr(h, "_rpa", False)]:
        log.removeHandler(handler)
    if verbose:
        handler = logging.StreamHandler(sys.stderr)
        handler._rpa = True  # type: ignore[attr-defined]
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)
    _ui = Ui(quiet=quiet, verbose=verbose)
    return _ui


def exit_code_for(exc: BaseException) -> int:
    if isinstance(exc, AuthError | ForbiddenError):
        return EXIT_AUTH
    if isinstance(exc, RateLimitedError | ServerError):
        return EXIT_NETWORK
    return EXIT_ERROR


@contextmanager
def cli_errors(ui: Ui) -> Iterator[None]:
    """Turn the suite's own errors and Ctrl+C into a message on stderr and an exit code."""
    try:
        yield
    except KeyboardInterrupt:
        typer.echo("\nInterrupted.", err=True)
        if ui.hint:
            typer.echo(ui.hint, err=True)
        raise typer.Exit(EXIT_INTERRUPTED) from None
    except RedditError as exc:
        typer.echo(f"Error: {exc}", err=True)
        if ui.hint:
            typer.echo(ui.hint, err=True)
        raise typer.Exit(exit_code_for(exc)) from exc


def fail(message: str) -> typer.Exit:
    typer.echo(f"Error: {message}", err=True)
    return typer.Exit(EXIT_ERROR)
