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


def activity_heatmap(activity: list[list[int]]) -> go.Figure:
    """Posts by weekday (rows) and hour of the day (columns), UTC."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    fig = go.Figure(
        go.Heatmap(z=activity, x=list(range(24)), y=days, colorscale="Blues", showscale=False)
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Hour (UTC)", dtick=3)
    return _layout(fig, "Activity by weekday and hour")


def sentiment_by_month(by_month: list[list]) -> go.Figure:
    months = [m for m, _ in by_month]
    fig = go.Figure(go.Scatter(x=months, y=[v for _, v in by_month], mode="lines+markers"))
    fig.update_xaxes(type="category")
    fig.update_yaxes(range=[-1, 1])
    return _layout(fig, "Mean sentiment per month (English posts)")


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
