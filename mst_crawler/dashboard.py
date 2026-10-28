"""Dashboard web theo dõi tiến độ crawl: python -m mst_crawler dashboard (mở http://localhost:8000).

Chỉ dùng thư viện chuẩn; đọc trực tiếp SQLite nên chạy song song được với lệnh crawl.
"""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROVINCE_SQL = """
SELECT province,
       COUNT(*)                                   AS total,
       SUM(status='done')                         AS done,
       SUM(pages>=10)                             AS capped,
       COALESCE(SUM(rows), 0)                     AS rows
FROM locations GROUP BY province ORDER BY province
"""


def snapshot(db_path):
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    one = lambda q: db.execute(q).fetchone()[0]
    provinces = []
    uniq = dict(db.execute(
        "SELECT l.province, COUNT(*) FROM companies c JOIN locations l ON l.path=c.first_location GROUP BY l.province"))
    for prov, total, done, capped, rows in db.execute(PROVINCE_SQL):
        provinces.append({"province": prov.rsplit("/", 1)[-1], "total": total, "done": done or 0,
                          "capped": capped or 0, "rows": rows, "unique": uniq.get(prov, 0)})
    rows_total = one("SELECT COUNT(*) FROM hits")
    unique = one("SELECT COUNT(*) FROM companies")
    recent = db.execute("SELECT mst, name FROM companies ORDER BY first_seen DESC, rowid DESC LIMIT 15").fetchall()
    db.close()
    return {
        "locations_total": sum(p["total"] for p in provinces),
        "locations_done": sum(p["done"] for p in provinces),
        "locations_capped": sum(p["capped"] for p in provinces),
        "rows_total": rows_total,
        "unique": unique,
        "dup_rate": round(100 * (rows_total - unique) / rows_total, 2) if rows_total else 0,
        "provinces": provinces,
        "recent": [{"mst": m, "name": n} for m, n in recent],
    }


PAGE = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MST Crawler</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1d2330;--mut:#6b7280;--line:#e5e7eb;--acc:#2563eb;--ok:#16a34a;--warn:#d97706}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b22;--fg:#e6e8ec;--mut:#9aa1ad;--line:#2a2f3a;--acc:#60a5fa;--ok:#4ade80;--warn:#fbbf24}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:20px 16px}h1{font-size:20px;margin:0 0 4px}.mut{color:var(--mut)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi b{display:block;font-size:24px;font-variant-numeric:tabular-nums}.kpi span{color:var(--mut);font-size:12px}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:var(--acc)}
.done .bar i{background:var(--ok)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}th{color:var(--mut);font-weight:500;font-size:12px;cursor:pointer;user-select:none}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:12px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
.wrap{overflow-x:auto}.recent div{padding:5px 0;border-bottom:1px solid var(--line);font-size:13px}.recent code{color:var(--mut)}
</style></head><body><main>
<h1>MST Crawler</h1><div class="mut" id="upd">Đang tải…</div>
<div class="kpis" id="kpis"></div>
<div class="grid">
 <div class="card wrap"><table><thead><tr>
  <th data-k="province">Tỉnh</th><th data-k="pct">Tiến độ</th><th data-k="done">Xã đã quét</th>
  <th data-k="capped">Chạm 250</th><th data-k="rows">Dòng</th><th data-k="unique">MST duy nhất</th></tr></thead>
  <tbody id="rows"></tbody></table></div>
 <div class="card recent"><b>Mới thu thập</b><div id="recent"></div></div>
</div></main>
<script>
const fmt=n=>n.toLocaleString('vi-VN');const esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');let sortK='province',asc=true,last=null;
document.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;asc=sortK===k?!asc:k==='province';sortK=k;render()});
function kpi(label,val,sub){return `<div class="card kpi"><span>${label}</span><b>${val}</b><span>${sub||''}</span></div>`}
function render(){const d=last;if(!d)return;
 const pct=d.locations_total?100*d.locations_done/d.locations_total:0;
 document.getElementById('kpis').innerHTML=
  kpi('Tiến độ xã/phường',pct.toFixed(1)+'%',fmt(d.locations_done)+' / '+fmt(d.locations_total))+
  kpi('MST duy nhất',fmt(d.unique))+kpi('Tổng dòng thu',fmt(d.rows_total))+
  kpi('Tỷ lệ trùng',d.dup_rate+'%',fmt(d.rows_total-d.unique)+' dòng trùng')+
  kpi('Xã chạm trần 250',fmt(d.locations_capped),'có thể còn sót công ty');
 const ps=d.provinces.map(p=>({...p,pct:p.total?p.done/p.total:0}));
 ps.sort((a,b)=>{const x=a[sortK],y=b[sortK];return (x>y?1:x<y?-1:0)*(asc?1:-1)});
 document.getElementById('rows').innerHTML=ps.map(p=>`<tr class="${p.done===p.total?'done':''}"><td>${p.province}</td>
  <td style="min-width:110px"><div class="bar"><i style="width:${(100*p.pct).toFixed(1)}%"></i></div></td>
  <td>${fmt(p.done)}/${fmt(p.total)}</td><td>${fmt(p.capped)}</td><td>${fmt(p.rows)}</td><td>${fmt(p.unique)}</td></tr>`).join('');
 document.getElementById('recent').innerHTML=d.recent.map(r=>`<div><code>${esc(r.mst)}</code> ${esc(r.name)}</div>`).join('')||'<div class="mut">Chưa có</div>';
}
async function load(){try{last=await (await fetch('api/stats')).json();render();
 document.getElementById('upd').textContent='Cập nhật '+new Date().toLocaleTimeString('vi-VN')+' · tự làm mới mỗi 10 giây'}
 catch(e){document.getElementById('upd').textContent='Lỗi tải dữ liệu: '+e}}
load();setInterval(load,10000);
</script></body></html>"""


def serve(db_path, port=8000):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/stats"):
                body = json.dumps(snapshot(db_path), ensure_ascii=False).encode()
                ctype = "application/json; charset=utf-8"
            else:
                body, ctype = PAGE.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    print(f"Dashboard: http://localhost:{port}  (Ctrl+C để dừng)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
