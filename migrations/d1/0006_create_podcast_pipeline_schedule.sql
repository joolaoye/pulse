CREATE TABLE podcast_pipeline_schedule (
    pipeline_id TEXT PRIMARY KEY,

    local_time TEXT NOT NULL,

    timezone TEXT NOT NULL,

    next_run_at TEXT NOT NULL,

    last_dispatched_at TEXT,

    created_at TEXT NOT NULL
        DEFAULT (
            strftime(
                '%Y-%m-%dT%H:%M:%fZ',
                'now'
            )
        ),

    updated_at TEXT NOT NULL
        DEFAULT (
            strftime(
                '%Y-%m-%dT%H:%M:%fZ',
                'now'
            )
        ),

    FOREIGN KEY (
        pipeline_id
    )
    REFERENCES podcast_pipeline (
        pipeline_id
    )
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

CREATE INDEX
    idx_podcast_pipeline_schedule_next_run_at
ON podcast_pipeline_schedule (
    next_run_at
);