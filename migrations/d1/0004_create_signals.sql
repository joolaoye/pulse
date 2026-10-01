CREATE TABLE IF NOT EXISTS signals (
    pipeline_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    source TEXT NOT NULL,
    relevance_score REAL NOT NULL,

    UNIQUE (
        pipeline_id,
        source,
        signal_id
    )
);

CREATE INDEX IF NOT EXISTS idx_signals_pipeline_id
ON signals (
    pipeline_id
);
