# Analyzers

An analyzer computes something about a collection. Results are stored in the local database
(table `analysis_results`), so the TUI and the web UI show them without recomputing.

```bash
rpa analyze --list                     # what is available and what needs an extra
rpa analyze my-collection              # run every analyzer that is ready
rpa analyze my-collection -a keywords  # run one (repeat -a for more)
rpa analyze my-collection --show       # print what is stored, compute nothing
```

Omit the collection to analyze the whole database.

## Built-in

| Name | Needs | What it gives |
|---|---|---|
| `stats` | | counts, posts per month, top subreddits and authors, activity by weekday and hour |
| `keywords` | | words that characterize the collection (TF-IDF, one document per post) |
| `language` | `[nlp]` | language of each post, saved on the post (dataset `lang` filters use it) |
| `sentiment` | `[nlp]` | VADER sentiment of **English** posts only |

!!! note "Why sentiment skips other languages"
    VADER only understands English. Scoring Italian or Spanish posts with it produces noise, so
    posts in other languages are counted as skipped instead of getting a wrong score.

## Writing a plugin

Subclass `Analyzer`, return JSON-serializable data from `run`, and register the class as an
entry point in your package's `pyproject.toml`:

```python
from reddit_analyzer.analyzers import Analyzer


class LongPosts(Analyzer):
    name = "long-posts"
    description = "Posts with more than 1000 characters."
    # requires = ("somelib",)   # importable modules; missing ones give an install hint
    # extra = "myextra"         # the pip extra named in that hint

    def run(self, db, collection):
        n = sum(len(p.selftext) > 1000 for p in db.iter_posts(collection=collection))
        return {"long_posts": n}

    def summary(self, data):
        return f"{data['long_posts']} long posts"
```

```toml
[project.entry-points."reddit_analyzer.analyzers"]
long-posts = "my_package:LongPosts"
```

After `pip install`, `rpa analyze --list` shows it, and the TUI and web UI list it with its
`summary`. A plugin that fails to import, or whose name is already taken, is skipped with a
warning; it never breaks the tool. `db` is a `reddit_analyzer.storage.Database`: use
`iter_posts`, `get_comments`, `count_posts` and friends.
