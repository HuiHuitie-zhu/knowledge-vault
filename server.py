#!/usr/bin/env python3
"""Knowledge Vault graph server.

Endpoints:
  GET /api/data     graph nodes and typed edges
  GET /api/summary  dashboard stats and recent notes
  GET /api/node     full note detail
  GET /api/pin      toggle pinned state
  GET /api/touch    increment usage_count for one note
  GET /api/print    printable / PDF-friendly note page
  GET /api/health   database and static asset health check
"""

import json, mimetypes, os, sqlite3, http.server, urllib.parse
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("KNOWLEDGE_DB_PATH", os.path.join(_HERE, "vault.db"))
PORT = int(os.environ.get("KNOWLEDGE_VAULT_PORT", "51420"))
NC = {"rule":"#4a90d9","checklist":"#7b68ee","trap":"#2ecc71","standard":"#f1c40f","case":"#e91e90","reference":"#9b59b6","doc":"#e67e22","note":"#95a5a6","implementation-log":"#14b8a6","architecture-decision":"#ef4444"}
EC = {"references":"#5a5a7a","related_to":"#5a5a7a","works_at":"#5e6ad2","created":"#22c55e","uses":"#22c55e","mentions":"#94a3b8","builds_on":"#f59e0b","contradicts":"#ef4444","similar_to":"#8b5cf6","part_of":"#6366f1","supersedes":"#e74c3c","conflicts_with":"#e67e22","complements":"#2ecc71","implements":"#06b6d4","depends_on":"#f97316","referenced_by":"#64748b"}

def get_data():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    ns = conn.execute("""
        SELECT id,title,source_type,tags_text,
               substr(content_raw,1,200) as preview,pinned,
               created_at,updated_at,confidence,last_verified,
               domain,usage_count
        FROM notes
    """).fetchall()
    ls = conn.execute("SELECT from_note_id AS s,to_note_id AS t,link_type AS r FROM links").fetchall()
    conn.close(); v = {n["id"] for n in ns}
    seen = set()
    deduped = []
    for l in ls:
        if l["s"] not in v or l["t"] not in v: continue
        key = (l["s"], l["t"], l["r"])
        if key in seen: continue
        seen.add(key)
        deduped.append(l)
    return {
        "nodes":[{"i":n["id"],"n":n["title"],"c":NC.get(n["source_type"],"#95a5a6"),"tp":n["source_type"]or"n","g":(n["tags_text"]or"").split(),"p":n["preview"],"pn":n["pinned"],"ca":n["created_at"]or None,"ua":n["updated_at"]or None,"cf":n["confidence"]or None,"lv":n["last_verified"]or None,"dm":n["domain"]or"","uc":n["usage_count"]or 0} for n in ns],
        "links":[{"s":l["s"],"t":l["t"],"r":l["r"]or"references","cl":EC.get(l["r"],"#5a5a7a")} for l in deduped]
    }

def build_summary():
    conn=sqlite3.connect(DB);conn.row_factory=sqlite3.Row
    total=conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    links=conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    verified=conn.execute("SELECT COUNT(*) FROM notes WHERE last_verified IS NOT NULL").fetchone()[0]
    recent_new=conn.execute("""
        SELECT id,title,source_type,tags_text,
               substr(content_raw,1,80) as preview,
               created_at,updated_at
        FROM notes WHERE created_at>=datetime('now','-7 days','localtime')
        ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    new_count=conn.execute(
        "SELECT COUNT(*) FROM notes WHERE created_at>=datetime('now','-7 days','localtime')"
    ).fetchone()[0]
    doms=conn.execute(
        "SELECT domain, COUNT(*) as c FROM notes GROUP BY domain ORDER BY c DESC"
    ).fetchall()
    stypes=conn.execute(
        "SELECT source_type, COUNT(*) as c FROM notes GROUP BY source_type ORDER BY c DESC"
    ).fetchall()
    recent_upd=conn.execute("""
        SELECT id,title,source_type,tags_text,
               substr(content_raw,1,80) as preview,created_at,updated_at
        FROM notes WHERE updated_at>=datetime('now','-7 days','localtime')
        ORDER BY updated_at DESC LIMIT 10
    """).fetchall()
    top_used=conn.execute(
        "SELECT id,title,source_type,usage_count FROM notes ORDER BY usage_count DESC LIMIT 5"
    ).fetchall()
    orp=conn.execute("""SELECT COUNT(*) FROM notes n WHERE n.id NOT IN
        (SELECT from_note_id FROM links UNION SELECT to_note_id FROM links)""").fetchone()[0]
    conn.close()
    return {
        "stats":{"total":total,"links":links,"verified":verified,"unverified":total-verified,
                 "orphan":orp,"recent_new":new_count},
        "recent_created":[{"i":r["id"],"n":r["title"][:50],"tp":r["source_type"],
            "g":(r["tags_text"]or"").split(),"ca":r["created_at"],"ua":r["updated_at"],
            "p":(r["preview"]or"")[:80]}for r in recent_new],
        "recent_updated":[{"i":r["id"],"n":r["title"][:50],"tp":r["source_type"],
            "ca":r["created_at"],"ua":r["updated_at"]}for r in recent_upd],
        "domains":[{"d":r["domain"],"c":r["c"]}for r in doms],
        "types":[{"t":r["source_type"],"c":r["c"]}for r in stypes],
        "top_used":[{"i":r["id"],"n":r["title"][:40],"u":r["usage_count"]}for r in top_used]
    }

def touch_node(nid):
    conn=sqlite3.connect(DB)
    conn.execute("UPDATE notes SET usage_count=usage_count+1 WHERE id=?",(nid,))
    conn.commit()
    r=conn.execute("SELECT usage_count FROM notes WHERE id=?",(nid,)).fetchone()
    conn.close();return{"id":nid,"usage_count":r[0]}if r else{"e":"not found"}

with open(os.path.join(_HERE, "index.html"), encoding="utf-8") as f:
    PAGE = f.read()
STATIC_FILES = {"d3.v7.min.js", "marked.min.js"}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/api/data": self.sj(get_data())
        elif p == "/api/summary": self.sj(build_summary())
        elif p == "/api/health": self.sj(self.hc())
        elif p.startswith("/api/print"): self.sp(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("id",[None])[0])
        elif p == "/api/touch":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            nid = q.get("id",[None])[0]
            self.sj(touch_node(int(nid)) if nid else {"e":"no id"})
        elif p == "/api/pin":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            nid = q.get("id",[None])[0]
            if nid: self.sj(self.tp(int(nid)))
            else: self.sj({"e":"no id"})
        elif p.startswith("/api/node"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            nid = q.get("id",[None])[0]
            self.sj(self.gn(nid)if nid else{"e":"no id"})
        elif p == "/": self.s(200,"text/html",PAGE.encode("utf-8"))
        elif p.startswith("/") and p[1:] in STATIC_FILES:
            self.sf(p[1:])
        else: self.send_error(404)
    def gn(self,nid):
        conn=sqlite3.connect(DB);conn.row_factory=sqlite3.Row
        r=conn.execute("SELECT * FROM notes WHERE id=?",(nid,)).fetchone()
        conn.close();return dict(r)if r else{"e":"not found"}
    def tp(self,nid):
        conn=sqlite3.connect(DB)
        conn.execute("UPDATE notes SET pinned=1-pinned WHERE id=?",(nid,))
        conn.commit()
        r=conn.execute("SELECT pinned FROM notes WHERE id=?",(nid,)).fetchone()
        conn.close();return{"id":nid,"pinned":r[0]}if r else{"e":"not found"}
    def tch(self,nid): return touch_node(nid)
    def hc(self):
        try:
            conn=sqlite3.connect(DB,timeout=1)
            n=conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            lk=conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
            emb=conn.execute("SELECT COUNT(*) FROM note_embeddings").fetchone()[0]
            fts=conn.execute("SELECT COUNT(*) FROM notes_fts").fetchone()[0]
            orp=conn.execute("""SELECT COUNT(*) FROM notes n WHERE n.id NOT IN
                (SELECT from_note_id FROM links UNION SELECT to_note_id FROM links)""").fetchone()[0]
            conn.close();db_ok=True
        except:db_ok=False;n=lk=emb=fts=orp=0
        so={}
        for fn in STATIC_FILES:so[fn]=os.path.exists(os.path.join(_HERE,fn))
        em=(emb==n) if emb>0 else True
        fs=(fts>=n) if n>0 else True
        if not db_ok:st="unhealthy"
        elif not em or not fs or orp>5:st="degraded"
        else:st="ok"
        return{"status":st,"timestamp":datetime.now().isoformat(),
            "checks":{"db_readable":db_ok,"notes":n,"links":lk,"embeddings":emb,
            "embeddings_match":em,"fts_rows":fts,"fts_sync":fs,
            "static_files":so,"orphan_nodes":orp}}
    def sp(self,nid):
        if not nid: self.send_error(400); return
        conn=sqlite3.connect(DB);conn.row_factory=sqlite3.Row
        r=conn.execute("SELECT * FROM notes WHERE id=?",(nid,)).fetchone()
        conn.close()
        if not r: self.send_error(404); return
        d=dict(r)
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
        tags="".join('<span class="t">'+t+"</span>" for t in (d.get("tags_text")or"").split() if t)
        src=d.get("source")or""
        ref=d.get("source_ref")or""
        src_html='<div class="s">来源: '+src+"</div>" if src else""
        ref_html='<div class="s">参考: '+ref+"</div>" if ref else""
        content=d.get("content_raw")or d.get("summary_raw")or""
        c_esc=json.dumps(content,ensure_ascii=False)
        t_esc=json.dumps(d["title"],ensure_ascii=False)
        page=('<html lang=zh-CN><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
            '<script src=/marked.min.js></script>'
            '<style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'html{font-size:16px}'
            '@media print{html{font-size:12pt}@page{margin:1.5cm}}'
            'body{font-family:"PingFang SC","Noto Sans SC","Inter","Helvetica Neue",sans-serif;'
            'padding:2rem;color:#1a1a1a;line-height:1.8;max-width:50rem;margin:0 auto}'
            '@media print{body{padding:0;max-width:none}}'
            'h1{font-size:1.6rem;font-weight:600;margin:0 0 .3rem;color:#111;line-height:1.3}'
            '.b{font-size:.8rem;color:#888;margin-bottom:.4rem}'
            '.m{font-size:.75rem;color:#999;margin-bottom:1.2rem;padding-bottom:.8rem;border-bottom:1px solid #eee}'
            '.t{display:inline-block;font-size:.75rem;padding:.1rem .6rem;border-radius:999px;background:#f0f0f0;color:#666;margin:.1rem .3rem .1rem 0}'
            '.s{font-size:.75rem;color:#999;margin:.3rem 0}'
            '.c{padding-top:1rem}'
            '.c h1,.c h2,.c h3,.c h4{font-weight:600;margin:1.5rem 0 .5rem;color:#111;line-height:1.4}'
            '.c h1{font-size:1.35rem}.c h2{font-size:1.2rem}.c h3{font-size:1.1rem}.c h4{font-size:1rem}'
            '.c p{margin:0 0 .7rem}'
            '.c ul,.c ol{padding-left:1.5rem;margin:.4rem 0 .7rem}'
            '.c li{margin:.2rem 0}'
            '.c code{font-family:"SF Mono","Menlo","Monaco","JetBrains Mono",monospace;'
            'font-size:.85em;background:#f4f4f4;padding:.1em .35em;border-radius:3px;word-break:break-word}'
            '.c pre{background:#f6f6f6;border-radius:6px;padding:.9rem;overflow-x:auto;'
            'border:1px solid #eee;margin:.7rem 0;white-space:pre-wrap;word-break:break-word}'
            '.c pre code{background:0;padding:0;font-size:.85em}'
            '.c table{border-collapse:collapse;margin:.7rem 0;width:100%;font-size:.85rem}'
            '.c th,.c td{padding:.4rem .6rem;border:1px solid #ddd;text-align:left}'
            '.c th{background:#f6f6f6;font-weight:500}'
            '.c blockquote{border-left:3px solid #ddd;padding:.3rem 1rem;margin:.7rem 0;color:#888;'
            'background:#fafafa;border-radius:0 4px 4px 0}'
            '.c img{max-width:100%;height:auto}.c a{color:#5e6ad2}'
            '.c hr{border:none;border-top:1px solid #eee;margin:1rem 0}'
            '@media print{.nb{display:none}.c pre{white-space:pre-wrap;page-break-inside:avoid}'
            '.c table{page-break-inside:avoid}.c blockquote{page-break-inside:avoid}}'
            '.nb{text-align:center;margin-bottom:1.5rem}'
            '.nb a{display:inline-block;padding:.5rem 1.5rem;background:#5e6ad2;color:#fff;border-radius:6px;text-decoration:none;font-size:.9rem;font-weight:500}'
            '.nb button{display:inline-block;margin-left:.5rem;padding:.5rem 1.5rem;background:#f0f0f0;color:#666;'
            'border-radius:6px;border:1px solid #ddd;font-size:.9rem;cursor:pointer;font-family:inherit}'
            '</style></head><body>'
            '<div class=nb><a href=/>← 返回知识图谱</a>'
            '<button onclick="window.print()">🖨 打印 / 保存为 PDF</button></div>'
            '<h1>'+d["title"]+'</h1>'
            '<div class=b>'+str(d.get("source_type")or"note")+' &middot; #'+str(d["id"])+'</div>'
            '<div class=m>导出时间: '+now+'</div>'
            '<div>'+tags+'</div>'
            +src_html+ref_html
            +'<div class=c id=c></div>'
            +'<script>'
            +'var c='+c_esc+';'
            +'var el=document.getElementById("c");'
            +'if(window.marked&&window.marked.parse){el.innerHTML=marked.parse(c)}'
            +'else if(window.marked){el.innerHTML=marked(c)}'
            +'else{el.textContent=c}'
            +'document.title='+t_esc+';'
            +'</script></body></html>')
        self.s(200,"text/html",page.encode("utf-8"))
    def s(self,c,t,d):
        self.send_response(c);self.send_header("Content-Type",t+"; charset=utf-8");self.end_headers();self.wfile.write(d)
    def sj(self,d):
        self.s(200,"application/json",json.dumps(d,ensure_ascii=False).encode("utf-8"))
    def sf(self,name):
        path=os.path.join(_HERE,name)
        try:
            with open(path,"rb") as f: data=f.read()
        except OSError:
            self.send_error(404);return
        self.s(200,mimetypes.guess_type(path)[0] or "application/octet-stream",data)

if __name__=="__main__":
    http.server.HTTPServer(("",PORT),H).serve_forever()
