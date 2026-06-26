#!/usr/bin/env python3
"""Knowledge Vault — HTTP API server (~50 lines).

Endpoints:
  GET /api/data    → all nodes + links for the graph
  GET /api/node?id → full content of one node
  GET /api/pin?id  → toggle pinned state
  GET /            → serve index.html (knowledge graph frontend)
"""

import json, os, sqlite3, http.server, urllib.parse

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault.db")
PORT = 51420
_HERE = os.path.dirname(os.path.abspath(__file__))

# Node colors by type
NC = {
    "rule": "#4a90d9", "checklist": "#7b68ee", "trap": "#34d399",
    "standard": "#fbbf24", "case": "#f472b6", "reference": "#a78bfa",
    "doc": "#f97316", "note": "#94a3b8",
}

# Edge colors by type
EC = {
    "references": "#5a5a7a", "related_to": "#5a5a7a", "works_at": "#5e6ad2",
    "created": "#22c55e", "uses": "#22c55e", "mentions": "#94a3b8",
    "builds_on": "#f59e0b", "contradicts": "#ef4444", "similar_to": "#8b5cf6",
    "part_of": "#6366f1",
}

def get_data():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    ns = conn.execute(
        "SELECT id,title,source_type,tags_text,substr(content_raw,1,200)as preview,pinned "
        "FROM notes"
    ).fetchall()
    ls = conn.execute(
        "SELECT from_note_id AS s,to_note_id AS t,link_type AS r FROM links "
        "UNION ALL SELECT source_id,target_id,relation FROM note_links"
    ).fetchall()
    conn.close()
    v = {n["id"] for n in ns}
    return {
        "nodes": [{
            "i": n["id"], "n": n["title"],
            "c": NC.get(n["source_type"], "#94a3b8"),
            "tp": n["source_type"] or "n",
            "g": (n["tags_text"] or "").split(),
            "p": n["preview"], "pn": n["pinned"]
        } for n in ns],
        "links": [{
            "s": l["s"], "t": l["t"], "r": l["r"] or "references",
            "cl": EC.get(l["r"], "#5a5a7a")
        } for l in ls if l["s"] in v and l["t"] in v],
    }


INDEX_HTML = os.path.join(_HERE, "index.html")
PAGE = open(INDEX_HTML, encoding="utf-8").read() if os.path.exists(INDEX_HTML) else ""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/data":
            self.json(get_data())
        elif p == "/api/pin":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            nid = q.get("id", [None])[0]
            self.json(self.toggle_pin(int(nid)) if nid else {"e": "no id"})
        elif p.startswith("/api/node"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            nid = q.get("id", [None])[0]
            self.json(self.get_node(nid) if nid else {"e": "no id"})
        elif p == "/":
            self.send(200, "text/html", PAGE.encode("utf-8"))
        else:
            self.send_error(404)

    def get_node(self, nid):
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        r = conn.execute("SELECT * FROM notes WHERE id=?", (nid,)).fetchone()
        conn.close()
        return dict(r) if r else {"e": "not found"}

    def toggle_pin(self, nid):
        conn = sqlite3.connect(DB)
        conn.execute("UPDATE notes SET pinned=1-pinned WHERE id=?", (nid,))
        conn.commit()
        r = conn.execute("SELECT pinned FROM notes WHERE id=?", (nid,)).fetchone()
        conn.close()
        return {"id": nid, "pinned": r[0]} if r else {"e": "not found"}

    def send(self, code, ctype, data):
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)

    def json(self, obj):
        self.send(200, "application/json",
                  json.dumps(obj, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    if not os.path.exists(DB):
        print(f"[vault] DB not found at {DB}")
        print("[vault] Run 'python3 vault.py init' first, or 'python3 seed.py' for demo data.")
        exit(1)
    srv = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[vault] Server at http://localhost:{PORT}")
    srv.serve_forever()
