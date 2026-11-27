# Dataset card: my-dataset

Generated on 2026-11-27 by Reddit Post Analyzer 0.2.0.dev0.

## Source

Collection `depressione-borderline-genitori-psicologo-suicidio`, stored locally. Runs that filled it:

- run 2: search “depressione, borderline, genitori, psicologo, suicidio”, sort relevance, 100 posts (2026-11-27)

## Contents

- Unit: one row per post
- Rows: 97 kept out of 100 candidates
- Columns: `id`, `subreddit`, `created_utc`, `score`, `num_comments`, `text`
- Format: jsonl
- Files: `my-dataset.jsonl`
- Text length: 1366 characters on average, 6367 at most
- `created_utc` is an ISO 8601 UTC timestamp.

## Dropped rows

- 2: score outside the allowed range
- 1: exact duplicate of an earlier row

## Recipe

Rebuild this dataset from the same database with this recipe:

```yaml
name: my-dataset
collection: depressione-borderline-genitori-psicologo-suicidio
unit: post
filters:
  min_score: 1
  subreddits: []
  lang: []
  exclude_removed: true
  nsfw: include
  min_chars: 40
  exclude_bots: false
  exclude_authors: []
transform:
  strip:
  - urls
  - markdown
  normalize_whitespace: true
  dedup: exact
  near_threshold: 0.8
output:
  format: jsonl
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
