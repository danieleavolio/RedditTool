# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semver](https://semver.org/).

## Unreleased

### Added
- Analyzers as plugins: `stats` (with weekday/hour heatmap), `keywords` (TF-IDF), `language`,
  `sentiment` (English only), discovered through the `reddit_analyzer.analyzers` entry point.
- `rpa analyze`, and stored results (`analysis_results`, migration 0002) shown by the TUI and web UI.
- English and Italian READMEs, MkDocs documentation, contribution guide, issue and PR templates.
- CI on Linux, Windows and macOS (Python 3.11 to 3.13) and PyPI release by tag.

### Changed
- The `nlp` extra is now `langdetect` and `vaderSentiment` (no more scikit-learn or NLTK).

### Removed
- `docs/Documentation.md`, which described the pre-0.2 script.

## 0.2.0 (in development)

The old single-script app became a library with a CLI, a terminal UI and a web UI:
official OAuth client with rate limiting, resumable collection runs, SQLite storage with
migrations, YAML dataset recipes with CSV/JSONL/Parquet/Hugging Face export, `rpa tui`, `rpa gui`.
The pre-0.2 database can be imported with `rpa db import-legacy`.
