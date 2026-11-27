# Quickstart

## 1. Credentials

```bash
rpa auth login      # client ID and secret, then authorize in your browser
rpa auth test       # shows your user and the remaining rate limit
```

See [Reddit credentials](reddit-credentials.md) if you have none.

## 2. Collect

```bash
# search, optionally inside subreddits, with comments
rpa collect search "rust" -s programming --sort top -t month -n 500 --comments

# or read a subreddit listing
rpa collect subreddit italy --sort new -n 1000
```

Posts go into a **collection** (named after the query, or `-c name`). Reddit returns about 1000
items per listing; to go further, combine several sorts and time windows into the same
collection. A run that stops (Ctrl+C, network, rate limit) resumes where it was:

```bash
rpa runs list
rpa runs resume 3
```

The same post found by two searches is stored once and appears in both collections.

## 3. Look at it

```bash
rpa collections list
rpa analyze my-collection        # statistics, keywords, language, sentiment
rpa tui                          # or: rpa gui
```

## 4. Build a dataset

Write a [recipe](recipes.md), check it, build it:

```bash
rpa dataset preview recipes/examples/ai-italia.yaml --n 20
rpa dataset build recipes/examples/ai-italia.yaml
```

The output folder holds the data files and a `dataset_card.md` (source, filters, counts, date,
disclaimer). For a plain dump without filters: `rpa export my-collection --format jsonl`.

## Where is my data?

In your user data folder (`reddit.db` plus `config.toml`). The *Settings* page of the web UI shows
the exact paths. Set `RPA_DATA_DIR` to put it elsewhere.
