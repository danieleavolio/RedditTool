"""Analysis: counts, rankings and trends of one collection."""

from __future__ import annotations

import streamlit as st

from reddit_analyzer import analyzers
from reddit_analyzer.errors import RedditError
from reddit_analyzer.gui import charts
from reddit_analyzer.gui.state import get_context

ALL = "All collections"


def render() -> None:
    service = get_context().service
    st.title("Analysis")
    names = [r.name for r in service.overview()]
    if not names:
        st.info("Nothing collected yet. Start from the Collect page.")
        return
    choice = st.selectbox("Collection", [ALL, *names])
    stats = service.stats(None if choice == ALL else choice)
    if not stats.posts:
        st.info("No posts in this collection.")
        return
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Posts", stats.posts)
    k2.metric("Comments", stats.comments)
    k3.metric("Mean score", f"{stats.score_mean:.1f}")
    k4.metric("Period", f"{stats.first_post} → {stats.last_post}")
    st.plotly_chart(charts.posts_per_month(stats), width="stretch")
    left, right = st.columns(2)
    left.plotly_chart(charts.ranking(stats.top_subreddits, "Top subreddits"), width="stretch")
    right.plotly_chart(charts.ranking(stats.top_authors, "Top authors"), width="stretch")
    st.plotly_chart(charts.ranking(stats.top_words, "Most frequent words"), width="stretch")
    st.plotly_chart(charts.activity_heatmap(stats.activity), width="stretch")
    _analyzers(service, None if choice == ALL else choice)


def _analyzers(service, collection: str | None) -> None:
    """Stored results of the other analyzers, each with a button to (re)compute it."""
    st.header("Analyzers")
    saved = service.saved_analyses(collection)
    for name, analyzer in service.analyzers().items():
        if name == "stats":  # shown above, live
            continue
        st.subheader(name)
        st.caption(analyzer.description)
        if analyzers.missing_requirements(analyzer):
            st.info(analyzers.install_hint(analyzer))
            continue
        label = "Recompute" if name in saved else "Compute"
        if st.button(label, key=f"run-{name}"):
            try:
                with st.spinner(f"Running {name} ..."):
                    saved[name] = service.run_analyzer(name, collection)
            except RedditError as exc:
                st.error(str(exc))
        if name in saved:
            st.caption(f"Computed {saved[name].computed_at:%Y-%m-%d %H:%M} UTC")
            _show(name, analyzer, saved[name].data)


def _show(name: str, analyzer, data: dict) -> None:
    if name == "keywords":
        top = [(k["term"], k["score"]) for k in data["keywords"][:15]]
        st.plotly_chart(charts.ranking(top, "Distinctive words (TF-IDF)"), width="stretch")
    elif name == "language":
        top = list(data["languages"].items())[:10]
        st.plotly_chart(charts.ranking(top, "Languages"), width="stretch")
    elif name == "sentiment":
        if data["analyzed"]:
            st.metric("Mean sentiment (English posts)", f"{data['mean']:+.2f}")
            st.plotly_chart(charts.sentiment_by_month(data["by_month"]), width="stretch")
        st.caption(analyzer.summary(data))
    else:  # a plugin: we only know its summary
        st.text(analyzer.summary(data))
