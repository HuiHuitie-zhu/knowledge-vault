#!/usr/bin/env python3
"""Knowledge Vault — CLI tool for managing your personal knowledge base.

Usage:
  vault.py init                    Create DB from schema
  vault.py add <title> <content>   Add a note
  vault.py search <query>          Search notes (FTS5)
  vault.py search <query> --semantic  Semantic search
  vault.py list                    List recent notes
  vault.py stats                   Show health report
  vault.py reindex                Rebuild vectors
  vault.py reindex --graph        Rebuild vectors + typed edges
  vault.py consolidate            Find duplicates / issues

Examples:
  vault.py add "Python装饰器" "装饰器是修改函数行为的函数..." --tags python,技巧 --type reference
  vault.py add "Functools模块" "高阶函数工具集" --link-to 1 --link-type uses
  vault.py search "装饰器"
  vault.py stats
"""

import sqlite3, argparse, sys, os, json, re
from datetime import datetime
from textwrap import shorten

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.db")
SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# ─── Schema ─────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

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
    confidence  REAL NOT NULL DEFAULT 1.0,
    last_verified TEXT,
    usage_count  INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS note_embeddings (
    note_id INTEGER PRIMARY KEY,
    embedding BLOB,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
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
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (from_note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (to_note_id)   REFERENCES notes(id) ON DELETE CASCADE
);

-- FTS5 full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title, content_raw, summary_raw, tags_text,
    content='notes', content_rowid='id',
    tokenize='unicode61'
);

-- FTS5 sync triggers
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, title, content_raw, summary_raw, tags_text)
    VALUES (new.id, new.title, new.content_raw, new.summary_raw, new.tags_text);
END;

CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content_raw, summary_raw, tags_text)
    VALUES ('delete', old.id, old.title, old.content_raw, old.summary_raw, old.tags_text);
END;

CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    INSERT INTO notes_fts(notes_fts, rowid, title, content_raw, summary_raw, tags_text)
    VALUES ('delete', old.id, old.title, old.content_raw, old.summary_raw, old.tags_text);
    INSERT INTO notes_fts(rowid, title, content_raw, summary_raw, tags_text)
    VALUES (new.id, new.title, new.content_raw, new.summary_raw, new.tags_text);
END;

-- For compatibility with some existing setups
CREATE TABLE IF NOT EXISTS note_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id  INTEGER NOT NULL,
    target_id  INTEGER NOT NULL,
    relation   TEXT NOT NULL DEFAULT 'references',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE
);
"""

# ─── Helpers ────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def ensure_schema():
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── Commands ───────────────────────────────────────────────────────────────

def cmd_init():
    ensure_schema()
    print(f"[vault] DB initialized at {DB}")

def cmd_add(args):
    conn = get_conn()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []

    # Insert note
    cur = conn.execute(
        "INSERT INTO notes (title, content_raw, summary_raw, tags_text, source_type, layer, domain) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (args.title, args.content, args.content[:200], " ".join(tags),
         args.type, args.layer, "tech")
    )
    note_id = cur.lastrowid
    conn.commit()

    # Handle tags
    for tag in tags:
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        tag_id = conn.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()["id"]
        conn.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                     (note_id, tag_id))
    conn.commit()

    # Handle link-to
    if args.link_to:
        conn.execute(
            "INSERT INTO links (from_note_id, to_note_id, link_type, link_source) "
            "VALUES (?, ?, ?, 'manual')",
            (note_id, args.link_to, args.link_type)
        )
        conn.commit()

    conn.close()
    print(f"[vault] Added #{note_id}: {args.title}")

def cmd_list(args):
    conn = get_conn()
    limit = args.limit if not args.full else 9999
    rows = conn.execute(
        "SELECT id, title, source_type, tags_text, layer, pinned, created_at "
        "FROM notes ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    print(f"{'#':>4} {'层':>2} {'类型':<10} {'标题':<40} {'标签'}")
    print("-" * 80)
    for r in rows:
        pin = "📌" if r["pinned"] else "  "
        print(f"{r['id']:>4} {r['layer']:>2} {r['source_type']:<10} "
              f"{shorten(r['title'], 38)} {r['tags_text'][:20]}")

def cmd_search(args):
    conn = get_conn()
    if args.semantic:
        print("[vault] Semantic search requires BGE embedding model.")
        print("[vault] Install: pip install fastembed")
        print("[vault] Then: from fastembed import TextEmbedding")
        print("[vault] Falling back to FTS5...")

    query = args.query
    rows = conn.execute(
        "SELECT id, title, source_type, tags_text, substr(content_raw, 1, 120) AS preview "
        "FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank LIMIT 10",
        (query,)
    ).fetchall()
    conn.close()

    if not rows:
        print(f"[vault] No results for '{query}'")
        return

    print(f"[vault] Results for '{query}':")
    for r in rows:
        print(f"  #{r['id']} [{r['source_type']}] {r['title']}")
        print(f"       {r['preview'][:80]}...")

def cmd_stats():
    conn = get_conn()
    notes = conn.execute("SELECT COUNT(*) AS c FROM notes").fetchone()["c"]
    tags = conn.execute("SELECT COUNT(*) AS c FROM tags").fetchone()["c"]
    links = conn.execute("SELECT COUNT(*) AS c FROM links").fetchone()["c"]
    emb = conn.execute("SELECT COUNT(*) AS c FROM note_embeddings").fetchone()["c"]

    layers = conn.execute(
        "SELECT layer, COUNT(*) AS c FROM notes GROUP BY layer ORDER BY layer"
    ).fetchall()

    types = conn.execute(
        "SELECT source_type, COUNT(*) AS c FROM notes GROUP BY source_type ORDER BY c DESC"
    ).fetchall()

    conn.close()
    print(f"笔记: {notes}  标签: {tags}  关联: {links}  向量: {emb}")
    print(f"分层: " + "  ".join(f"L{r['layer']}={r['c']}" for r in layers))
    print(f"类型: " + "  ".join(f"{r['source_type']}={r['c']}" for r in types))

def cmd_reindex(args):
    print("[vault] Rebuilding FTS5 index...")
    conn = get_conn()
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()
    print("[vault] FTS5 index rebuilt.")

    if args.graph:
        print("[vault] Rebuilding typed edges (auto-inference)...")
        conn = get_conn()
        conn.execute("DELETE FROM links WHERE link_source='auto'")
        # Simple auto-linking: same tag = reference
        tag_links = conn.execute("""
            SELECT DISTINCT nt1.note_id AS a, nt2.note_id AS b
            FROM note_tags nt1
            JOIN note_tags nt2 ON nt1.tag_id = nt2.tag_id AND nt1.note_id < nt2.note_id
        """).fetchall()
        for row in tag_links:
            conn.execute(
                "INSERT OR IGNORE INTO links (from_note_id, to_note_id, link_type, link_source) "
                "VALUES (?, ?, 'references', 'auto')",
                (row["a"], row["b"])
            )
        conn.commit()
        conn.close()
        print(f"[vault] Auto-linked {len(tag_links)} note pairs.")

def cmd_consolidate():
    print("[vault] Checking for potential issues...")
    conn = get_conn()
    # Check notes with missing content
    empty = conn.execute(
        "SELECT id, title FROM notes WHERE length(trim(content_raw)) < 5"
    ).fetchall()
    if empty:
        print(f"  ⚠ {len(empty)} notes with near-empty content:")
        for r in empty[:5]:
            print(f"    #{r['id']} {r['title']}")
    else:
        print("  ✓ All notes have content")

    # Check dangling links
    dangling = conn.execute("""
        SELECT l.id FROM links l
        LEFT JOIN notes n1 ON l.from_note_id = n1.id
        LEFT JOIN notes n2 ON l.to_note_id = n2.id
        WHERE n1.id IS NULL OR n2.id IS NULL
    """).fetchall()
    if dangling:
        print(f"  ⚠ {len(dangling)} dangling links")
    else:
        print("  ✓ No dangling links")

    conn.close()
    print("[vault] Consolidation report complete (advisory only, no changes made)")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Knowledge Vault CLI")
    sub = p.add_subparsers(dest="cmd")

    # init
    sub.add_parser("init")

    # add
    a = sub.add_parser("add")
    a.add_argument("title")
    a.add_argument("content")
    a.add_argument("--tags", default="", help="comma-separated tags")
    a.add_argument("--type", default="reference",
                   choices=["rule", "trap", "reference", "note", "standard", "checklist", "case", "doc"])
    a.add_argument("--layer", type=int, default=2, choices=[0, 1, 2])
    a.add_argument("--link-to", type=int, help="link to existing note ID")
    a.add_argument("--link-type", default="references",
                   choices=["references", "related_to", "uses", "builds_on", "part_of",
                            "similar_to", "contradicts", "created", "mentions"])

    # search
    a = sub.add_parser("search")
    a.add_argument("query")
    a.add_argument("--semantic", action="store_true")

    # list
    a = sub.add_parser("list")
    a.add_argument("--limit", type=int, default=20)
    a.add_argument("--full", action="store_true")

    # stats
    sub.add_parser("stats")

    # reindex
    a = sub.add_parser("reindex")
    a.add_argument("--graph", action="store_true")

    # consolidate
    sub.add_parser("consolidate")

    args = p.parse_args()

    if not args.cmd:
        p.print_help()
        return

    if args.cmd == "init":
        cmd_init()
    elif args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "search":
        cmd_search(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "reindex":
        cmd_reindex(args)
    elif args.cmd == "consolidate":
        cmd_consolidate()


if __name__ == "__main__":
    main()
