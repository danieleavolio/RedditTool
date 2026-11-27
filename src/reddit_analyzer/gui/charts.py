"""Plotly figures built from ``CollectionStats``. No pandas needed."""

from __future__ import annotations

import plotly.graph_objects as go

from reddit_analyzer.stats import CollectionStats

COLOR = "#4C8BF5"


def _layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def posts_per_month(stats: CollectionStats) -> go.Figure:
    months, counts = (
        zip(*stats.posts_per_month, strict=False) if stats.posts_per_month else ((), ())
    )
    fig = go.Figure(go.Bar(x=list(months), y=list(counts), marker_color=COLOR))
    fig.update_xaxes(type="category")
    return _layout(fig, "Posts per month")


def ranking(pairs: list[tuple[str, int]], title: str) -> go.Figure:
    """Horizontal bars, biggest on top."""
    ordered = list(reversed(pairs))
    fig = go.Figure(
        go.Bar(
            x=[n for _, n in ordered],
            y=[name for name, _ in ordered],
            orientation="h",
            marker_color=COLOR,
        )
    )
    return _layout(fig, title)
