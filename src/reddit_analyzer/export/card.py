"""The ``dataset_card.md`` written next to every dataset."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from reddit_analyzer import __version__
from reddit_analyzer.models import ListingParams, Run

if TYPE_CHECKING:
    from reddit_analyzer.datasets.builder import Stats
    from reddit_analyzer.datasets.recipe import Recipe

DISCLAIMER = """\
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
for how it is used."""

_REASONS = {
    "removed": "removed or deleted by the author or moderators",
    "bot": "written by a bot",
    "author": "written by an excluded author",
    "score": "score outside the allowed range",
    "date": "outside the date range",
    "subreddit": "from another subreddit",
    "nsfw": "excluded by the NSFW setting",
    "short": "shorter than min_chars after cleaning",
    "long": "longer than max_chars after cleaning",
    "lang": "language not in the list",
    "duplicate_exact": "exact duplicate of an earlier row",
    "duplicate_near": "near-duplicate of an earlier row",
    "no_reply": "no usable reply to pair with",
}


def _describe(run: Run) -> str:
    params = run.params
    where = (
        f"r/{params.subreddit}"
        if isinstance(params, ListingParams)
        else (
            f"search “{params.query}”"
            + (f" in {', '.join('r/' + s for s in params.subreddits)}" if params.subreddits else "")
        )
    )
    when = (run.finished_at or run.created_at).strftime("%Y-%m-%d")
    return f"- run {run.id}: {where}, sort {params.sort}, {run.posts_fetched} posts ({when})"


def render_card(
    *,
    recipe: Recipe,
    recipe_yaml: str,
    stats: Stats,
    files: list[str],
    runs: list[Run],
    generated_at: datetime,
) -> str:
    lines = [
        f"# Dataset card: {recipe.name}",
        "",
        f"Generated on {generated_at:%Y-%m-%d} by Reddit Post Analyzer {__version__}.",
        "",
        "## Source",
        "",
        f"Collection `{recipe.collection}`, stored locally. Runs that filled it:",
        "",
        *(_describe(r) for r in reversed(runs)),
    ]
    if not runs:
        lines.append("- (no runs recorded)")
    lines += [
        "",
        "## Contents",
        "",
        f"- Unit: one row per {recipe.unit}",
        f"- Rows: {stats.kept} kept out of {stats.seen} candidates",
        f"- Columns: {', '.join(f'`{f}`' for f in recipe.fields)}",
        f"- Format: {recipe.output.format}",
        f"- Files: {', '.join(f'`{f}`' for f in files)}",
        f"- Text length: {stats.chars_mean:.0f} characters on average, {stats.chars_max} at most",
        "- `created_utc` is an ISO 8601 UTC timestamp.",
    ]
    if recipe.split:
        shares = ", ".join(f"{n} {s:g}" for n, s in recipe.split.parts.items())
        lines.append(
            f"- Partitions (seed {recipe.split.seed}, grouped by post): {shares}. "
            "Rows per part: " + ", ".join(f"{n} {stats.parts[n]}" for n in recipe.split.parts)
        )
    if stats.dropped:
        lines += ["", "## Dropped rows", ""]
        for reason, count in stats.dropped.most_common():
            lines.append(f"- {count}: {_REASONS.get(reason, reason)}")
    lines += [
        "",
        "## Recipe",
        "",
        "Rebuild this dataset from the same database with this recipe:",
        "",
        "```yaml",
        recipe_yaml.rstrip(),
        "```",
        "",
        "## Disclaimer",
        "",
        DISCLAIMER,
        "",
    ]
    return "\n".join(lines)
