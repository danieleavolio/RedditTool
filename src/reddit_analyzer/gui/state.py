"""Objects shared by every page: one ``Service`` and one ``RunManager`` per server process."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from reddit_analyzer.gui.jobs import RunManager
from reddit_analyzer.service import Service

# Tests put their own Context here (with a fake source) before running a page.
OVERRIDE_KEY = "rpa_context"


@dataclass(frozen=True)
class Context:
    service: Service
    runs: RunManager


@st.cache_resource
def _shared() -> Context:
    service = Service()
    return Context(service, RunManager(service))


def get_context() -> Context:
    return st.session_state.get(OVERRIDE_KEY) or _shared()
