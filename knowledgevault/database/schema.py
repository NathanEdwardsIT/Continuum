"""SQLite schema definitions and migrations."""

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS note_categories (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, category_id)
);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

CREATE TABLE IF NOT EXISTS note_folders (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, folder_id)
);

CREATE TABLE IF NOT EXISTS backlinks (
    source_note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    strength REAL NOT NULL DEFAULT 0.0,
    reason TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (source_note_id, target_note_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    content,
    categories,
    tags,
    content='notes_fts_content',
    content_rowid='note_id'
);

CREATE TABLE IF NOT EXISTS notes_fts_content (
    note_id INTEGER PRIMARY KEY,
    title TEXT,
    content TEXT,
    categories TEXT,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_modified ON notes(modified_at);
CREATE INDEX IF NOT EXISTS idx_backlinks_source ON backlinks(source_note_id);
CREATE INDEX IF NOT EXISTS idx_backlinks_target ON backlinks(target_note_id);
CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id);
"""

FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS notes_fts_ai AFTER INSERT ON notes_fts_content BEGIN
    INSERT INTO notes_fts(rowid, title, content, categories, tags)
    VALUES (new.note_id, new.title, new.content, new.categories, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_ad AFTER DELETE ON notes_fts_content BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, categories, tags)
    VALUES ('delete', old.note_id, old.title, old.content, old.categories, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_au AFTER UPDATE ON notes_fts_content BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content, categories, tags)
    VALUES ('delete', old.note_id, old.title, old.content, old.categories, old.tags);
    INSERT INTO notes_fts(rowid, title, content, categories, tags)
    VALUES (new.note_id, new.title, new.content, new.categories, new.tags);
END;
"""
