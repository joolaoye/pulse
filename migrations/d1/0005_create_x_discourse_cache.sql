CREATE TABLE IF NOT EXISTS x_discourse_cache (
    conversation_id TEXT PRIMARY KEY,
    discourse_json TEXT NOT NULL,
    latest_post_id TEXT NOT NULL,
    refreshed_at TEXT NOT NULL
);