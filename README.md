# Reddit Post Analyzer

[![CI](https://github.com/danieleavolio/RedditTool/actions/workflows/ci.yml/badge.svg)](https://github.com/danieleavolio/RedditTool/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/reddit-post-analyzer)](https://pypi.org/project/reddit-post-analyzer/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Collect Reddit posts and comments into a local SQLite database, build reproducible datasets
from YAML recipes, and explore everything from the command line, a terminal UI or a web UI.
One core library, three interfaces.

Italiano: [README.it.md](README.it.md) · Docs: <https://danieleavolio.github.io/RedditTool/>

<!-- TODO: add a GIF of the TUI here (docs/assets/tui.gif) -->

## Quickstart

```bash
pip install "reddit-post-analyzer[tui,gui,nlp]"      # the core and the CLI are always included
rpa auth login                                        # your own Reddit API credentials
rpa collect search "rust" -s programming -n 500 --comments && rpa tui
```

You need **your own Reddit API credentials**: the tool ships no keys. See
[docs/reddit-credentials.md](docs/reddit-credentials.md) for how to set them up and what to do
if you do not have any.

## What it does

| Command | What it does |
|---|---|
| `rpa collect search "rust" -s programming -n 500 --comments` | search Reddit and store posts and comments |
| `rpa collect subreddit italy --sort top -t year -n 1000` | read a subreddit listing |
| `rpa runs list` / `rpa runs resume <id>` | interrupted collections continue where they stopped |
| `rpa dataset build recipes/examples/ai-italia.yaml` | build a dataset from a recipe (filters, cleaning, split) |
| `rpa export <collection> --format jsonl` | export a whole collection (CSV, JSONL, Parquet, Hugging Face) |
| `rpa analyze <collection>` | statistics, keywords (TF-IDF), language and sentiment |
| `rpa tui` | terminal UI (Textual) |
| `rpa gui` | web UI (Streamlit) |

Every command accepts `--json` for scripting. Run `rpa --help` or read the
[CLI reference](https://danieleavolio.github.io/RedditTool/cli/).

- **Datasets are recipes.** A YAML file describes sources, filters, text cleaning, deduplication
  and an optional deterministic split. The same recipe on the same database gives the same output,
  byte for byte, and writes a `dataset_card.md`.
- **Resumable and incremental.** The same post found by two searches is stored once and belongs
  to both collections.
- **Analyzers are plugins.** Results are stored, so the TUI and the web UI show them without
  recomputing. Write your own with an
  [entry point](https://danieleavolio.github.io/RedditTool/analyzers/).
- **Light.** SQLite and a few dependencies. Extras are opt-in: `[tui]`, `[gui]`, `[nlp]`,
  `[parquet]`, `[hf]`.

**TUI keys:** `F1` dashboard, `F2` new collection, `F3` post browser, `F4` recipe editor with live
preview, `F5` analysis, `Ctrl+P` command palette. In a browser: `textual serve "rpa tui"`.

## Install from source

```bash
git clone https://github.com/danieleavolio/RedditTool && cd RedditTool
uv sync --all-extras
uv run pytest
```

## Disclaimer

Reddit Post Analyzer is a tool for **downloading, organizing and exploring** Reddit
content locally. It is not designed or intended for training machine learning or AI models.

- This project is not affiliated with, endorsed by, or sponsored by Reddit, Inc.
- You must use your own Reddit API credentials, approved by Reddit, and comply with
  Reddit's User Agreement, Developer Terms, Data API Terms and Responsible Builder Policy.
- Using Reddit data to train ML/AI models, or for any commercial purpose, requires
  express written approval from Reddit. Obtaining it is your responsibility.
- No Reddit data is distributed with this project. Do not redistribute datasets built
  with it unless you are allowed to.
- Respect users' privacy: delete content that has been removed from Reddit and do not
  try to identify individuals.

The software is provided "as is", without warranty. The authors are not responsible
for how it is used.

> **Status of Reddit's Data API.** Reddit stopped accepting new Data API access requests on
> 31 Oct 2026 and plans to end remaining public access in March 2027. If you already have an
> approved app the tool works for as long as Reddit keeps it active. Check your access before
> relying on this tool.

## Contributing and license

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Released under the
[MIT License](LICENSE).
