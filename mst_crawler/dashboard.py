"""Dashboard web: theo dõi tiến độ và chọn tỉnh để chạy crawl.

python -m mst_crawler dashboard  ->  http://localhost:8000
Chỉ dùng thư viện chuẩn; đọc SQLite ở chế độ chỉ đọc, crawl chạy trong tiến trình con riêng.
"""
import collections
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .provinces import display_name

PREFIX = "/tra-cuu-ma-so-thue-theo-tinh/"
SLUG = re.compile(r"^[a-z0-9-]+-\d+$")

PROVINCE_SQL = """
SELECT province,
       COUNT(*)                                   AS total,
       SUM(status='done')                         AS done,
       SUM(pages>=10)                             AS capped,
       COALESCE(SUM(rows), 0)                     AS rows
FROM locations GROUP BY province
"""


def snapshot(db_path, province=None):
    """province: slug tỉnh (vd an-giang-93) để lọc danh sách 'Mới thu thập'; None = tất cả."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    one = lambda q: db.execute(q).fetchone()[0]
    provinces = []
    uniq = dict(db.execute(
        "SELECT l.province, COUNT(*) FROM companies c JOIN locations l ON l.path=c.first_location GROUP BY l.province"))
    for prov, total, done, capped, rows in db.execute(PROVINCE_SQL):
        provinces.append({"slug": prov.rsplit("/", 1)[-1], "name": display_name(prov), "total": total,
                          "done": done or 0, "capped": capped or 0, "rows": rows, "unique": uniq.get(prov, 0)})
    provinces.sort(key=lambda p: p["name"])
    rows_total = one("SELECT COUNT(*) FROM hits")
    unique = one("SELECT COUNT(*) FROM companies")
    if province:
        recent = db.execute(
            "SELECT c.mst, c.name FROM companies c JOIN locations l ON l.path=c.first_location "
            "WHERE l.province=? ORDER BY c.first_seen DESC, c.rowid DESC LIMIT 15", (PREFIX + province,)).fetchall()
    else:
        recent = db.execute("SELECT mst, name FROM companies ORDER BY first_seen DESC, rowid DESC LIMIT 15").fetchall()
    db.close()
    return {
        "locations_total": sum(p["total"] for p in provinces),
        "locations_done": sum(p["done"] for p in provinces),
        "locations_capped": sum(p["capped"] for p in provinces),
        "rows_total": rows_total,
        "unique": unique,
        "provinces": provinces,
        "recent": [{"mst": m, "name": n} for m, n in recent],
    }


class Runner:
    """Chạy `mst_crawler crawl` trong tiến trình con và giữ 200 dòng log cuối."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.proc = None
        self.log = collections.deque(maxlen=200)
        self.provinces = []
        self.lock = threading.Lock()

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, provinces, workers, delay):
        with self.lock:
            if self.running():
                return False, "Đang chạy, hãy dừng trước."
            provinces = [p for p in provinces if SLUG.match(p)]
            if not provinces:
                return False, "Chưa chọn tỉnh nào."
            cmd = [sys.executable, "-m", "mst_crawler", "--db", self.db_path, "crawl",
                   "--workers", str(max(1, min(int(workers), 8))), "--delay", str(max(0.5, float(delay))),
                   "--provinces", ",".join(provinces)]
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
            self.log.clear()
            self.provinces = provinces
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()
            return True, "Đã bắt đầu."

    def _pump(self, proc):
        for raw in proc.stdout:
            self.log.append(raw.decode("utf-8", "replace").rstrip())
        code = proc.wait()
        self.log.append({0: "== Hoàn tất ==", 2: "== Dừng vì bị chặn. Đợi một lúc rồi bấm Bắt đầu lại =="}
                        .get(code, f"== Đã dừng (mã {code}) =="))

    def stop(self):
        with self.lock:
            if self.running():
                self.proc.terminate()
                return True, "Đã gửi lệnh dừng."
            return False, "Không có tiến trình đang chạy."

    def status(self):
        names = [display_name(p) for p in self.provinces]
        # log dùng đường dẫn tỉnh -> đổi sang tên cho dễ đọc
        lines = [re.sub(r"/tra-cuu-ma-so-thue-theo-tinh/([a-z0-9-]+-\d+)", lambda m: display_name(m.group(1)), l)
                 for l in self.log]
        return {"running": self.running(), "provinces": names, "log": lines[-60:]}


PAGE = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MST Crawler</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--fg:#1d2330;--mut:#6b7280;--line:#e5e7eb;--acc:#2563eb;--ok:#16a34a;--bad:#dc2626}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b22;--fg:#e6e8ec;--mut:#9aa1ad;--line:#2a2f3a;--acc:#60a5fa;--ok:#4ade80;--bad:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:20px 16px}h1{font-size:20px;margin:0 0 4px}.mut{color:var(--mut)}
.head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:16px 0}
.tabs button{background:none;border:0;border-bottom:2px solid transparent;color:var(--mut);padding:8px 14px;font:inherit;cursor:pointer}
.tabs button.on{color:var(--fg);border-color:var(--acc);font-weight:600}
.pane{display:none}.pane.on{display:block}
select,input{padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);font:inherit}
select{margin-left:6px;min-width:200px}input[type=number]{width:80px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi b{display:block;font-size:24px;font-variant-numeric:tabular-nums}.kpi span{color:var(--mut);font-size:12px}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:var(--acc)}
.done .bar i{background:var(--ok)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}th{color:var(--mut);font-weight:500;font-size:12px;cursor:pointer;user-select:none}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:12px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
.wrap{overflow-x:auto}.recent div{padding:5px 0;border-bottom:1px solid var(--line);font-size:13px}.recent code{color:var(--mut)}
.btn{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:7px 14px;border-radius:8px;font:inherit;cursor:pointer}
.btn.pri{background:var(--acc);border-color:var(--acc);color:#fff}.btn.stop{color:var(--bad);border-color:var(--bad)}
.btn:disabled{opacity:.45;cursor:default}
.ctrl{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
.plist{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px;max-height:430px;overflow:auto}
.plist label{display:flex;gap:8px;align-items:center;padding:6px 8px;border:1px solid var(--line);border-radius:8px;cursor:pointer}
.plist label.full{opacity:.55}.plist small{margin-left:auto;color:var(--mut);font-variant-numeric:tabular-nums}
.status{font-weight:600}.status.run{color:var(--ok)}
pre{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;height:300px;overflow:auto;font-size:12px;margin:8px 0 0;white-space:pre-wrap}
</style></head><body><main>
<div class="head"><div><h1>MST Crawler</h1><div class="mut" id="upd">Đang tải…</div></div></div>
<div class="tabs"><button data-t="ov" class="on">Tổng quan</button><button data-t="run">Chạy crawl</button></div>

<section class="pane on" id="ov">
 <div class="ctrl"><label class="mut">Tỉnh/thành <select id="prov"><option value="">Tất cả</option></select></label></div>
 <div class="kpis" id="kpis"></div>
 <div class="grid">
  <div class="card wrap"><table><thead><tr>
   <th data-k="name">Tỉnh</th><th data-k="pct">Tiến độ</th><th data-k="done">Xã đã quét</th>
   <th data-k="capped">Chạm 250</th><th data-k="rows">Dòng</th><th data-k="unique">MST duy nhất</th></tr></thead>
   <tbody id="rows"></tbody></table></div>
  <div class="card recent"><b>Mới thu thập</b><div id="recent"></div></div>
 </div>
</section>

<section class="pane" id="run">
 <div class="card">
  <div class="ctrl">
   <button class="btn" id="all">Chọn tất cả</button><button class="btn" id="none">Bỏ chọn</button>
   <button class="btn" id="todo">Chọn tỉnh chưa xong</button>
   <span class="mut" id="cnt"></span>
  </div>
  <div class="plist" id="plist"></div>
 </div>
 <div class="card" style="margin-top:12px">
  <div class="ctrl">
   <label class="mut">Số luồng <input type="number" id="workers" min="1" max="8" value="1"></label>
   <label class="mut">Nghỉ (giây) <input type="number" id="delay" min="0.5" step="0.5" value="2"></label>
   <button class="btn pri" id="start">Bắt đầu</button><button class="btn stop" id="stop">Dừng</button>
   <span class="status" id="st">—</span>
  </div>
  <div class="mut" id="runprov"></div>
  <pre id="log"></pre>
 </div>
</section>
</main>
<script>
const $=id=>document.getElementById(id);
const fmt=n=>n.toLocaleString('vi-VN');const esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
let sortK='name',asc=true,last=null,checked=new Set(JSON.parse(store.get('checked')||'[]'));

document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('on',x===b));
 document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('on',p.id===b.dataset.t));store.set('tab',b.dataset.t)});
if(store.get('tab')==='run')document.querySelector('[data-t=run]').click();

document.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;asc=sortK===k?!asc:k==='name';sortK=k;render()});
const sel=$('prov');sel.onchange=()=>{store.set('prov',sel.value);load()};
function kpi(label,val,sub){return `<div class="card kpi"><span>${label}</span><b>${val}</b><span>${sub||''}</span></div>`}
function fillSelect(ps){if(sel.options.length>1)return;const saved=store.get('prov')||'';
 ps.forEach(p=>sel.add(new Option(p.name,p.slug)));
 if(saved&&ps.some(p=>p.slug===saved)){sel.value=saved;setTimeout(load)}}

function render(){const d=last;if(!d)return;fillSelect(d.provinces);
 const cur=sel.value,one=d.provinces.find(p=>p.slug===cur);
 const t=one||{total:d.locations_total,done:d.locations_done,capped:d.locations_capped,rows:d.rows_total,unique:d.unique};
 const pct=t.total?100*t.done/t.total:0,dup=Math.max(0,t.rows-t.unique);
 $('kpis').innerHTML=
  kpi('Tiến độ xã/phường',pct.toFixed(1)+'%',fmt(t.done)+' / '+fmt(t.total))+
  kpi('MST duy nhất',fmt(t.unique))+kpi('Tổng dòng thu',fmt(t.rows))+
  kpi('Tỷ lệ trùng',(t.rows?(100*dup/t.rows).toFixed(2):0)+'%',fmt(dup)+' dòng trùng')+
  kpi('Xã chạm trần 250',fmt(t.capped),'có thể còn sót công ty');
 const ps=d.provinces.filter(p=>!cur||p.slug===cur).map(p=>({...p,pct:p.total?p.done/p.total:0}));
 ps.sort((a,b)=>{const x=a[sortK],y=b[sortK];return (sortK==='name'?x.localeCompare(y,'vi'):(x>y?1:x<y?-1:0))*(asc?1:-1)});
 $('rows').innerHTML=ps.map(p=>`<tr class="${p.done===p.total?'done':''}"><td>${esc(p.name)}</td>
  <td style="min-width:110px"><div class="bar"><i style="width:${(100*p.pct).toFixed(1)}%"></i></div></td>
  <td>${fmt(p.done)}/${fmt(p.total)}</td><td>${fmt(p.capped)}</td><td>${fmt(p.rows)}</td><td>${fmt(p.unique)}</td></tr>`).join('');
 $('recent').innerHTML=d.recent.map(r=>`<div><code>${esc(r.mst)}</code> ${esc(r.name)}</div>`).join('')||'<div class="mut">Chưa có</div>';
 renderList();
}

function renderList(){const d=last;if(!d)return;
 $('plist').innerHTML=d.provinces.map(p=>`<label class="${p.done===p.total?'full':''}">
  <input type="checkbox" value="${esc(p.slug)}" ${checked.has(p.slug)?'checked':''}> ${esc(p.name)}
  <small>${fmt(p.done)}/${fmt(p.total)}</small></label>`).join('');
 $('plist').querySelectorAll('input').forEach(i=>i.onchange=()=>{i.checked?checked.add(i.value):checked.delete(i.value);saveChecked()});
 updCount()}
function saveChecked(){store.set('checked',JSON.stringify([...checked]));updCount()}
function updCount(){$('cnt').textContent='Đã chọn '+checked.size+' tỉnh'}
function setAll(fn){if(!last)return;checked=new Set(last.provinces.filter(fn).map(p=>p.slug));saveChecked();renderList()}
$('all').onclick=()=>setAll(()=>true);$('none').onclick=()=>setAll(()=>false);$('todo').onclick=()=>setAll(p=>p.done<p.total);

async function post(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});return r.json()}
$('start').onclick=async()=>{
 const order=last?last.provinces.map(p=>p.slug).filter(s=>checked.has(s)):[...checked];
 const r=await post('api/crawl/start',{provinces:order,workers:+$('workers').value,delay:+$('delay').value});
 if(!r.ok)alert(r.msg);status()};
$('stop').onclick=async()=>{await post('api/crawl/stop');status()};

async function status(){try{const s=await (await fetch('api/crawl/status')).json();
 $('st').textContent=s.running?'● Đang chạy':'Đang dừng';$('st').className='status'+(s.running?' run':'');
 $('start').disabled=s.running;$('stop').disabled=!s.running;
 $('runprov').textContent=s.provinces.length?'Lần chạy này: '+s.provinces.join(', '):'';
 const pre=$('log'),atEnd=pre.scrollTop+pre.clientHeight>=pre.scrollHeight-5;
 pre.textContent=s.log.join('\\n')||'Chưa có log.';if(atEnd)pre.scrollTop=pre.scrollHeight}catch(e){}}

async function load(){try{last=await (await fetch('api/stats?province='+encodeURIComponent(sel.value))).json();render();
 $('upd').textContent='Cập nhật '+new Date().toLocaleTimeString('vi-VN')+' · tự làm mới mỗi 10 giây'}
 catch(e){$('upd').textContent='Lỗi tải dữ liệu: '+e}}
load();status();setInterval(load,10000);setInterval(status,3000);
</script></body></html>"""


def serve(db_path, port=8000):
    runner = Runner(os.path.abspath(db_path))

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, ctype="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/api/stats":
                prov = parse_qs(url.query).get("province", [""])[0]
                self._send(snapshot(db_path, prov or None))
            elif url.path == "/api/crawl/status":
                self._send(runner.status())
            else:
                self._send(PAGE.encode(), "text/html; charset=utf-8")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/crawl/start":
                ok, msg = runner.start(data.get("provinces", []), data.get("workers", 1), data.get("delay", 2))
            elif self.path == "/api/crawl/stop":
                ok, msg = runner.stop()
            else:
                ok, msg = False, "Không hỗ trợ"
            self._send({"ok": ok, "msg": msg})

        def log_message(self, *args):
            pass

    print(f"Dashboard: http://localhost:{port}  (Ctrl+C để dừng)")
    try:
        ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
    finally:
        runner.stop()
