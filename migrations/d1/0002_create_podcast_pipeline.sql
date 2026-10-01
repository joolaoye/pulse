CREATE TABLE podcast_pipeline (
    pipeline_id TEXT PRIMARY KEY,

    show_id TEXT NOT NULL,

    podcast_profile_json TEXT NOT NULL,

    speakers_json TEXT NOT NULL,

    speaker_voice_bindings_json TEXT NOT NULL,

    interest_profile_markdown TEXT NOT NULL,

    x_list_id TEXT NOT NULL,

    target_episode_duration_seconds INTEGER NOT NULL
        CHECK (
            target_episode_duration_seconds > 0
        ),

    enabled INTEGER NOT NULL
        DEFAULT 1
        CHECK (
            enabled IN (0, 1)
        ),

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
        show_id
    )
    REFERENCES podcast_show (
        show_id
    )
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE INDEX
    idx_podcast_pipeline_show_id
ON podcast_pipeline (
    show_id
);

CREATE INDEX
    idx_podcast_pipeline_enabled
ON podcast_pipeline (
    enabled
);
