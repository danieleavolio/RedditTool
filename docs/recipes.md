# Recipes

A recipe is a YAML file that **selects and shapes** what is already in your local database. It
never touches the network. The same recipe on the same database always writes the same bytes.

```yaml
name: ai-italia-2026            # lowercase letters, digits, - and _
collection: ai-italia           # a collection you filled with `rpa collect ...`
search: "intelligenza artificiale"   # optional local full-text match on title and selftext
unit: post                      # post | comment | pair (post -> its top reply)

filters:
  subreddits: [italy, ItaliaPersonalFinance]
  min_score: 5
  after: 2026-01-01
  lang: it                      # needs the [nlp] extra
  exclude_removed: true
  exclude_bots: true
  min_chars: 40

transform:
  text: "{title}\n\n{selftext}"
  strip: [urls, markdown, usernames]
  dedup: exact                  # none | exact | near

split:                          # optional; a thread never crosses parts
  parts: { a: 0.8, b: 0.2 }
  seed: 42

output:
  format: jsonl                 # csv | jsonl | parquet | hf
  fields: [id, subreddit, created_utc, score, num_comments, text]
```

## Reference

| Section | Option | Meaning |
|---|---|---|
| top level | `unit` | rows are `post`s, `comment`s or `pair`s (post and its top reply) |
| `filters` | `min_score`, `max_score` | score range |
| | `after` (inclusive), `before` (exclusive) | dates; a bare date means 00:00 UTC |
| | `subreddits`, `exclude_authors` | lists, case-insensitive |
| | `lang` | ISO codes, e.g. `[it, en]`; uses the stored language or detects it |
| | `exclude_removed` | default `true`: `[removed]` is never data |
| | `nsfw` | `include` (default), `exclude`, `only` |
| | `min_chars`, `max_chars` | measured on the cleaned text |
| | `exclude_bots` | AutoModerator and authors named like `*bot` / `*_bot` |
| `transform` | `text` | template using the unit's fields, e.g. `{title}` and `{selftext}` |
| | `strip` | any of `urls`, `markdown`, `usernames` |
| | `normalize_whitespace` | default `true` |
| | `dedup` | `none`, `exact` (hash) or `near` (MinHash, threshold `near_threshold`) |
| `split` | `parts`, `seed` | shares must sum to 1; parts are deterministic and grouped by post |
| `output` | `format`, `fields` | defaults depend on the unit |

Mistakes are reported with the option name and what was expected, for example
`filters.min_score: 'min_score' cannot be greater than 'max_score'`.

!!! note
    The split is optional and generic: it creates named partitions of the data, nothing more.
    See the [disclaimer](index.md#disclaimer) about what the data may be used for.
