-- Output of the analyzers, so the interfaces can show it without recomputing.
-- ``collection`` is '' for "the whole database"; it is not a foreign key for that reason.
CREATE TABLE analysis_results (
    collection  TEXT NOT NULL,
    analyzer    TEXT NOT NULL,
    result      TEXT NOT NULL,                -- JSON, shape defined by the analyzer
    computed_at TEXT NOT NULL,
    PRIMARY KEY (collection, analyzer)
) WITHOUT ROWID;
