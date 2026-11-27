"""Dataset: edit a YAML recipe, preview the rows, build and download the files."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from reddit_analyzer.errors import RedditError
from reddit_analyzer.gui.state import get_context
from reddit_analyzer.service import TEMPLATE, find_recipes

NEW = "New recipe from template"


def _template() -> str:
    rows = get_context().service.overview()
    return TEMPLATE.format(collection=rows[0].name if rows else "my-collection")


def _load_choice(files: dict[str, Path]) -> None:
    choice = st.session_state.recipe_file
    if choice == NEW:
        st.session_state.recipe_text = _template()
    else:
        st.session_state.recipe_text = files[choice].read_text(encoding="utf-8")
        st.session_state.recipe_path = choice


def render() -> None:
    service = get_context().service
    st.title("Dataset")
    files = {str(p.relative_to(Path.cwd())): p for p in find_recipes(Path.cwd())}
    st.session_state.setdefault("recipe_text", _template())
    st.session_state.setdefault("recipe_path", "recipes/my-dataset.yaml")
    st.selectbox("Recipe", [NEW, *files], key="recipe_file", on_change=_load_choice, args=(files,))
    editor, result = st.columns(2)
    with editor:
        st.text_area(
            "Recipe (YAML)",
            key="recipe_text",
            height=420,
            help="Applied when you click outside the box or press Ctrl+Enter.",
        )
        path = st.text_input("Save as", key="recipe_path")
        if st.button("Save recipe"):
            target = Path(path.strip())
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(st.session_state.recipe_text, encoding="utf-8", newline="\n")
            except OSError as exc:
                st.error(f"Cannot save {target}: {exc.strerror or exc}")
            else:
                st.success(f"Saved {target}")
    text = st.session_state.recipe_text
    with result:
        st.markdown("**Preview**")
        try:
            _, preview = service.preview_recipe(text)
        except RedditError as exc:
            st.error(str(exc))
            return
        stats = preview.stats
        k1, k2 = st.columns(2)
        k1.metric("Rows kept", stats.kept)
        k2.metric("Candidates", stats.seen)
        if stats.dropped:
            st.dataframe(
                [{"Dropped": n, "Reason": reason} for reason, n in stats.dropped.most_common()],
                hide_index=True,
                width="stretch",
            )
        if stats.kept:
            st.caption(f"Text: {stats.chars_mean:.0f} characters on average, {stats.chars_max} max")
        st.dataframe(
            [
                {
                    "Subreddit": r.get("subreddit", ""),
                    "Score": r.get("score", ""),
                    "Text": " ".join(str(r.get("text", "")).split())[:200],
                }
                for r in preview.rows
            ],
            hide_index=True,
            width="stretch",
        )
    if st.button("Build dataset", type="primary"):
        try:
            _, built = service.build_recipe(text)
        except RedditError as exc:
            st.error(str(exc))
            return
        st.session_state.built = [*built.files, built.card]
        st.success(f"{built.stats.kept} rows written to {built.card.parent}")
    for file in st.session_state.get("built", []):
        if file.exists():
            st.download_button(
                f"Download {file.name}", file.read_bytes(), file_name=file.name, key=f"dl_{file}"
            )
