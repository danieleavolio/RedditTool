# Contributing

Thanks for helping. Bug reports, docs fixes, new analyzers and new exporters are all welcome.
Issues labelled `good first issue` are a good place to start.

## Setup

```bash
git clone https://github.com/danieleavolio/RedditTool && cd RedditTool
uv sync --all-extras        # the dev group (pytest, ruff, textual, streamlit...) comes with it
uv run pytest               # offline: no Reddit credentials needed
uv run ruff check . && uv run ruff format --check .
```

Python 3.11 or newer.

## How the code is organized

The **core** (`src/reddit_analyzer`: `models`, `sources`, `collect`, `storage`, `datasets`,
`export`, `analyzers`, `service`) holds all the logic. The interfaces (`cli`, `tui`, `gui`) are
thin: they call the core and display the result. If you are adding behavior, it almost always
belongs in the core, with a test, and the interfaces just expose it.

## Tests

- Tests never touch the network: Reddit is mocked with recorded responses (`respx`, see
  `tests/fixtures`). Tests marked `live` need real credentials in `RPA_*` variables and are
  skipped otherwise.
- TUI tests drive the real screens with Textual's pilot; GUI tests use Streamlit's `AppTest`.
- A bug fix comes with a test that fails without it.

## Pull requests

- One topic per PR, branched from `main`. Keep the diff focused.
- `ruff check`, `ruff format --check` and `pytest` must pass (CI runs them on Linux, Windows and
  macOS with Python 3.11 to 3.13).
- Add a line to `CHANGELOG.md` under "Unreleased" for anything a user would notice.
- Do not commit Reddit data, credentials or databases.

## Writing an analyzer

Subclass `reddit_analyzer.analyzers.Analyzer` and register it as an entry point. See
[docs/analyzers.md](docs/analyzers.md).

## Reddit's rules

The project must keep following Reddit's Data API terms: official OAuth only, a descriptive
User-Agent, no bypassing of rate limits, no anonymous scraping fallback. PRs that weaken this
cannot be accepted.
