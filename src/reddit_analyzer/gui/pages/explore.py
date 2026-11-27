"""Explore: full-text search over the local database, with the post and its comments."""

from __future__ import annotations

import streamlit as st

from reddit_analyzer.gui.state import get_context

MAX_COMMENTS = 200
ALL = "All collections"


def quote(text: str, depth: int) -> str:
    """Markdown block quote nested ``depth + 1`` times, so replies look indented."""
    prefix = "> " * (depth + 1)
    return "\n".join(f"{prefix}{line}" for line in text.splitlines() or [""])


def render() -> None:
    service = get_context().service
    st.title("Explore")
    names = [r.name for r in service.overview()]
    if not names:
        st.info("Nothing collected yet. Start from the Collect page.")
        return
    c1, c2, c3 = st.columns([2, 3, 2])
    choice = c1.selectbox("Collection", [ALL, *names])
    text = c2.text_input("Search", placeholder="full-text match on title and body")
    sub = c3.text_input("Subreddit", placeholder="optional")
    posts = service.posts(None if choice == ALL else choice, text, sub, limit=500)
    st.caption(f"{len(posts)} posts shown (newest first, or best match first when searching)")
    event = st.dataframe(
        [
            {
                "Date": p.created_utc.date(),
                "Subreddit": p.subreddit,
                "Score": p.score,
                "Comments": p.num_comments,
                "Title": p.title,
            }
            for p in posts
        ],
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key="explore_table",
    )
    selected = event.selection.rows
    if not selected:
        return
    post = posts[selected[0]]
    st.divider()
    st.subheader(post.title)
    st.caption(
        f"r/{post.subreddit} · u/{post.author or '[deleted]'} · {post.created_utc:%Y-%m-%d %H:%M} "
        f"· score {post.score} · [open on Reddit]({post.full_url})"
    )
    if post.selftext:
        st.markdown(post.selftext)
    comments = service.comments(post.id)
    st.markdown(f"**Comments** ({len(comments)} saved of {post.num_comments})")
    for comment in comments[:MAX_COMMENTS]:
        who = comment.author or "[deleted]"
        st.markdown(quote(f"**{who}** · {comment.score}\n\n{comment.body}", comment.depth))
    if len(comments) > MAX_COMMENTS:
        st.caption(f"Only the first {MAX_COMMENTS} comments are shown.")
