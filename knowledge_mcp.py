#!/usr/bin/env python3
"""Knowledge Vault — MCP protocol server for AI Agents.

Provides 9 tools for reading and writing the knowledge base via the
Model Context Protocol. Compatible with any MCP client (Claude Code,
Cursor, custom Agent frameworks, etc.).

Usage:
  Register in your .mcp.json and let your AI Agent handle the rest.
  Or run stand-alone for testing:
    python3 knowledge_mcp.py

Tools:
  knowledge_search          FTS5 keyword search (with type/layer/domain filters)
  knowledge_hybrid_search   FTS5 + graph RRF hybrid search
  knowledge_semantic_search Semantic vector search (requires fastembed)
  knowledge_list            List notes with filters
  knowledge_get             Get a single note's full content
  knowledge_graph           BFS knowledge graph traversal
  knowledge_add             Create a new note
  knowledge_update          Update an existing note
  knowledge_delete          Delete a note (cascades tags and links)

Environment:
  KNOWLEDGE_DB_PATH   Path to the SQLite database (default: ./vault.db)
"""

import json, sys, sqlite3, os, re

DB = os.environ.get(
    "KNOWLEDGE_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.db"),
)


# ── Type filter map ─────────────────────────────────────────
# Groups source_type values into two conceptual layers for
# AI Agent consumption: "calibrate" (rules/standards) vs
# "retrieve" (reference/notes).

TYPE_FILTERS = {
    "calibrate": ("calibrate", ("rule", "checklist", "trap", "standard", "case")),
    "retrieve": ("retrieve", ("reference", "doc", "note")),
}


def apply_type_filter(sql_where, params, search_type):
    """Append source_type filter for calibrate/retrieve/all."""
    if search_type and search_type in TYPE_FILTERS:
        _label, types = TYPE_FILTERS[search_type]
        placeholders = ",".join("?" for _ in types)
        clause = f"n.source_type IN ({placeholders})"
        sql_where = f"{sql_where} AND {clause}" if sql_where else clause
        params = list(params) + list(types)
    return sql_where, tuple(params)


def apply_layer_filter(sql_where, params, layer):
    """Append layer filter (0 / 1 / 2)."""
    if layer is not None:
        clause = "n.layer=?"
        sql_where = f"{sql_where} AND {clause}" if sql_where else clause
        params = list(params) + [layer]
    return sql_where, tuple(params)


def apply_domain_filter(sql_where, params, domain):
    """Append domain filter."""
    if domain:
        clause = "n.domain=?"
        sql_where = f"{sql_where} AND {clause}" if sql_where else clause
        params = list(params) + [domain]
    return sql_where, tuple(params)


# ── MCP wire protocol ──────────────────────────────────────


def respond(data):
    msg = json.dumps(data)
    sys.stdout.write(f"Content-Length: {len(msg)}\r\n\r\n{msg}")
    sys.stdout.flush()


def read_request():
    raw_header = b""
    while True:
        ch = sys.stdin.buffer.read(1)
        if not ch:
            return None
        raw_header += ch
        if raw_header.endswith(b"\r\n\r\n"):
            break
    m = re.search(rb"Content-Length:\s*(\d+)", raw_header)
    if not m:
        return None
    length = int(m.group(1))
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


# ── Query helpers ──────────────────────────────────────────

BASE_COLS = (
    "n.id, n.title, substr(n.content_raw,1,300) as content, "
    "n.created_at, n.tags_text, n.confidence, n.last_verified, "
    "n.source_type, n.usage_count, n.success_count, n.fail_count, n.layer, n.domain"
)

TABLE = "notes n"
FTS_TABLE = "notes_fts"


def search_notes(query, limit=5, search_type=None, layer=None, domain=None):
    """FTS5 keyword search with LIKE fallback. Supports type/layer/domain filters."""
    where, params = apply_type_filter("notes_fts MATCH ?", [query], search_type)
    where, params = apply_layer_filter(where, params, layer)
    where, params = apply_domain_filter(where, params, domain)
    sql = f"SELECT {BASE_COLS} FROM notes_fts f JOIN notes n ON f.rowid = n.id"
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY rank LIMIT ?"

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params + (limit,)).fetchall()
    except Exception:
        rows = []
    conn.close()

    if rows:
        return [dict(r) for r in rows]

    # LIKE fallback (preserving type/layer/domain filters)
    cols = BASE_COLS.replace("n.", "")
    where2, params2 = apply_type_filter(
        "(content_raw LIKE ? OR title LIKE ?)",
        [f"%{query}%", f"%{query}%"],
        search_type,
    )
    where2, params2 = apply_layer_filter(where2, params2, layer)
    where2, params2 = apply_domain_filter(where2, params2, domain)
    sql2 = f"SELECT {cols} FROM notes n"
    if where2:
        sql2 += f" WHERE {where2}"
    sql2 += " LIMIT ?"

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql2, params2 + (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def semantic_search(query, limit=5, search_type=None, layer=None, domain=None):
    """Semantic vector search via BGE embeddings (requires fastembed)."""
    try:
        from fastembed import TextEmbedding
        import numpy as np

        embedder = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
        query_vec = np.array(list(embedder.query_embed(query))[0])

        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row

        # Get all note embeddings (or use a smarter retrieval strategy)
        candidates = conn.execute(
            "SELECT ne.note_id, ne.embedding FROM note_embeddings ne"
        ).fetchall()

        results = []
        for row in candidates:
            stored = np.frombuffer(row["embedding"], dtype=np.float32)
            score = float(np.dot(query_vec, stored) / (np.linalg.norm(query_vec) * np.linalg.norm(stored)))
            results.append((row["note_id"], score))

        results.sort(key=lambda x: x[1], reverse=True)
        top_ids = [r[0] for r in results[:limit]]

        enriched = []
        cols = BASE_COLS.replace("n.", "")
        for nid in top_ids:
            stmt = f"SELECT {cols} FROM notes WHERE id=?"
            where, p = apply_type_filter("", [], search_type)
            if where:
                stmt += f" AND {where}"
            row = conn.execute(stmt, [nid] + list(p)).fetchone()
            if row:
                enriched.append(dict(row))
        conn.close()
        return enriched if enriched else results[:limit]

    except ImportError:
        return {"error": "Semantic search requires fastembed: pip install fastembed"}
    except Exception as e:
        return {"error": f"Semantic search failed: {str(e)}"}


def list_notes(limit=20, tag=None, search_type=None, layer=None, domain=None):
    """List notes with optional type/layer/domain/tag filtering."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    cols = BASE_COLS.replace("n.", "")
    where_parts = []
    params = []

    if search_type and search_type in TYPE_FILTERS:
        _label, types = TYPE_FILTERS[search_type]
        placeholders = ",".join("?" for _ in types)
        where_parts.append(f"n.source_type IN ({placeholders})")
        params.extend(types)

    if tag:
        where_parts.append("t.name=?")
        params.append(tag)

    if layer is not None:
        where_parts.append("n.layer=?")
        params.append(layer)

    if domain:
        where_parts.append("n.domain=?")
        params.append(domain)

    where = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    if tag:
        rows = conn.execute(
            f"SELECT {cols} FROM notes n "
            "JOIN note_tags nt ON n.id=nt.note_id JOIN tags t ON nt.tag_id=t.id "
            f"{where} ORDER BY n.updated_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {cols} FROM notes n {where} ORDER BY n.updated_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_note(note_id):
    """Get full note content by ID."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    return dict(r) if r else None


# ── Graph traversal ────────────────────────────────────────


def query_graph(note_id, max_depth=2, limit=10):
    """BFS traversal of the knowledge graph starting from a note."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    edges = []
    visited = {note_id}
    current = [note_id]
    depth = 0

    while current and depth < max_depth:
        placeholders = ",".join("?" for _ in current)
        rows = conn.execute(
            f"""
            SELECT l.from_note_id, l.to_note_id, l.link_type,
                   n_from.title as from_title, n_to.title as to_title
            FROM links l
            JOIN notes n_from ON l.from_note_id = n_from.id
            JOIN notes n_to ON l.to_note_id = n_to.id
            WHERE l.from_note_id IN ({placeholders})
               OR l.to_note_id IN ({placeholders})
            """,
            current * 2,
        ).fetchall()

        next_batch = set()
        for r in rows:
            edges.append(dict(r))
            if r["from_note_id"] not in visited:
                next_batch.add(r["from_note_id"])
            if r["to_note_id"] not in visited:
                next_batch.add(r["to_note_id"])

        visited.update(current)
        current = list(next_batch - visited)
        depth += 1

    conn.close()

    # Deduplicate
    seen = set()
    unique = []
    for e in edges:
        key = (e["from_note_id"], e["to_note_id"], e["link_type"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:limit]


# ── Write tools ────────────────────────────────────────────


def add_note(
    title,
    content_raw,
    summary_raw="",
    source="",
    source_ref="",
    tags_text="",
    source_type="note",
    layer=2,
    domain="tech",
    confidence=0.8,
    tags=None,
):
    """Create a new note. FTS index is maintained automatically by SQLite triggers."""
    conn = sqlite3.connect(DB)
    try:
        cur = conn.execute(
            """
            INSERT INTO notes (title, content_raw, summary_raw, source, source_ref,
                               tags_text, source_type, layer, domain, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (title, content_raw, summary_raw, source, source_ref,
             tags_text, source_type, layer, domain, confidence),
        )
        note_id = cur.lastrowid

        # Associate existing tags
        if tags:
            for tag_name in tags:
                t = conn.execute(
                    "SELECT id FROM tags WHERE name=?", (tag_name,)
                ).fetchone()
                if t:
                    conn.execute(
                        "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                        (note_id, t[0]),
                    )
        conn.commit()
        return {"success": True, "note_id": note_id}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def update_note(
    note_id,
    title=None,
    content_raw=None,
    summary_raw=None,
    source=None,
    source_ref=None,
    tags_text=None,
    source_type=None,
    layer=None,
    domain=None,
    confidence=None,
):
    """Update a note. Only provided fields are changed (None = skip)."""
    fields = []
    params = []
    for k, v in [
        ("title", title),
        ("content_raw", content_raw),
        ("summary_raw", summary_raw),
        ("source", source),
        ("source_ref", source_ref),
        ("tags_text", tags_text),
        ("source_type", source_type),
        ("layer", layer),
        ("domain", domain),
        ("confidence", confidence),
    ]:
        if v is not None:
            fields.append(f"{k}=?")
            params.append(v)

    if not fields:
        return {"success": False, "error": "No fields to update"}

    params.append(note_id)
    conn = sqlite3.connect(DB)
    try:
        conn.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id=?", params)
        if conn.total_changes == 0:
            conn.rollback()
            return {"success": False, "error": f"Note {note_id} not found"}
        conn.commit()
        return {"success": True, "note_id": note_id}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def delete_note(note_id):
    """Delete a note. Cascades to tags, links, and FTS index automatically."""
    conn = sqlite3.connect(DB)
    try:
        conn.execute("DELETE FROM links WHERE from_note_id=? OR to_note_id=?", (note_id, note_id))
        conn.execute("DELETE FROM note_tags WHERE note_id=?", (note_id,))
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        if conn.total_changes == 0:
            conn.rollback()
            return {"success": False, "error": f"Note {note_id} not found"}
        conn.commit()
        return {"success": True, "note_id": note_id}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ── Hybrid search (FTS5 + graph RRF) ──────────────────────


def hybrid_search_notes(query, limit=5, search_type=None, layer=None, domain=None):
    """FTS5 + graph RRF fused search. First pass: FTS5; second pass: graph neighbors."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # 1. FTS5 primary pass
    where, params = apply_type_filter("notes_fts MATCH ?", [query], search_type)
    where, params = apply_layer_filter(where, params, layer)
    where, params = apply_domain_filter(where, params, domain)
    sql = f"SELECT {BASE_COLS}, rank FROM notes_fts f JOIN notes n ON f.rowid = n.id"
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY rank LIMIT ?"

    try:
        fts_rows = conn.execute(sql, params + (limit * 2,)).fetchall()
    except Exception:
        fts_rows = []

    fts_map = {}
    fts_ids = set()
    for i, r in enumerate(fts_rows):
        d = dict(r)
        d["_fts_rank"] = i + 1
        d["_score"] = 1.0 / (i + 1)
        d["_source"] = "fts5"
        fts_map[r["id"]] = d
        fts_ids.add(r["id"])

    # 2. Graph pass: neighbors of FTS5 results
    if fts_ids:
        placeholders = ",".join("?" for _ in fts_ids)
        graph_candidates = {}
        for fid in fts_ids:
            neighbors = conn.execute(
                f"""
                SELECT l.to_note_id AS nid, COUNT(*) AS w
                FROM links l WHERE l.from_note_id = ? AND l.to_note_id NOT IN ({placeholders})
                GROUP BY l.to_note_id
                UNION ALL
                SELECT l.from_note_id AS nid, COUNT(*) AS w
                FROM links l WHERE l.to_note_id = ? AND l.from_note_id NOT IN ({placeholders})
                GROUP BY l.from_note_id
            """,
                (fid, *fts_ids, fid, *fts_ids),
            ).fetchall()
            for n in neighbors:
                gid = n["nid"]
                if gid in fts_ids:
                    continue
                graph_candidates[gid] = graph_candidates.get(gid, 0) + n["w"]

        for gid, weight in graph_candidates.items():
            if weight < 1:
                continue
            row = conn.execute(
                f"SELECT {BASE_COLS.replace('n.', '')} FROM notes WHERE id=?", (gid,)
            ).fetchone()
            if row:
                d = dict(row)
                # Apply filters to graph candidates too
                if search_type:
                    tmap = {
                        "calibrate": ("rule", "checklist", "trap", "standard", "case"),
                        "retrieve": ("reference", "doc", "note"),
                    }
                    if search_type in tmap and d.get("source_type", "") not in tmap[search_type]:
                        continue
                if layer is not None and d.get("layer") != layer:
                    continue
                if domain and d.get("domain") != domain:
                    continue
                d["_source"] = "graph"
                d["_score"] = None
                fts_map[gid] = d

    conn.close()

    # 3. Merge: FTS5 first, graph neighbors after
    fts_results = [v for v in fts_map.values() if v["_source"] == "fts5"]
    graph_results = [v for v in fts_map.values() if v["_source"] == "graph"]
    merged = fts_results + graph_results
    return merged[:limit]


# ── Tool definitions ───────────────────────────────────────

TOOLS = {
    "knowledge_search": {
        "description": "Search knowledge base (FTS5 keyword). type=calibrate/retrieve, layer=0/1/2, domain=profile/fiction/tech/note/project/infra",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword(s)"},
                "limit": {"type": "integer", "default": 5},
                "type": {
                    "type": "string",
                    "enum": ["calibrate", "retrieve", "all"],
                },
                "layer": {
                    "type": "integer",
                    "description": "0=ironclad rules, 1=cognitive calibrator, 2=knowledge records",
                },
                "domain": {
                    "type": "string",
                    "enum": ["profile", "fiction", "tech", "note", "project", "infra"],
                    "description": "profile=personal, fiction=novel, tech=technical, note=notes, project=project, infra=infrastructure",
                },
            },
            "required": ["query"],
        },
        "handler": lambda args: search_notes(
            args["query"],
            args.get("limit", 5),
            args.get("type"),
            args.get("layer"),
            args.get("domain"),
        ),
    },
    "knowledge_hybrid_search": {
        "description": "Hybrid search (FTS5 + graph RRF). type/layer/domain filters apply.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
                "type": {"type": "string", "enum": ["calibrate", "retrieve", "all"]},
                "layer": {"type": "integer"},
                "domain": {
                    "type": "string",
                    "enum": ["profile", "fiction", "tech", "note", "project", "infra"],
                },
            },
            "required": ["query"],
        },
        "handler": lambda args: hybrid_search_notes(
            args["query"],
            args.get("limit", 5),
            args.get("type"),
            args.get("layer"),
            args.get("domain"),
        ),
    },
    "knowledge_semantic_search": {
        "description": "Semantic vector search via BGE embeddings (requires fastembed). type/layer/domain filters apply.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
                "type": {"type": "string", "enum": ["calibrate", "retrieve", "all"]},
                "layer": {"type": "integer"},
                "domain": {
                    "type": "string",
                    "enum": ["profile", "fiction", "tech", "note", "project", "infra"],
                },
            },
            "required": ["query"],
        },
        "handler": lambda args: semantic_search(
            args["query"],
            args.get("limit", 5),
            args.get("type"),
            args.get("layer"),
            args.get("domain"),
        ),
    },
    "knowledge_list": {
        "description": "List notes with type/layer/domain/tag filtering.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "tag": {"type": "string", "description": "Filter by tag name"},
                "type": {"type": "string", "enum": ["calibrate", "retrieve", "all"]},
                "layer": {"type": "integer"},
                "domain": {
                    "type": "string",
                    "enum": ["profile", "fiction", "tech", "note", "project", "infra"],
                },
            },
        },
        "handler": lambda args: list_notes(
            args.get("limit", 20),
            args.get("tag"),
            args.get("type"),
            args.get("layer"),
            args.get("domain"),
        ),
    },
    "knowledge_get": {
        "description": "Get a single note's full content by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_id": {"type": "integer", "description": "Note ID"}
            },
            "required": ["note_id"],
        },
        "handler": lambda args: get_note(args["note_id"]),
    },
    "knowledge_graph": {
        "description": "BFS traversal of the knowledge graph from a starting note. Returns connected notes with relationship types.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_id": {"type": "integer", "description": "Start note ID"},
                "max_depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "Max traversal depth",
                },
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["note_id"],
        },
        "handler": lambda args: query_graph(
            args["note_id"], args.get("max_depth", 2), args.get("limit", 10)
        ),
    },
    "knowledge_add": {
        "description": "Create a new knowledge entry. title + content_raw are required. FTS index is auto-maintained.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title"},
                "content_raw": {"type": "string", "description": "Markdown content"},
                "summary_raw": {"type": "string", "description": "Optional summary"},
                "source": {"type": "string", "description": "Source (optional)"},
                "source_ref": {
                    "type": "string",
                    "description": "Source reference URL (optional)",
                },
                "tags_text": {
                    "type": "string",
                    "description": "Space-separated tags (optional)",
                },
                "source_type": {
                    "type": "string",
                    "default": "note",
                    "enum": [
                        "rule",
                        "checklist",
                        "trap",
                        "standard",
                        "case",
                        "reference",
                        "doc",
                        "note",
                    ],
                },
                "layer": {
                    "type": "integer",
                    "default": 2,
                    "description": "0=ironclad, 1=calibrator, 2=reference",
                },
                "domain": {
                    "type": "string",
                    "default": "tech",
                    "enum": ["profile", "fiction", "tech", "note", "project", "infra"],
                },
                "confidence": {"type": "number", "default": 0.8},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Existing tag names to associate (must already exist in tags table)",
                },
            },
            "required": ["title", "content_raw"],
        },
        "handler": lambda args: add_note(
            args["title"],
            args["content_raw"],
            args.get("summary_raw", ""),
            args.get("source", ""),
            args.get("source_ref", ""),
            args.get("tags_text", ""),
            args.get("source_type", "note"),
            args.get("layer", 2),
            args.get("domain", "tech"),
            args.get("confidence", 0.8),
            args.get("tags", None),
        ),
    },
    "knowledge_update": {
        "description": "Update an existing note. Only provided fields change (None = skip). FTS index auto-maintained.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_id": {"type": "integer", "description": "Note ID"},
                "title": {"type": "string"},
                "content_raw": {"type": "string"},
                "summary_raw": {"type": "string"},
                "source": {"type": "string"},
                "source_ref": {"type": "string"},
                "tags_text": {"type": "string"},
                "source_type": {
                    "type": "string",
                    "enum": [
                        "rule",
                        "checklist",
                        "trap",
                        "standard",
                        "case",
                        "reference",
                        "doc",
                        "note",
                    ],
                },
                "layer": {"type": "integer"},
                "domain": {
                    "type": "string",
                    "enum": ["profile", "fiction", "tech", "note", "project", "infra"],
                },
                "confidence": {"type": "number"},
            },
            "required": ["note_id"],
        },
        "handler": lambda args: update_note(
            args["note_id"],
            args.get("title"),
            args.get("content_raw"),
            args.get("summary_raw"),
            args.get("source"),
            args.get("source_ref"),
            args.get("tags_text"),
            args.get("source_type"),
            args.get("layer"),
            args.get("domain"),
            args.get("confidence"),
        ),
    },
    "knowledge_delete": {
        "description": "Delete a note. Cascades to tags, links, and FTS index automatically.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "Note ID to delete",
                }
            },
            "required": ["note_id"],
        },
        "handler": lambda args: delete_note(args["note_id"]),
    },
}


# ── Main loop (standard MCP protocol) ─────────────────────


def main():
    """Standard MCP protocol loop. Compatible with Claude Code and other MCP clients."""
    initialized = False

    while True:
        req = read_request()
        if req is None:
            break
        method = req.get("method")
        _id = req.get("id")

        if method == "initialize":
            respond(
                {
                    "jsonrpc": "2.0",
                    "id": _id,
                    "result": {
                        "protocolVersion": "0.1.0",
                        "serverInfo": {
                            "name": "knowledge-mcp",
                            "version": "2.1.0",
                        },
                        "capabilities": {"tools": {}},
                    },
                }
            )

        elif method == "notifications/initialized":
            initialized = True

        elif method == "tools/list":
            respond(
                {
                    "jsonrpc": "2.0",
                    "id": _id,
                    "result": {
                        "tools": [
                            {
                                "name": name,
                                "description": t["description"],
                                "inputSchema": t["parameters"],
                            }
                            for name, t in TOOLS.items()
                        ]
                    },
                }
            )

        elif method == "tools/call":
            tool_name = req["params"]["name"]
            args = req["params"].get("arguments", {})
            tool = TOOLS.get(tool_name)
            if tool:
                try:
                    result = tool["handler"](args)
                    respond({"jsonrpc": "2.0", "id": _id, "result": result})
                except Exception as e:
                    respond(
                        {
                            "jsonrpc": "2.0",
                            "id": _id,
                            "error": {"code": -1, "message": str(e)},
                        }
                    )
            else:
                respond(
                    {
                        "jsonrpc": "2.0",
                        "id": _id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}",
                        },
                    }
                )

        elif method == "notifications/cancelled":
            pass

        else:
            if _id:
                respond(
                    {
                        "jsonrpc": "2.0",
                        "id": _id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {method}",
                        },
                    }
                )


if __name__ == "__main__":
    main()
