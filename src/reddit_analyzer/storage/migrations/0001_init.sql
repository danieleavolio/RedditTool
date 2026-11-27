-- Initial schema. Posts are global (one row per Reddit id); collections reach them
-- through runs and the run_posts bridge, so the same post can live in several collections.

CREATE TABLE collections (
    name        TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    collection       TEXT NOT NULL REFERENCES collections(name) ON DELETE CASCADE,
    source           TEXT NOT NULL,
    params           TEXT NOT NULL,           -- JSON of SearchParams / ListingParams
    status           TEXT NOT NULL,
    cursor           TEXT,                    -- Reddit "after" token, saved every page
    posts_fetched    INTEGER NOT NULL DEFAULT 0,
    posts_inserted   INTEGER NOT NULL DEFAULT 0,
    posts_updated    INTEGER NOT NULL DEFAULT 0,
    comments_fetched INTEGER NOT NULL DEFAULT 0,
    error            TEXT,
    created_at       TEXT NOT NULL,
    started_at       TEXT,
    finished_at      TEXT
);
CREATE INDEX idx_runs_collection ON runs(collection);

CREATE TABLE posts (
    rid          INTEGER PRIMARY KEY,         -- stable rowid, needed by the FTS index
    id           TEXT NOT NULL UNIQUE,
    subreddit    TEXT NOT NULL,
    author       TEXT,
    title        TEXT NOT NULL,
    selftext     TEXT NOT NULL,
    url          TEXT NOT NULL,
    permalink    TEXT NOT NULL,
    score        INTEGER NOT NULL,
    upvote_ratio REAL,
    num_comments INTEGER NOT NULL,
    created_utc  REAL NOT NULL,               -- epoch seconds, UTC
    over_18      INTEGER NOT NULL,
    is_self      INTEGER NOT NULL,
    flair        TEXT,
    status       TEXT NOT NULL,
    lang         TEXT,
    raw          TEXT NOT NULL,
    first_seen   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX idx_posts_subreddit ON posts(subreddit COLLATE NOCASE);
CREATE INDEX idx_posts_created ON posts(created_utc);

CREATE TABLE run_posts (
    run_id  INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    PRIMARY KEY (run_id, post_id)
) WITHOUT ROWID;
CREATE INDEX idx_run_posts_post ON run_posts(post_id);

CREATE TABLE comments (
    id          TEXT PRIMARY KEY,
    post_id     TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    parent_id   TEXT NOT NULL,
    depth       INTEGER NOT NULL,
    author      TEXT,
    body        TEXT NOT NULL,
    score       INTEGER NOT NULL,
    created_utc REAL NOT NULL,
    status      TEXT NOT NULL,
    raw         TEXT NOT NULL
);
CREATE INDEX idx_comments_post ON comments(post_id);

-- Local full-text search over title and selftext, kept in sync by triggers.
CREATE VIRTUAL TABLE posts_fts USING fts5(
    title, selftext,
    content='posts', content_rowid='rid',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, title, selftext) VALUES (new.rid, new.title, new.selftext);
END;
CREATE TRIGGER posts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, title, selftext)
    VALUES ('delete', old.rid, old.title, old.selftext);
END;
CREATE TRIGGER posts_au AFTER UPDATE OF title, selftext ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, title, selftext)
    VALUES ('delete', old.rid, old.title, old.selftext);
    INSERT INTO posts_fts(rowid, title, selftext) VALUES (new.rid, new.title, new.selftext);
END;
