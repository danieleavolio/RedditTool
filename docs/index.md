# Reddit Post Analyzer

Collect Reddit posts and comments into a local SQLite database, build reproducible datasets from
YAML recipes, and explore them from the command line (`rpa`), a terminal UI (`rpa tui`) or a web
UI (`rpa gui`). All three are thin layers over one core library, so they always agree.

```bash
uv tool install "reddit-post-analyzer[tui,gui,nlp] @ git+https://github.com/danieleavolio/RedditTool"
rpa auth login
rpa collect search "rust" -s programming -n 500 --comments && rpa tui
```

Start with the [quickstart](quickstart.md). You need your own Reddit API credentials:
[how to get and use them](reddit-credentials.md).

## Install extras

| Extra | Adds |
|---|---|
| *(none)* | core, SQLite storage, recipes, CSV/JSONL export and the CLI |
| `tui` | `rpa tui` (Textual) |
| `gui` | `rpa gui` (Streamlit, Plotly) |
| `nlp` | language detection and sentiment (`langdetect`, `vaderSentiment`) |
| `parquet` | Parquet export |
| `hf` | Hugging Face `datasets` export (local format only) |

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
