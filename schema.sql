-- Knowledge Vault — Database Schema
-- SQLite + FTS5 full-text search + vector embeddings + typed edges

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    content_raw TEXT NOT NULL DEFAULT '',
    content_seg TEXT NOT NULL DEFAULT '',
    summary_raw TEXT NOT NULL DEFAULT '',
    summary_seg TEXT NOT NULL DEFAULT '',
    tags_text   TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    source_ref  TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'reference',
    layer       INTEGER NOT NULL DEFAULT 2,
    domain      TEXT NOT NULL DEFAULT 'tech',
    pinned      INTEGER NOT NULL DEFAULT 0,
    confidence  REAL NOT NULL DEFAULT 0.8,
    last_verified TEXT,
    usage_count  INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS note_embeddings (
    note_id    INTEGER PRIMARY KEY,
    embedding  BLOB,
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL,
    tag_id  INTEGER NOT NULL,
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS links (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    from_note_id INTEGER NOT NULL,
    to_note_id   INTEGER NOT NULL,
    link_type    TEXT NOT NULL DEFAULT 'references',
    context      TEXT NOT NULL DEFAULT '',
    link_source  TEXT NOT NULL DEFAULT 'manual',
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (from_note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (to_note_id)   REFERENCES notes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_note_id);
CREATE INDEX IF NOT EXISTS idx_links_to   ON links(to_note_id);
CREATE INDEX IF NOT EXISTS idx_links_type ON links(link_type);

-- Compatibility table (some setups use the legacy note_links table for bidirectional graph)
CREATE TABLE IF NOT EXISTS note_links (
    source_id  INTEGER NOT NULL,
    target_id  INTEGER NOT NULL,
    relation   TEXT DEFAULT 'related',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (source_id, target_id),
    FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE
);

-- FTS5 full-text search virtual table (external content, auto-synced via triggers)
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title, content_raw, content_seg, summary_raw, summary_seg, tags_text,
    content='notes', content_rowid='id',
    tokenize='unicode61'
);

-- FTS5 sync triggers (INSERT / DELETE / UPDATE)
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, content_raw, content_seg, summary_raw, summary_seg, tags_text)
    VALUES (new.id, new.title, new.content_raw, new.content_seg, new.summary_raw, new.summary_seg, new.tags_text);
END;

CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content_raw, content_seg, summary_raw, summary_seg, tags_text)
    VALUES ('delete', old.id, old.title, old.content_raw, old.content_seg, old.summary_raw, old.summary_seg, old.tags_text);
END;

CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content_raw, content_seg, summary_raw, summary_seg, tags_text)
    VALUES ('delete', old.id, old.title, old.content_raw, old.content_seg, old.summary_raw, old.summary_seg, old.tags_text);
    INSERT INTO notes_fts(rowid, title, content_raw, content_seg, summary_raw, summary_seg, tags_text)
    VALUES (new.id, new.title, new.content_raw, new.content_seg, new.summary_raw, new.summary_seg, new.tags_text);
END;
