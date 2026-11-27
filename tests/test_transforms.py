from reddit_analyzer.datasets.recipe import Split, Transform
from reddit_analyzer.datasets.split import assign_part
from reddit_analyzer.datasets.transforms import (
    Cleaner,
    ExactDeduper,
    NearDeduper,
    normalize_whitespace,
    strip_markdown,
    strip_urls,
    strip_usernames,
)


def test_strip_urls_including_markdown_links():
    assert strip_urls("see https://a.io/x?y=1 now") == "see  now"
    assert strip_urls("see www.a.io/x, ok") == "see , ok"
    assert strip_urls("[label](https://a.io/x)") == "[label]"


def test_strip_usernames():
    assert strip_usernames("thanks u/some_user and /u/other-1!") == "thanks  and !"
    assert strip_usernames("you/me") == "you/me"  # not a username
    assert strip_usernames("u/ab") == "u/ab"  # too short to be one


def test_strip_markdown_keeps_the_words():
    text = (
        "# Title\n> quoted\n- item one\n1. item two\n"
        "**bold** and *italic* and ~~gone~~ and `code` and [link](http://x.io)\n"
        "![alt text](http://i.png) >!spoiler!<\n```py\nprint(1)\n```\n---\nsnake_case_name 2*3*4"
    )
    out = strip_markdown(text)
    assert "#" not in out and ">" not in out and "**" not in out and "`" not in out
    assert "Title" in out and "quoted" in out and "item one" in out and "item two" in out
    assert "bold and italic and gone and code and link" in out
    assert "alt text" in out and "spoiler" in out and "print(1)" in out
    assert "snake_case_name" in out and "2*3*4" in out
    assert "http" not in out


def test_normalize_whitespace():
    assert normalize_whitespace("a  b \t c\r\n\r\n\r\n\r\n d  \n") == "a b c\n\nd"


def test_cleaner_order_and_defaults():
    clean = Cleaner(Transform(strip=["urls", "markdown", "usernames"]))
    assert clean("**hi** [there](https://x.io) u/someone ") == "hi there"
    assert Cleaner(Transform(normalize_whitespace=False))("  a  ") == "  a  "
    assert Cleaner(Transform())("  a   b \n\n\n\nc ") == "a b\n\nc"


def test_exact_dedup_ignores_case_and_spacing():
    d = ExactDeduper()
    assert not d.is_duplicate("Hello   World")
    assert d.is_duplicate("hello world")
    assert not d.is_duplicate("hello there")


_BASE = (
    "the quick brown fox jumps over the lazy dog while the rest of the herd keeps walking "
    "slowly across the wide open field under a bright and cloudless summer sky today"
)


def test_near_dedup_catches_small_edits_only():
    d = NearDeduper(0.8)
    assert not d.is_duplicate(_BASE)
    assert d.is_duplicate(_BASE + " indeed")
    assert d.is_duplicate(_BASE.replace("quick", "fast"))
    assert not d.is_duplicate(
        "completely different words about databases, indexes and query plans "
        "that share nothing with the fox story at all, really nothing"
    )
    assert not d.is_duplicate("")  # nothing to compare


def test_near_dedup_is_deterministic():
    results = []
    for _ in range(2):
        d = NearDeduper(0.8)
        results.append([d.is_duplicate(t) for t in (_BASE, _BASE + " x", "other text here now")])
    assert results[0] == results[1] == [False, True, False]


def test_split_is_stable_proportional_and_seeded():
    split = Split(parts={"a": 0.8, "b": 0.2}, seed=7)
    ids = [f"p{i}" for i in range(4000)]
    first = {i: assign_part(i, split) for i in ids}
    assert first == {i: assign_part(i, split) for i in reversed(ids)}  # order independent
    share_a = sum(v == "a" for v in first.values()) / len(ids)
    assert 0.77 < share_a < 0.83
    other = Split(parts={"a": 0.8, "b": 0.2}, seed=8)
    assert any(assign_part(i, other) != first[i] for i in ids)
    # adding posts later never moves the old ones
    assert all(assign_part(i, split) == first[i] for i in ids[:100])
