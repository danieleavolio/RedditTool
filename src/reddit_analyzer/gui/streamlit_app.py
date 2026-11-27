"""Entry point: ``rpa gui`` runs ``streamlit run`` on this file."""

import streamlit as st

from reddit_analyzer.gui.pages import analysis, collect, dataset, explore, settings

st.set_page_config(page_title="Reddit Post Analyzer", page_icon=":material/forum:", layout="wide")

navigation = st.navigation(
    [
        st.Page(collect.render, title="Collect", icon=":material/download:", url_path="collect"),
        st.Page(explore.render, title="Explore", icon=":material/search:", url_path="explore"),
        st.Page(dataset.render, title="Dataset", icon=":material/dataset:", url_path="dataset"),
        st.Page(
            analysis.render, title="Analysis", icon=":material/monitoring:", url_path="analysis"
        ),
        st.Page(settings.render, title="Settings", icon=":material/settings:", url_path="settings"),
    ]
)
navigation.run()
