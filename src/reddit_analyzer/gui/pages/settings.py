"""Settings: where the data lives and whether the Reddit credentials work."""

from __future__ import annotations

import streamlit as st

from reddit_analyzer.config import config_file_path
from reddit_analyzer.errors import RedditError
from reddit_analyzer.gui.state import get_context


def render() -> None:
    service = get_context().service
    settings = service.settings
    st.title("Settings")
    st.subheader("Reddit credentials")
    st.caption("Set them with `rpa auth login`. Secrets are never shown here.")
    st.write(f"Client ID: `{settings.reddit.client_id or 'not set'}`")
    st.write(f"Redirect URI: `{settings.reddit.redirect_uri}`")
    if st.button("Check credentials"):
        with st.spinner("Asking Reddit ..."):
            try:
                status = service.auth_status()
            except RedditError as exc:
                st.error(str(exc))
            else:
                remaining = status.ratelimit_remaining
                st.success(
                    f"Signed in as u/{status.username}. Rate limit left: "
                    f"{'unknown' if remaining is None else int(remaining)}."
                )
    st.subheader("Files")
    st.write(f"Database: `{settings.db_path}`")
    st.write(f"Config file: `{config_file_path()}`")
    st.subheader("Collection defaults")
    st.json(settings.collect.model_dump())
