CREATE TABLE IF NOT EXISTS episode_publication (
    show_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    guid TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    published_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    audio_object_key TEXT NOT NULL,
    audio_size_bytes INTEGER NOT NULL,
    audio_content_type TEXT NOT NULL,
    created_at TEXT NOT NULL,

    PRIMARY KEY (
        show_id,
        episode_id
    ),

    UNIQUE (
        show_id,
        guid
    ),

    UNIQUE (
        show_id,
        audio_object_key
    )
);

CREATE INDEX IF NOT EXISTS
    idx_episode_publication_show_published_at
ON episode_publication (
    show_id,
    published_at DESC
);
