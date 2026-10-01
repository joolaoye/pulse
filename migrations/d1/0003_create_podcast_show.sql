CREATE TABLE podcast_show (
    show_id TEXT PRIMARY KEY,

    title TEXT NOT NULL,
    description TEXT NOT NULL,
    author TEXT NOT NULL,

    website_url TEXT NOT NULL,
    artwork_url TEXT NOT NULL,

    category TEXT NOT NULL,
    language TEXT NOT NULL,

    explicit INTEGER NOT NULL
        CHECK (
            explicit IN (0, 1)
        ),

    verification_email TEXT,

    public_base_url TEXT NOT NULL,

    feed_object_key TEXT NOT NULL
        UNIQUE,

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
        )
);
