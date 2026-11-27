"""Text helpers shared by the analyzers."""

from __future__ import annotations

import re

from reddit_analyzer.models import Post

WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
URL = re.compile(r"https?://\S+")
# Small multilingual list: enough to keep the top words readable, not a linguistic resource.
STOPWORDS = frozenset(
    """that this with from have there their about would could which what when your will been
    were they them then than also just like into more some very only over such other because
    where while these those being does doing here again once each both cannot dont
    che non per una sono come anche più questo questa quello della delle degli dello nel nella
    nelle nei alla alle agli allo con del dei gli suo sua suoi sue loro dove quando perché
    perche cosa tutto tutti tutte molto ancora solo sulla sulle essere stato stata fatto
    hanno aveva ogni però pero oppure""".split()
)


def post_text(post: Post) -> str:
    """Title and body without links, the text every analyzer looks at."""
    return URL.sub(" ", f"{post.title}\n{post.selftext}").strip()


def words(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS]
