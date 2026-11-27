"""Collect: start a run (it keeps going in the background), watch it, resume interrupted ones."""

from __future__ import annotations

from typing import get_args

import streamlit as st
from pydantic import ValidationError

from reddit_analyzer.gui.state import Context, get_context
from reddit_analyzer.models import (
    CommentsSpec,
    ListingParams,
    ListingSort,
    Run,
    RunStatus,
    SearchParams,
    Sort,
    TimeFilter,
)

SEARCH, LISTING = "Search by keywords", "Subreddit listing"
DEFAULT_SORT = {SEARCH: "relevance", LISTING: "new"}


def _explain(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'form'}: {e['msg']}" for e in exc.errors()
        )
    return str(exc)


def build_run(
    ctx: Context,
    kind: str,
    text: str,
    subs: str,
    sort: str,
    time: str,
    limit: int,
    comments: bool,
    name: str,
) -> Run:
    text = text.strip()
    if not text:
        raise ValueError("Type the keywords or the subreddit first.")
    spec = None
    if comments:
        cfg = ctx.service.settings.collect
        spec = CommentsSpec(depth=cfg.comments_depth, max_per_post=cfg.comments_max_per_post)
    if kind == SEARCH:
        subreddits = [s for s in (p.strip() for p in subs.split(",")) if s]
        params: SearchParams | ListingParams = SearchParams(
            query=text, subreddits=subreddits, sort=sort, time=time, limit=limit, comments=spec
        )
        seed = text
    else:
        params = ListingParams(subreddit=text, sort=sort, time=time, limit=limit, comments=spec)
        seed = params.subreddit
    return Run(collection=name.strip() or ctx.service.default_collection(seed), params=params)


def _form(ctx: Context) -> None:
    kind = st.radio("Source", [SEARCH, LISTING], horizontal=True, key="collect_kind")
    sorts = get_args(Sort) if kind == SEARCH else get_args(ListingSort)
    with st.form("collect_form"):
        text = st.text_input("Keywords" if kind == SEARCH else "Subreddit")
        subs = ""
        if kind == SEARCH:
            subs = st.text_input(
                "Subreddits", placeholder="optional, comma separated: python, rust"
            )
        left, middle, right = st.columns(3)
        sort = left.selectbox("Sort", sorts, index=sorts.index(DEFAULT_SORT[kind]))
        time = middle.selectbox("Time window", get_args(TimeFilter), index=5)
        limit = right.number_input("Max posts", min_value=1, value=100, step=50)
        comments = st.checkbox("Download comments too")
        name = st.text_input("Collection", placeholder="optional, default derived from the input")
        submitted = st.form_submit_button("Start", type="primary")
    if not submitted:
        return
    try:
        run = ctx.service.create_run(
            build_run(ctx, kind, text, subs, sort, time, int(limit), comments, name)
        )
    except (ValidationError, ValueError) as exc:
        st.error(_explain(exc))
        return
    ctx.runs.start(run)
    st.rerun()


def _progress(ctx: Context) -> None:
    """Live view of the current job. Polls once a second only while the job is running."""
    mgr = ctx.runs
    job = mgr.job
    if job is None:
        return
    running = mgr.busy

    @st.fragment(run_every=1 if running else None)
    def view() -> None:
        if running and not mgr.busy:
            st.rerun()  # the job just ended: redraw the whole page (re-enables the form)
        run = job.run
        st.subheader(f"Run {run.id}: {run.collection}")
        total = run.params.limit
        st.progress(
            min(run.posts_fetched / total, 1.0),
            text=f"{run.posts_fetched} / {total} posts, {run.comments_fetched} comments "
            f"({run.posts_inserted} new)",
        )
        if job.status_line:
            st.caption(job.status_line)
        if job.error:
            st.error(job.error)
        elif job.final is not None:
            st.success(f"Run {job.final.status.value}.")
        st.code("\n".join(job.log[-30:]), language=None)
        if not job.done and st.button("Cancel", key="cancel_run"):
            mgr.cancel()
            st.caption("Cancelling after the current step ...")

    view()


def _resumable(ctx: Context) -> None:
    runs = [r for r in ctx.service.recent_runs(10) if r.status is not RunStatus.COMPLETED]
    if not runs:
        return
    st.subheader("Interrupted runs")
    for run in runs:
        left, right = st.columns([5, 1])
        left.write(
            f"Run {run.id} · {run.collection} · {run.status.value} · "
            f"{run.posts_fetched}/{run.params.limit} posts"
        )
        if right.button("Resume", key=f"resume_{run.id}", disabled=ctx.runs.busy):
            ctx.runs.start(run, resumed=True)
            st.rerun()


def render() -> None:
    ctx = get_context()
    st.title("Collect")
    if ctx.runs.busy:
        st.info("A run is in progress: wait for it or cancel it before starting another.")
    else:
        _form(ctx)
    _progress(ctx)
    _resumable(ctx)
    st.subheader("Collections")
    rows = ctx.service.overview()
    if rows:
        st.dataframe(
            [
                {"Name": r.name, "Posts": r.posts, "Comments": r.comments, "Runs": r.runs}
                for r in rows
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("Nothing collected yet.")
