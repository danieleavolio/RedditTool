"""Analysis: counts, rankings and trends of one collection."""

from __future__ import annotations

import streamlit as st

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
