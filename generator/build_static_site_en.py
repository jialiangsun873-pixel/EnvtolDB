#!/usr/bin/env python3
"""EnvTolDB static site generator v2 — English-first, bilingual (EN/中文) toggle.

Design language follows leading bio-DB sites (UniProt search-first landing,
GTDB taxonomy browser, MGnify card layout):
  * sticky header w/ logo + nav + language toggle + GitHub link
  * hero with big search + release badge + stat chips
  * browse cards per environmental group
  * sortable / filterable tables (vanilla JS, zero dependencies)
  * breadcrumb + provenance links on every record page
  * footer with citation, sources, license

Output: repo root (GitHub Pages serves from root of main branch).
"""
import csv, glob, gzip, html, json, os, sqlite3, datetime
from collections import defaultdict
from statistics import median

from build_afp_site import build_site as build_afp_site

# ENVTOLDB_DB / ENVTOLDB_OUT let a build be rehearsed against a staged copy without touching the repo.
DB = os.environ.get("ENVTOLDB_DB", "/public/home/sjl2/datasetdb/dataset.db")
CFG = "/public/home/sjl2/datasetdb/config.json"
OUT = os.environ.get("ENVTOLDB_OUT", "/public/home/sjl2/envtoldb_site")   # repo root = site root
NOW = datetime.datetime.now().strftime("%Y-%m-%d")
RELEASE = "v3.8.0"
UNIPROT_RELEASE = "2026_01"

cfg = json.load(open(CFG, encoding="utf-8"))
db = sqlite3.connect(DB, timeout=60)
db.row_factory = sqlite3.Row
db.execute("PRAGMA busy_timeout=60000")
DATA_AS_OF = db.execute("SELECT MAX(substr(ts, 1, 10)) FROM import_batches WHERE kind IS NULL OR kind != 'afp_ibp'").fetchone()[0] or NOW

POOLS = {p["key"]: p for p in cfg["pools"]}
POOL_EN = {"thermo": "Thermophilic", "salt": "Halophilic", "ph": "Acid/Alkaliphilic", "metal": "Metal-resistant", "endolithic": "Endolithic", "xerophilic": "Xerophilic", "cold": "Cold-adapted", "piezo": "Piezophilic", "rad": "Radiation-resistant",
           "solvent": "Solvent-tolerant", "meso": "Mesophilic controls", "cold": "Cold-adapted",
           "arsenic": "Arsenic-resistant", "magnetotactic": "Magnetotactic", "oligotrophic": "Oligotrophic"}
POOL_ZH = {"thermo": "嗜热", "salt": "耐盐", "ph": "耐酸碱", "solvent": "耐溶剂", "meso": "中温对照", "cold": "嗜冷", "piezo": "嗜压", "rad": "耐辐射", "metal": "耐重金属", "endolithic": "石内内生", "xerophilic": "耐干燥",
           "arsenic": "耐砷", "magnetotactic": "趋磁", "oligotrophic": "耐贫营养"}

for sub in ("species", "species/data", "protein", "downloads/fasta", "downloads/tsv", ".github/workflows"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
open(f"{OUT}/.nojekyll", "w").close()

ANCH_OK = '<span class="badge b-ok">yes</span>'
ANCH_NO = '<span class="badge b-no">no</span>'
V_OK = '<span class="badge b-ok">✓</span>'

def esc(s): return html.escape(str(s if s is not None else ""))
def slugify(name): return name.replace(" ", "_").replace("/", "_")

# ---------------- shared chrome ----------------
CSS = """
:root{color-scheme:light dark;--ink:#1d1d1f;--soft:#48484a;--faint:#6e6e73;--line:rgba(60,60,67,.13);--bg:#f5f5f7;--card:rgba(255,255,255,.74);--header:rgba(249,249,251,.76);--accent:#007aff;--accent-ink:#0066cc;--ok:#248a3d;--ok-bg:rgba(52,199,89,.14);--no:#ff3b30;--no-bg:rgba(255,59,48,.12);--warn:#9a6200;--warn-bg:rgba(255,159,10,.15);--radius:24px;--shadow:0 18px 50px rgba(28,38,60,.10),0 2px 8px rgba(28,38,60,.05);--shadow-soft:0 8px 24px rgba(28,38,60,.08);--glass:blur(24px) saturate(180%)}
@media(prefers-color-scheme:dark){:root{--ink:#f5f5f7;--soft:#d1d1d6;--faint:#98989d;--line:rgba(255,255,255,.11);--bg:#111114;--card:rgba(44,44,46,.74);--header:rgba(28,28,30,.78);--accent:#0a84ff;--accent-ink:#409cff;--ok:#30d158;--ok-bg:rgba(48,209,88,.15);--no:#ff453a;--no-bg:rgba(255,69,58,.14);--warn:#ffd60a;--warn-bg:rgba(255,214,10,.13);--shadow:0 22px 60px rgba(0,0,0,.34),0 2px 10px rgba(0,0,0,.22);--shadow-soft:0 10px 30px rgba(0,0,0,.26)}}
*{box-sizing:border-box}html{scroll-behavior:smooth}html{background:var(--bg)}body{position:relative;isolation:isolate;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","SF Pro Display","Helvetica Neue","PingFang SC","Microsoft YaHei",sans-serif;margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.55;overflow-wrap:anywhere;-webkit-font-smoothing:antialiased}body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(circle at 8% 2%,rgba(0,122,255,.13),transparent 30%),radial-gradient(circle at 94% 12%,rgba(52,199,89,.09),transparent 28%),radial-gradient(circle at 50% 100%,rgba(255,159,10,.06),transparent 34%)}::selection{background:rgba(0,122,255,.24)}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}button,input{font:inherit}button{touch-action:manipulation}a,button,input,summary{-webkit-tap-highlight-color:transparent}:focus-visible{outline:3px solid rgba(0,122,255,.34);outline-offset:3px}
header{position:sticky;top:0;z-index:50;background:var(--header);border-bottom:1px solid var(--line);padding:12px 28px;display:flex;align-items:center;gap:18px;flex-wrap:wrap;backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}
.brand{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:700;letter-spacing:-.02em;color:var(--ink)}.brand svg{width:27px;height:27px;color:var(--accent)}.brand small{display:block;font-weight:500;font-size:10.5px;color:var(--faint);margin-top:-2px;letter-spacing:.01em}
nav{display:flex;gap:3px;flex-wrap:wrap;padding:4px;border:1px solid var(--line);border-radius:18px;background:var(--card);box-shadow:0 6px 20px rgba(28,38,60,.06);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}nav a{padding:7px 12px;border-radius:13px;color:var(--soft);font-size:13px;font-weight:550;line-height:1.2;min-height:34px;display:inline-flex;align-items:center}nav a:hover{background:rgba(120,120,128,.10);color:var(--ink);text-decoration:none}nav a.on{background:rgba(0,122,255,.13);color:var(--accent);font-weight:650}
.hdr-right{margin-left:auto;display:flex;align-items:center;gap:9px}.langbtn{border:1px solid var(--line);background:var(--card);border-radius:13px;padding:7px 11px;font-size:12.5px;cursor:pointer;color:var(--soft);min-height:36px;backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}.langbtn:hover{color:var(--ink);background:rgba(120,120,128,.12)}.gh{font-size:12.5px;color:var(--soft);border:1px solid var(--line);background:var(--card);border-radius:13px;padding:7px 11px;min-height:36px;display:inline-flex;align-items:center}.gh:hover{color:var(--ink);text-decoration:none;background:rgba(120,120,128,.12)}
main{max-width:1180px;margin:0 auto;padding:30px 20px 76px}main>*{animation:iosReveal .58s cubic-bezier(.2,.75,.25,1) both}main>*:nth-child(2){animation-delay:.05s}main>*:nth-child(3){animation-delay:.1s}main>*:nth-child(4){animation-delay:.15s}main>*:nth-child(5){animation-delay:.2s}main>*:nth-child(n+6){animation-delay:.24s}@keyframes iosReveal{from{opacity:0;transform:translateY(12px) scale(.992)}to{opacity:1;transform:none}}
.hero{position:relative;isolation:isolate;overflow:hidden;background:linear-gradient(145deg,rgba(255,255,255,.90),rgba(238,244,255,.76));border:1px solid rgba(255,255,255,.82);border-radius:32px;padding:38px 38px 30px;margin-bottom:24px;box-shadow:var(--shadow)}@media(prefers-color-scheme:dark){.hero{background:linear-gradient(145deg,rgba(44,44,46,.92),rgba(22,36,55,.82));border-color:var(--line)}}.hero::before,.hero::after{content:"";position:absolute;z-index:-1;border-radius:999px;filter:blur(8px);opacity:.72}.hero::before{width:260px;height:260px;right:-70px;top:-110px;background:radial-gradient(circle,rgba(0,122,255,.24),transparent 68%)}.hero::after{width:220px;height:220px;left:36%;bottom:-160px;background:radial-gradient(circle,rgba(52,199,89,.17),transparent 68%)}.hero>*{position:relative;z-index:1}.hero h1{font-size:34px;line-height:1.12;margin:0 0 7px;letter-spacing:-.045em;font-weight:720}.hero .tag{font-size:15.5px;color:var(--soft);margin-bottom:18px;max-width:850px}.badge-line{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}.rel{background:var(--accent);color:#fff;font-size:12px;padding:5px 12px;border-radius:999px;font-weight:650;box-shadow:0 6px 16px rgba(0,122,255,.22)}.rel2{background:var(--card);border:1px solid var(--line);color:var(--soft);font-size:12px;padding:5px 12px;border-radius:999px;backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}
.srch{display:flex;gap:9px;max-width:590px}.srch input{flex:1;padding:12px 16px;font-size:14px;border:1px solid var(--line);border-radius:15px;background:var(--card);color:var(--ink);box-shadow:inset 0 1px 0 rgba(255,255,255,.28);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}.srch input:focus{outline:none;border-color:rgba(0,122,255,.55);box-shadow:0 0 0 4px rgba(0,122,255,.12)}.srch button{padding:11px 20px;font-size:14px;border-radius:15px;background:var(--accent);color:#fff;border:none;cursor:pointer;font-weight:650;box-shadow:0 8px 20px rgba(0,122,255,.20)}.srch button:hover{background:var(--accent-ink)}.srch button:active{transform:scale(.97)}.hint{font-size:12px;color:var(--faint);margin-top:8px}
.chips{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}.chip{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:13px 17px;min-width:154px;box-shadow:var(--shadow-soft);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}.chip b{font-size:23px;line-height:1.15;display:block;letter-spacing:-.035em}.chip span{font-size:11.5px;color:var(--faint)}
h2.sec{font-size:20px;letter-spacing:-.025em;margin:30px 0 14px}h2{font-size:19px;margin:0 0 13px;letter-spacing:-.02em}h3{font-size:15px;margin:20px 0 7px;letter-spacing:-.01em}.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:21px 22px;margin-bottom:18px;box-shadow:var(--shadow-soft);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}.pcard{display:block;background:var(--card);border:1px solid var(--line);border-radius:22px;padding:18px 19px;box-shadow:var(--shadow-soft);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass);transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease}.pcard b{font-size:15px;letter-spacing:-.01em}.pcard .n{font-size:26px;font-weight:720;letter-spacing:-.04em;display:block;margin:3px 0}.pcard .m{font-size:12px;color:var(--faint);display:block;margin-bottom:9px}
table{border-collapse:separate;border-spacing:0;width:100%;background:var(--card);border:1px solid var(--line);border-radius:20px;overflow:hidden;font-size:13px;box-shadow:0 8px 26px rgba(28,38,60,.05);backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}th{background:rgba(120,120,128,.08);text-align:left;padding:11px 13px;font-weight:650;white-space:nowrap;cursor:pointer;user-select:none;border-bottom:1px solid var(--line)}th:hover{background:rgba(120,120,128,.13)}td{padding:9px 13px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}tbody tr:hover td,tr:hover td{background:rgba(0,122,255,.045)}
.badge{display:inline-flex;align-items:center;padding:3px 10px;border-radius:999px;font-size:11.5px;font-weight:600;line-height:1.35;white-space:nowrap;background:rgba(0,122,255,.11);color:var(--accent)}.b-ok,.badge.ok{background:var(--ok-bg);color:var(--ok)}.b-no,.badge.bad{background:var(--no-bg);color:var(--no)}.badge.warn,.b-grade{background:var(--warn-bg);color:var(--warn)}.bar{height:10px;border-radius:999px;display:inline-block;vertical-align:middle}.bar-neg{background:var(--no)}.bar-pos{background:var(--ok)}.muted{color:var(--faint);font-size:12.5px}.note{background:rgba(0,122,255,.085);border:1px solid rgba(0,122,255,.16);color:var(--accent-ink);padding:12px 16px;border-radius:18px;margin-bottom:18px;font-size:13.5px;backdrop-filter:var(--glass);-webkit-backdrop-filter:var(--glass)}.warnbox{background:var(--warn-bg);border:1px solid rgba(255,159,10,.20);border-radius:18px;padding:12px 15px;margin:14px 0;color:var(--warn)}.err{background:var(--no-bg);border:1px solid rgba(255,59,48,.18);color:var(--no);padding:10px 15px;border-radius:16px;margin-bottom:14px;font-size:13px}
code{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12px;background:rgba(120,120,128,.11);padding:2px 6px;border-radius:6px}pre,.seq{font:12px/1.7 ui-monospace,"SF Mono",Menlo,Consolas,monospace;background:rgba(120,120,128,.09);border:1px solid var(--line);padding:14px;border-radius:18px;overflow:auto;max-height:380px}.seq{word-break:break-all}input,button{font-size:13.5px;padding:9px 12px;border:1px solid var(--line);border-radius:14px;background:var(--card);color:var(--ink);font-family:inherit}input{width:340px;max-width:100%}input:focus{outline:none;border-color:rgba(0,122,255,.5);box-shadow:0 0 0 4px rgba(0,122,255,.10)}button{background:var(--accent);color:#fff;border-color:transparent;cursor:pointer;font-weight:650}button:hover{background:var(--accent-ink)}button:active{transform:scale(.98)}.btn{display:inline-flex;align-items:center;padding:10px 16px;border-radius:14px;background:var(--accent);color:#fff;font-weight:650}.btn:hover{background:var(--accent-ink);text-decoration:none}
details{border:1px solid var(--line);border-radius:18px;padding:12px 16px;margin:10px 0;background:var(--card)}summary{cursor:pointer;font-weight:650;font-size:13.5px}.kv{display:grid;grid-template-columns:150px 1fr;gap:8px 16px}.kv dt{color:var(--faint)}.kv dd{margin:0}.crumb{font-size:12.5px;color:var(--faint);margin-bottom:16px}.crumb a{color:var(--faint)}footer{max-width:1180px;margin:28px auto 52px;padding:18px 20px;border-top:1px solid var(--line);color:var(--faint);font-size:12.5px}
@media(hover:hover) and (pointer:fine){.card:hover,.pcard:hover{transform:translateY(-3px);box-shadow:0 22px 54px rgba(28,38,60,.13);border-color:rgba(0,122,255,.18)}.chip:hover{transform:translateY(-2px)}}
@media(max-width:760px){header{padding:10px 14px;gap:10px}.brand{width:calc(100% - 120px)}nav{order:3;width:100%;flex-wrap:nowrap;overflow-x:auto;border-radius:16px;scrollbar-width:none}nav::-webkit-scrollbar{display:none}nav a{white-space:nowrap}.hdr-right{margin-left:auto}.gh{display:none}main{padding:22px 14px 60px}.hero{padding:26px 22px 22px;border-radius:26px}.hero h1{font-size:29px}.hero .tag{font-size:14.5px}.srch{flex-direction:column}.srch button{width:100%}.chips{gap:9px}.chip{min-width:calc(50% - 5px);padding:12px 14px}.card{padding:17px 16px;border-radius:21px}.grid{grid-template-columns:1fr}table{display:block;overflow-x:auto;border-radius:18px}.kv{grid-template-columns:1fr;gap:3px}.kv dd{margin-bottom:9px}footer{margin:20px 14px 40px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation:none!important;transition:none!important}}
"""

JS = """
// ---- language toggle (EN default; 中文 via data-zh) ----
function setLang(l){
  document.documentElement.lang = l==='zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-zh]').forEach(el=>{
    if(l==='zh'){ if(!el.dataset.en) el.dataset.en = el.textContent; el.textContent = el.dataset.zh; }
    else { if(el.dataset.en) el.textContent = el.dataset.en; }
  });
  document.querySelectorAll('.langbtn').forEach(b=>b.style.fontWeight = b.dataset.l===l ? '700':'400');
  try{ localStorage.setItem('envtoldb_lang', l); }catch(e){}
}
document.addEventListener('DOMContentLoaded', ()=>{
  let l='en'; try{ l = localStorage.getItem('envtoldb_lang')||'en'; }catch(e){}
  setLang(l);
});
// ---- sortable tables ----
function sortTable(th){
  const tb = th.closest('table').querySelector('tbody') || th.closest('table');
  const idx = Array.from(th.parentNode.children).indexOf(th);
  const dir = th.dataset.dir === 'asc' ? -1 : 1;
  th.dataset.dir = dir===1 ? 'asc' : 'desc';
  const rows = Array.from(tb.querySelectorAll('tr')).filter(r=>!r.querySelector('th'));
  rows.sort((a,b)=>{
    const A=a.children[idx], B=b.children[idx];
    if(!A||!B) return 0;
    const na=parseFloat(A.textContent.replace(/[,%]/g,'')), nb=parseFloat(B.textContent.replace(/[,%]/g,''));
    const numA=!isNaN(na)&&A.textContent.match(/[\\d.]/), numB=!isNaN(nb)&&B.textContent.match(/[\\d.]/);
    let c = (numA&&numB) ? na-nb : A.textContent.localeCompare(B.textContent);
    return c*dir;
  });
  rows.forEach(r=>tb.appendChild(r));
  const pg = th.closest('[data-pg-wrap]');
  if (pg) { pg.dataset.page='1'; pgProt(th,0); }
}
// ---- protein table pagination (50/page) ----
function pgProt(btn, dir){
  const wrap = btn.closest('[data-pg-wrap]');
  const tb = wrap.querySelector('tbody');
  const rows = Array.from(tb.querySelectorAll('tr'));
  if (!rows.length) return;
  let page = parseInt(wrap.dataset.page || '1');
  const size = 50;
  const maxp = Math.ceil(rows.length / size);
  page = Math.min(maxp, Math.max(1, page + dir));
  wrap.dataset.page = page;
  rows.forEach((tr, i) => tr.style.display = (i >= (page-1)*size && i < page*size) ? '' : 'none');
  wrap.querySelector('.pgstat').textContent = `page ${page} / ${maxp}  (${rows.length} proteins)`;
}
function pgInit(wrap){
  const tb = wrap.querySelector('tbody');
  const rows = Array.from(tb.querySelectorAll('tr'));
  rows.forEach((tr, i) => tr.style.display = i < 50 ? '' : 'none');
  const maxp = Math.max(1, Math.ceil(rows.length / 50));
  wrap.dataset.page = '1';
  const st = wrap.querySelector('.pgstat');
  if (st) st.textContent = `page 1 / ${maxp}  (${rows.length} proteins)`;
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-pg-wrap]').forEach(pgInit);
});
// ---- live species filter ----
function filterSpecies(input){
  const q = input.value.toLowerCase();
  document.querySelectorAll('[data-sp-row]').forEach(tr=>{
    tr.style.display = tr.textContent.toLowerCase().indexOf(q)>-1 ? '' : 'none';
  });
}
"""
def lang_btns():
    return ('<button class="langbtn" data-l="en" onclick="setLang(\'en\')">EN</button>'
            '<button class="langbtn" data-l="zh" onclick="setLang(\'zh\')">中文</button>')

LOGO = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><path d="M12 2.6 20.4 7.4v9.2L12 21.4 3.6 16.6V7.4Z"/><circle cx="12" cy="12" r="2" fill="currentColor" stroke="none"/><path d="M12 5v2.8M12 16.2V19M5.7 8.5l2.4 1.4M15.9 14.1l2.4 1.4M18.3 8.7l-2.4 1.3M8.1 14l-2.4 1.4" opacity=".5"/></svg>"""

def page(title, body, active="", crumb="", subdir=False):
    pre = "../" if subdir else ""
    items = [("index.html", "Overview", "总览"), ("species/index.html", "Species", "物种"),
             ("afp/index.html", "AFP/IBP", "抗冻/冰结合"), ("solvents.html", "Solvents", "溶剂统计"),
             ("experiments.html", "Experiments", "实验参数"), ("methods.html", "Methods", "采集方法"),
             ("downloads.html", "Downloads", "下载"), ("api.html", "API", "API")]
    nav = "".join(
        f'<a href="{pre}{h}" class="{"on" if k==active else ""}" data-zh="{zh}">{t}</a>'
        for h, t, k, zh in [(h, t, k, zh) for (h, t, k, zh) in
                            [(i[0], i[1], i[2], i[3]) for i in
                             [("index.html","Overview","","总览"),("species/index.html","Species","","物种"),
                              ("afp/index.html","AFP/IBP","","抗冻/冰结合"),("solvents.html","Solvents","","溶剂统计"),
                              ("experiments.html","Experiments","","实验参数"),("methods.html","Methods","","采集方法"),
                              ("downloads.html","Downloads","","下载"),("api.html","API","","API")]]])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f5f5f7">
<title>{esc(title)} · EnvTolDB</title>
<meta name="description" content="EnvTolDB — environment-tolerant proteome database: 301 organisms, 892,811 UniProt proteins, 973,185 experimental measurements, 2.44M EC annotations.">
<style>{CSS}</style></head><body>
<header>
  <a class="brand" href="{pre}index.html">{LOGO}<span>EnvTolDB<small>Environment-Tolerant Proteome Database</small></span></a>
  <nav>{nav}</nav>
  <div class="hdr-right">{lang_btns()}<a class="gh" href="https://github.com/jialiangsun873-pixel/EnvtolDB" target="_blank" rel="noopener">GitHub ↗</a></div>
</header>
<main>
{'<div class="crumb"><a href="'+pre+'index.html">Home</a> › '+ ('<a href="'+pre+'species/index.html">Species</a> › ' if active in ('species','species-detail') else '') + esc(title) + '</div>' if crumb else ''}
{body}
</main>
<footer>
  <b>EnvTolDB</b> {esc(RELEASE)} · built {esc(NOW)} · MIT (code) / CC-BY 4.0 (data) ·
  <a href="https://github.com/jialiangsun873-pixel/EnvtolDB" target="_blank" rel="noopener">GitHub</a> ·
  <span data-zh="引用：EnvProGen 论文（撰写中）；数据来源 UniProtKB · BacDive · OrganiZymeDB · FireProtDB · ProThermDB · Europe PMC。">Citation: EnvProGen manuscript (in preparation); sources UniProtKB · BacDive · OrganiZymeDB · FireProtDB · ProThermDB · Europe PMC.</span>
</footer>
<script>{JS}</script>
</body></html>"""

def rel_links(r):
    out = []
    if r["proteome_id"]: out.append(f'<a href="https://www.uniprot.org/proteomes/{esc(r["proteome_id"])}" target="_blank" rel="noopener">UniProt proteome</a>')
    if r["taxon_id"]: out.append(f'<a href="https://www.ncbi.nlm.nih.gov/taxonomy/{esc(r["taxon_id"])}" target="_blank" rel="noopener">NCBI txid{esc(r["taxon_id"])}</a>')
    out.append(f'<a href="https://europepmc.org/search?query=%22{slugify(r["name"]).replace("_","%20")}%22" target="_blank" rel="noopener">Europe PMC</a>')
    return " · ".join(out)

# ================= collect data =================
sp_by_pool = defaultdict(list)
all_species = []
for r in db.execute("SELECT * FROM species ORDER BY pool, name"):
    sp_by_pool[r["pool"]].append(dict(r))
    all_species.append(dict(r))

pool_counts = {}
for key in POOLS:
    pool_counts[key] = db.execute("""SELECT
        (SELECT COUNT(*) FROM species WHERE pool={k}),
        (SELECT COUNT(*) FROM proteins p JOIN species s ON s.id=p.species_id WHERE s.pool={k}),
        (SELECT COUNT(*) FROM structures st JOIN proteins p ON p.accession=st.accession
           JOIN species s ON s.id=p.species_id WHERE s.pool={k})""".format(k=repr(key))).fetchone()

totals = {
    "species": db.execute("SELECT COUNT(*) FROM species").fetchone()[0],
    "proteins": db.execute("SELECT COUNT(*) FROM proteins").fetchone()[0],
    "experiments": db.execute("SELECT COUNT(*) FROM experiments WHERE value IS NOT NULL").fetchone()[0],
    "structures": db.execute("SELECT COUNT(*) FROM structures").fetchone()[0],
}
afp_present = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='afp_ibp_proteins'").fetchone()[0]
afp_counts = None
if afp_present:
    afp_counts = {
        "taxa": db.execute("SELECT COUNT(*) FROM afp_ibp_species WHERE inclusion_status='included'").fetchone()[0],
        "species": db.execute("SELECT COUNT(*) FROM afp_ibp_species").fetchone()[0],
        "proteins": db.execute("SELECT COUNT(*) FROM afp_ibp_proteins").fetchone()[0],
        "evidence": db.execute("SELECT COUNT(*) FROM afp_ibp_evidence").fetchone()[0],
        "quarantine": db.execute("SELECT COUNT(*) FROM afp_ibp_quarantine").fetchone()[0],
    }

# ================= gene mapping (v3.7.0): NCBI IPG + EBI coordinates + verified CDS =================
ipg = {}
gene_status_count = defaultdict(int)
for r in db.execute("SELECT accession, mapping_status, nucleotide, start, stop, strand, gene_name, cds_validation_status FROM gene_mapping_status WHERE mapping_status IN ('CDS_VERIFIED','COORDINATES_ONLY','MAPPED_CDS_UNVERIFIED')"):
    gene_status_count[r["mapping_status"]] += 1
    ipg[r["accession"]] = [r["mapping_status"], r["nucleotide"], r["start"], r["stop"], r["strand"], r["gene_name"], r["cds_validation_status"], None]
for r in db.execute("SELECT accession, sequence_length FROM gene_sequences"):
    if r["accession"] in ipg:
        ipg[r["accession"]][7] = r["sequence_length"]
print(f"gene mapping loaded: {len(ipg):,} ({dict(gene_status_count)}), CDS lengths: {sum(1 for v in ipg.values() if v[7]):,}", flush=True)
sp_cds = defaultdict(int)
for r in db.execute("SELECT species_id, COUNT(*) c FROM gene_sequences GROUP BY species_id"):
    sp_cds[r["species_id"]] = r["c"]
print(f"per-species CDS coverage: {len(sp_cds)} species", flush=True)

# ================= index =================
notice_en = cfg["site"].get("notice_en", "").format(n_pools=len(POOLS), n_species=totals["species"], n_proteins=totals["proteins"])
notice_zh = cfg["site"].get("notice", "").format(n_pools=len(POOLS), n_species=totals["species"], n_proteins=totals["proteins"])
afp_entry = ""
afp_methods = ""
afp_downloads = ""
afp_schema = ""
if afp_counts:
    afp_schema = f"""<tr><td><code>afp_ibp_species</code> / <code>afp_ibp_proteins</code> / <code>afp_ibp_evidence</code> / <code>afp_ibp_quarantine</code></td>
<td>independent AFP/IBP identities, functions, evidence classes, limitations and review exclusions; no core-pool membership</td>
<td>{afp_counts['species']} / {afp_counts['proteins']} / {afp_counts['evidence']} / {afp_counts['quarantine']}</td></tr>"""
    afp_downloads = """<div class="card"><h2>Independent AFP / IBP subset</h2>
<p style="font-size:13.5px"><a href="afp/downloads/afp_ibp_proteins.fasta" download>Protein FASTA</a> ·
<a href="afp/downloads/afp_ibp_proteins.tsv" download>Protein TSV</a> ·
<a href="afp/downloads/afp_ibp.json" download>Complete subset JSON</a>. The JSON includes species decisions,
evidence rows and quarantined records; sequence SHA-256 values are included for integrity checks.</p></div>"""
    afp_methods = """<div class="card"><h2>Independent AFP / IBP subset</h2>
<p style="font-size:13.5px">AFP/IBP records are curated in separate tables and are not assigned to the 14 core pools.
Evidence classes distinguish native protein characterization, reviewed annotation, direct recombinant activity,
primary-literature function, transcript/homology prediction and database-only annotation. Quarantined identity
conflicts and keyword false positives are retained for audit but excluded from protein counts.</p>
<p><a href="afp/methods.html">AFP/IBP evidence guide →</a></p></div>"""
    afp_entry = f"""<div class="card"><h2 data-zh="独立抗冻/冰结合蛋白子集">Independent AFP / IBP subset</h2>
<p style="font-size:13.5px">{afp_counts['taxa']} included taxa · {afp_counts['proteins']} accession-level proteins · {afp_counts['evidence']} evidence rows.
Functions, activity types, limitations, sequences and primary-literature links are curated separately; these records do not alter the 14 core environmental pools.</p>
<p><a href="afp/index.html">Browse AFP/IBP functions &amp; evidence →</a></p></div>"""

sp_rows = "".join(
    f'<tr data-sp-row><td><a href="species/{slugify(r["name"])}.html">{esc(r["name"])}</a></td>'
    f'<td><span class="badge">{POOL_EN.get(r["pool"], esc(r["pool"]))}</span></td>'
    f'<td>{esc(r["grade"] or "—")}</td><td>{(r["n_seqs"] or 0):,}</td>'
    f'<td>{ANCH_OK if r["lit_anchored"] else ANCH_NO}</td></tr>'
    for r in all_species)

pool_cards = "".join(f"""<a class="pcard" href="species/{k}.html" style="text-decoration:none">
<b>{esc(POOL_EN[k])} <span data-zh="{POOL_ZH[k]}">{POOL_ZH[k]}</span></b>
<span class="n">{pool_counts[k][0]}</span>
<span class="m">{pool_counts[k][1]:,} proteins · {pool_counts[k][2]:,} structures</span>
Browse →</a>""" for k in POOLS)

body = f"""<div class="hero">
  <h1>EnvTolDB</h1>
  <div class="tag">A curated, provenance-tracked database of proteins from environment-tolerant organisms — thermophilic, halophilic, acid/alkaliphilic, solvent-tolerant — with mesophilic controls.</div>
  <div class="badge-line"><span class="rel">Release {esc(RELEASE)}</span><span class="rel2">Data as of {esc(DATA_AS_OF)}</span><span class="rel2">Source: UniProtKB {esc(UNIPROT_RELEASE)}</span></div>
  <div class="srch"><input id="spq" placeholder="Search 231 species — e.g. Halobacterium, Sulfolobus, putida…" oninput="filterSpecies(this)"><button onclick="var t=document.getElementById('spq');filterSpecies(t)">Search</button></div>
  <div class="hint">Filters the species table below. Bulk/protein-level search: download the SQLite database (Downloads).</div>
  <div class="chips">
    <div class="chip"><b>{totals['species']}</b><span>curated organisms</span></div>
    <div class="chip"><b>{totals['proteins']:,}</b><span>UniProt protein sequences</span></div>
    <div class="chip"><b>{totals['experiments']:,}</b><span>experimental measurements</span></div>
    <div class="chip"><b>{totals['structures']:,}</b><span>AlphaFold structure records</span></div>
  </div>
</div>
<div class="note" data-zh="{esc(notice_zh)}">{esc(notice_en)}</div>
{afp_entry}
<h2 class="sec" data-zh="按环境组浏览">Browse by environmental group</h2>
<div class="grid">{pool_cards}</div>
<h2 class="sec" data-zh="全部物种">All species</h2>
<div class="card">
<table><thead><tr>
  <th onclick="sortTable(this)">Species</th><th onclick="sortTable(this)">Group</th>
  <th onclick="sortTable(this)">Grade</th><th onclick="sortTable(this)">Sequences ▾</th>
  <th onclick="sortTable(this)">Lit. anchored</th></tr></thead>
<tbody>{sp_rows}</tbody></table>
<p class="muted">Click a column header to sort. Per-species pages list every protein with pLDDT and salt-bridge metrics, plus FASTA downloads.</p></div>
<div class="card"><h2 data-zh="准确性核验">Accuracy &amp; provenance</h2>
<p style="font-size:13.5px">Every sequence carries its UniProt accession (open it on uniprot.org to compare) and a SHA-256 checksum.
Every experimental record carries source database and DOI. Literature anchoring status is recorded per species from a strict
Europe PMC co-occurrence search. Human verification flags require written evidence.</p>
<p class="muted">Details: <a href="methods.html">Collection methods</a> · <a href="api.html">Schema &amp; queries</a></p></div>
<div class="card"><h2 data-zh="引用">Citation</h2>
<p style="font-size:13.5px">{esc(cfg['site'].get('citation_en', cfg['site'].get('citation','')))}</p></div>"""
open(f"{OUT}/index.html", "w", encoding="utf-8").write(page("Overview", body, "index.html"))
print("index ✓", flush=True)

# ================= species index =================
body = f"""<div class="card"><h2 data-zh="全部物种">All curated species ({totals['species']})</h2>
<input placeholder="Filter by name / grade / group…" oninput="filterSpecies(this)" style="width:320px;margin-bottom:10px">
<table><thead><tr>
 <th onclick="sortTable(this)">Species</th><th onclick="sortTable(this)">Group</th>
 <th onclick="sortTable(this)">Grade</th><th onclick="sortTable(this)">Sequences</th>
 <th onclick="sortTable(this)">CDS verified</th><th onclick="sortTable(this)">Anchored</th><th onclick="sortTable(this)">Evidence level</th></tr></thead>
<tbody>{''.join(f'<tr data-sp-row><td><a href="{slugify(r["name"])}.html">{esc(r["name"])}</a></td>'
    f'<td>{POOL_EN.get(r["pool"], esc(r["pool"]))}</td><td>{esc(r["grade"] or "—")}</td>'
    f'<td>{(r["n_seqs"] or 0):,}</td>'
    f'<td>{sp_cds.get(r["id"], 0):,}</td>'
    f'<td>{ANCH_OK if r["lit_anchored"] else ANCH_NO}</td>'
    f'<td>{esc(r["evidence_level"] or "—")}</td></tr>' for r in all_species)}</tbody></table></div>"""
open(f"{OUT}/species/index.html", "w", encoding="utf-8").write(page("Species", body, "species", subdir=True))
print("species index ✓", flush=True)

# ================= pool pages =================
for pool in POOLS:
    items = sp_by_pool.get(pool, [])
    trs = "".join(
        f'<tr data-sp-row><td><a href="{slugify(r["name"])}.html">{esc(r["name"])}</a></td>'
        f'<td>{esc(r["grade"] or "—")}</td><td>{(r["n_seqs"] or 0):,}</td>'
        f'<td>{sp_cds.get(r["id"], 0):,}</td>'
        f'<td>{ANCH_OK if r["lit_anchored"] else ANCH_NO}</td></tr>' for r in items)
    en = POOLS.get(pool, {}).get("en") or (cfg["collection"]["pools"][list(POOL_EN).index(pool)].get("en") if False else {})
    b = f'<div class="card"><h2>{esc(POOL_EN.get(pool, pool))} — {len(items)} organisms</h2><table>' \
        '<tr><th>Species</th><th>Grade</th><th>Sequences</th><th>CDS verified</th><th>Anchored</th></tr>' + trs + '</table></div>'
    open(f"{OUT}/species/{pool}.html", "w", encoding="utf-8").write(page(POOL_EN.get(pool, pool), b, "species", subdir=True))
print("pool pages ✓", flush=True)

# ================= per-species pages =================
acc2struct = {}
for r in db.execute("SELECT accession, mean_plddt, salt_bridges_per_100, n_residues, frac_plddt70 FROM structures"):
    acc2struct[r["accession"]] = (r["mean_plddt"], r["salt_bridges_per_100"], r["n_residues"], r["frac_plddt70"])
acc2exp = defaultdict(int)
for r in db.execute("SELECT accession, COUNT(*) c FROM experiments WHERE accession IS NOT NULL GROUP BY accession"):
    acc2exp[r["accession"]] = r["c"]
# 每蛋白参数摘要: kind(短名)+值, 每蛋白最多展示 8 条
KIND_SHORT = {"brenda_ts": "Tstab", "brenda_to": "Topt", "brenda_tr": "Trange",
              "brenda_pho": "pHopt", "brenda_phs": "pHstab", "brenda_phr": "pHrange",
              "brenda_km": "Km", "brenda_tn": "kcat", "brenda_sa": "SpAct",
              "brenda_ki": "Ki", "brenda_ic50": "IC50",
              "meltome_tm": "Tm_cell", "thermomut_ddg": "ddG", "thermomut_dtm": "dTm",
              "ddG": "ddG_fire", "dTm_protherm": "dTm_prot", "Tm_vs_pH": "Tm@pH",
              "dTm_solvent": "dTm_solv", "Tm_aqueous": "Tm_aq", "Tm_solvent": "Tm_solv"}
acc2params = defaultdict(list)
for r in db.execute("""SELECT accession, kind, value, unit FROM experiments
  WHERE accession IS NOT NULL AND value IS NOT NULL
  AND (kind LIKE 'brenda_%' OR kind IN ('meltome_tm','thermomut_ddg','thermomut_dtm','ddG','dTm_protherm','Tm_vs_pH','dTm_solvent','Tm_aqueous','Tm_solvent'))
  ORDER BY accession"""):
    short = KIND_SHORT.get(r["kind"], r["kind"])
    if len(acc2params[r["accession"]]) < 6:
        val = f"{r['value']:g}"
        acc2params[r["accession"]].append(f"{short}={val}{(' ' + r['unit']) if r['unit'] and r['kind'].startswith('brenda_t') else ''}")
# CLEAN EC 预测: 每蛋白最多 3 个高置信 EC (实验参数之后追加, 无实验参数的蛋白以此为主显示)
for r in db.execute("""SELECT accession, ec, confidence FROM clean_ec
  WHERE confidence >= 0.5 ORDER BY accession, confidence DESC"""):
    lst = acc2params[r["accession"]]
    if len([x for x in lst if not x.startswith("EC ")]) >= 6:
        continue
        if len([x for x in lst if x.startswith("EC ")]) < 3:
            lst.append(f"EC {r['ec']} ({r['confidence']:.2f})")

# 物种级文献证据 (v3.6.2): Europe PMC 标题/摘要锚定 + 命名/分类论文; 表不存在时不出卡片
import urllib.parse as _up
lit_stats, lit_papers, lit_names = defaultdict(dict), defaultdict(lambda: defaultdict(list)), defaultdict(list)
lit_phen = defaultdict(list)
try:
    for r in db.execute("SELECT species_id, query_kind, hit_count, query FROM species_literature_stats"):
        lit_stats[r["species_id"]][r["query_kind"]] = (r["hit_count"], r["query"])
    for r in db.execute("""SELECT species_id, query_kind, rank, pmid, pmcid, doi, pub_year, title, journal, cited_by, is_oa
                           FROM species_literature ORDER BY species_id, query_kind, rank"""):
        lit_papers[r["species_id"]][r["query_kind"]].append(r)
    for r in db.execute("SELECT species_id, name FROM species_synonyms ORDER BY species_id, rowid"):
        lit_names[r["species_id"]].append(r["name"])
    for r in db.execute("""SELECT species_id, trait, relation, value_min, value_max, unit, value_text, nacl_molar_min,
                           nacl_molar_max, quote, pmid, doi, pub_year, review_note FROM species_literature_phenotypes
                           WHERE review_status='agent_confirmed' ORDER BY species_id, trait, quote, relation"""):
        lit_phen[r["species_id"]].append(r)
    phen_n, phen_sp = db.execute("SELECT COUNT(*), COUNT(DISTINCT species_id) FROM species_literature_phenotypes").fetchone()
except sqlite3.OperationalError:
    phen_n, phen_sp = 0, 0
    print("species literature tables not present — literature cards skipped", flush=True)


def lit_link(p):
    if p["pmcid"]: return f"https://europepmc.org/article/PMC/{esc(p['pmcid'])}"
    if p["pmid"]: return f"https://europepmc.org/abstract/MED/{esc(p['pmid'])}"
    return f"https://doi.org/{esc(p['doi'])}" if p["doi"] else ""


def lit_block(title, papers):
    if not papers: return ""
    rows = "".join(
        f'<li><a href="{lit_link(p)}" target="_blank" rel="noopener">{esc(p["title"] or p["doi"] or p["pmid"])}</a> '
        f'<span class="muted">({esc(p["pub_year"] or "")}{", " + esc(p["journal"]) if p["journal"] else ""}'
        f'{", cited by " + format(p["cited_by"], ",") if p["cited_by"] is not None else ""})</span></li>'
        for p in papers[:5])
    return f"<li><b>{title}</b><ul>{rows}</ul></li>"


def lit_card(sp):
    sl, sp_ = lit_stats.get(sp["id"], {}), lit_papers.get(sp["id"], {})
    if not sl: return ""
    a = sl.get("anchor")
    bits = []
    if a:
        bits.append(f"<b>{a[0]:,}</b> papers co-mention this species and {esc(POOL_EN.get(sp['pool'], sp['pool'])).lower()} "
                    "terms in title/abstract")
    if "description" in sl:
        bits.append(f"<b>{sl['description'][0]:,}</b> naming or reclassification paper(s) name the species in the title")
    if "genus_anchor" in sl:
        bits.append(f"none at species level; <b>{sl['genus_anchor'][0]:,}</b> papers name only the genus "
                    f"{esc((sp['name'].split() or [''])[0])} with the same terms")
    if "physiology" in sl:
        bits.append(f"<b>{sl['physiology'][0]:,}</b> papers on growth physiology")
    search = (f' · <a href="https://europepmc.org/search?query={_up.quote(a[1])}" target="_blank" rel="noopener">'
              "run this search in Europe PMC ↗</a>") if a else ""
    return f"""<div class="card"><h2>Species literature (Europe PMC)</h2>
<p style="font-size:13.5px">{' · '.join(bits)}{search}</p>
<p class="muted">Searched names: {esc('; '.join(lit_names.get(sp['id'], [])))}. Up to ten most-cited records per search are kept in
<code>species_literature</code>; the exact queries and hit counts are in <code>species_literature_stats</code>.</p>
<ul style="margin-bottom:0">{lit_block('Anchoring literature', sp_.get('anchor', []))}{lit_block('Naming / reclassification papers', sp_.get('description', []))}{lit_block('Growth physiology', sp_.get('physiology', []))}{lit_block('Genus-level anchoring', sp_.get('genus_anchor', []))}</ul></div>"""


def phen_text(r):
    """The value as the paper states it: a range when min and max differ."""
    if r["value_text"]:
        return r["value_text"]
    return f'{r["value_min"]:g}' if r["value_min"] == r["value_max"] else f'{r["value_min"]:g}–{r["value_max"]:g}'


def phen_cell(rows, kind):
    if not rows:
        return "—"
    r = rows[0]
    v = phen_text(r)
    if kind == "range" and r["value_min"] == r["value_max"]:
        v = "at " + v                      # a single-point statement ("capable of growth at 45 °C")
    s = v + ("" if r["trait"] == "temperature" else " " + r["unit"])
    if r["trait"] == "salt_tolerance" and r["unit"] != "M" and r["nacl_molar_min"] is not None:
        lo, hi = r["nacl_molar_min"], r["nacl_molar_max"]
        s += " <span class='muted'>(≈ {} M)</span>".format(f"{lo:.2g}" if abs(hi - lo) < 1e-9 else f"{lo:.2g}–{hi:.2g}")
    return s


def phen_card(sp):
    """Growth conditions (temperature / pH / NaCl) read from the literature and checked sentence by sentence."""
    recs = lit_phen.get(sp["id"], [])
    if not recs:
        return ""
    rows = []
    for trait, label in (("temperature", "Temperature"), ("ph", "pH"), ("salt_tolerance", "NaCl")):
        mine = [r for r in recs if r["trait"] == trait]
        if not mine:
            continue
        by = {k: [r for r in mine if r["relation"] == k] for k in ("growth", "optimum", "minimum", "maximum")}
        limits = "; ".join(x for x in ("≥ " + phen_text(by["minimum"][0]) if by["minimum"] else "",
                                      "≤ " + phen_text(by["maximum"][0]) if by["maximum"] else "") if x)
        rows.append(f"<tr><td>{label}</td><td>{phen_cell(by['growth'], 'range')}</td><td>{phen_cell(by['optimum'], 'opt')}"
                    f"<td>{limits or '—'}</td></tr>")
    sources, seen = [], set()
    for r in recs:
        key = (r["quote"], r["pmid"])
        if key in seen or not r["quote"] or r["quote"] == "see paper":
            continue
        seen.add(key)
        link = (f"https://europepmc.org/abstract/MED/{esc(r['pmid'])}" if r["pmid"] else
                f"https://doi.org/{esc(r['doi'])}" if r["doi"] else "")
        ref = f"<a href='{link}' target='_blank' rel='noopener'>PMID {esc(r['pmid'])}</a>" if r["pmid"] else esc(r["doi"] or "")
        sources.append(f"<li>{esc(r['quote'])} <span class='muted'>— {ref} ({esc(r['pub_year'] or '')})</span></li>")
    notes = " · ".join(dict.fromkeys(r["review_note"] for r in recs if r["review_note"]))
    return f"""<div class="card"><h2>Growth conditions reported in the literature</h2>
<p style="font-size:13.5px">Read from the abstracts of this species' papers and checked sentence by sentence against the source
sentence; values are shown as the paper states them.</p>
<table><tr><th></th><th>Growth range</th><th>Optimum</th><th>Limits</th></tr>{''.join(rows)}</table>
<p class="muted" style="margin-bottom:4px">Source sentences:</p>
<ul style="margin-bottom:0">{''.join(sources)}</ul>
<p class="muted">{esc(notes)}</p></div>"""

count = 0
import json as _json
for pool, items in sp_by_pool.items():
    for sp in items:
        slug = slugify(sp["name"])
        prots = db.execute("SELECT accession, name, length, verified FROM proteins WHERE species_id=? ORDER BY length DESC",
                           (sp["id"],)).fetchall()
        # ── 全蛋白 JSON (供蛋白详情模板页) ──
        data = {}
        for p in prots:
            acc = p["accession"]
            st = acc2struct.get(acc)
            data[acc] = {
                "n": p["name"] or "", "l": p["length"], "v": p["verified"],
                "s": db.execute("SELECT sequence FROM proteins WHERE accession=?", (acc,)).fetchone()[0],
                "st": ({"pl": st[0], "sb": st[1], "nr": st[2], "f70": st[3]} if st else None),
                "ec": [ [r[0], round(r[1] or 0, 2), r[2] or "", r[3] or ""] for r in db.execute(
                    "SELECT ec, confidence, protein_name, gene_name FROM clean_ec WHERE accession=? ORDER BY confidence DESC", (acc,)) ],
                "ex": [ [r[0], r[1], r[2] or "", (r[3] or "")[:200], r[4] or "", (r[5] or "")[:90]] for r in db.execute(
                    "SELECT kind, value, unit, condition, source, source_ref FROM experiments WHERE accession=? AND value IS NOT NULL", (acc,)) ],
                "ipg": ipg.get(acc),
            }
        os.makedirs(f"{OUT}/species/data", exist_ok=True)
        with open(f"{OUT}/species/data/{slug}.json", "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        n_exp = sum(acc2exp.get(p["accession"], 0) for p in prots)
        trs = []
        for p in prots:
            st = acc2struct.get(p["accession"])
            v = V_OK if p["verified"] else ""
            plist = acc2params.get(p["accession"])
            ptxt = (" · ".join(plist) + (f" (+{acc2exp[p['accession']]+1-len(plist)} more exp)" if acc2exp[p["accession"]] > len([x for x in plist if not x.startswith("EC ")]) else "")) if plist else f"<span style='color:#b6bfca'>0 exp</span>"
            acc_cell = f"<a href='../protein/view.html?acc={esc(p['accession'])}&amp;sp={slug}'><code>{esc(p['accession'])}</code></a>"
            trs.append(f"<tr><td>{acc_cell}</td><td>{esc((p['name'] or '')[:64])}</td>"
                       f"<td>{p['length']}</td><td>{(f'{st[0]:.1f} · {st[1]:.2f}' if st else '—')}</td>"
                       f"<td style='font-size:12px'>{ptxt}</td><td>{v}</td></tr>")
        gz = f"downloads/fasta/{slug}.fasta.gz"
        gz_rel = ("../" + gz) if True else gz
        lit = ANCH_OK if sp["lit_anchored"] else ANCH_NO
        prov = rel_links(sp)
        b = f"""<div class="card"><h2>{esc(sp['name'])}</h2>
<p style="font-size:14px">{POOL_EN.get(sp['pool'], esc(sp['pool']))} · grade <b>{esc(sp['grade'] or '—')}</b> ·
NCBI txid {esc(sp['taxon_id'] or '—')} · proteome {esc(sp['proteome_id'] or '—')} ·
<b>{len(prots):,}</b> proteins ({n_exp} experiment-linked) · {lit} ·
evidence {esc(sp['evidence_level'] or '—')}
{('· BacDive optimum ' + esc(sp['bacdive_value']) + ' ' + esc(sp['bacdive_unit'])) if sp['bacdive_value'] is not None else ''}</p>
<p class="muted">Provenance: {prov}{(' · last edited by ' + esc(sp['updated_by'])) if sp['updated_by'] else ''}</p>
<p class="muted">{esc(sp['evidence_note'] or '')} {esc(sp['notes'] or '')}</p>
<p><a class="btn" href="{gz_rel}" download>⬇ FASTA (.fasta.gz)</a>{(' <a class="btn" href="downloads/fasta_cds/' + slug + '.cds.fasta.gz" download>⬇ CDS FASTA (.fasta.gz)</a>') if sp_cds.get(sp['id']) else ''}</p></div>
{lit_card(sp)}
{phen_card(sp)}
<div class="card"><h2>Proteins ({len(prots):,})</h2>
<input placeholder="Filter proteins…" oninput="filterSpecies(this)" style="width:300px;margin-bottom:10px">
<div data-pg-wrap>
<table><thead><tr><th onclick="sortTable(this)">Accession</th><th onclick="sortTable(this)">Protein</th>
<th onclick="sortTable(this)">Length ▾</th><th onclick="sortTable(this)">mean pLDDT · salt-bridges/100</th><th onclick="sortTable(this)">Experimental parameters</th><th onclick="sortTable(this)">Verified</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
<div style="margin:10px 0"><button onclick="pgProt(this,-1)">‹ prev</button> <span class="pgstat"></span> <button onclick="pgProt(this,1)">next ›</button></div></div>
<p class="muted">Click headers to sort. pLDDT and salt-bridge metrics from AlphaFold DB v2.0 records where available.</p></div>"""
        open(f"{OUT}/species/{slug}.html", "w", encoding="utf-8").write(page(sp["name"], b, "species-detail", crumb=True, subdir=True))
        count += 1
        if count % 40 == 0: print(f"  {count}/231", flush=True)
print(f"species pages ✓ ({count})", flush=True)

# ================= solvents =================
sol = defaultdict(list)
for r in db.execute("SELECT solvent, value FROM experiments WHERE kind='dTm_solvent' AND solvent != '' AND value IS NOT NULL"):
    sol[r["solvent"]].append(r["value"])
max_abs = max((abs(median(v)) for v in sol.values()), default=1)
srows = ""
for s, v in sorted(sol.items(), key=lambda kv: median(kv[1])):
    m = median(v)
    w = min(abs(m) / max_abs * 100, 100) if m else 0
    cls = "bar bar-neg" if m < 0 else "bar bar-pos"
    srows += (f"<tr><td>{esc(s)}</td><td>{len(v)}</td><td><b>{m:+.1f}</b></td>"
              f"<td>{min(v):+.1f} ~ {max(v):+.1f}</td>"
              f"<td>{sum(1 for x in v if x<0)}/{len(v)}</td>"
              f"<td style='width:160px'><span class='{cls}' style='width:{w:.0f}%'></span></td></tr>")
b = f"""<div class="note">Effect of organic solvents on protein thermal stability (OrganiZymeDB experimental
measurements; negative ΔTm = destabilizing). Details — concentration, pH, temperature, mutation, DOI — are in
each record; download the SQLite database for the full table.</div>
<div class="card"><h2>Per-solvent aggregation ({len(sol)} solvents, {sum(len(v) for v in sol.values())} measurements)</h2>
<table><thead><tr><th onclick="sortTable(this)">Solvent</th><th onclick="sortTable(this)">n</th>
<th onclick="sortTable(this)">median ΔTm (°C) ▾</th><th onclick="sortTable(this)">range</th>
<th onclick="sortTable(this)">destabilizing</th><th>median (bar)</th></tr></thead>
<tbody>{srows}</tbody></table>
<p class="muted">Alcohol series shows the classic chain-length effect (methanol −9 → ethanol −10 → isopropanol −14 →
tert-butanol −23 °C); DMSO and polyols are mildest. Consistent with the logP correlation (Spearman ρ = −0.502) reported in the manuscript.</p></div>"""
open(f"{OUT}/solvents.html", "w", encoding="utf-8").write(page("Solvents", b, "solvents"))
print("solvents ✓", flush=True)

# ================= experiments =================
kinds = db.execute("""SELECT kind, COUNT(*), SUM(CASE WHEN accession IS NOT NULL THEN 1 ELSE 0 END),
                      ROUND(AVG(value),1) FROM experiments GROUP BY kind ORDER BY 2 DESC""").fetchall()
KIND_EN = {"ddG": "ΔΔG of folding (kcal/mol)", "dTm_protherm": "ΔTm of single-site mutations (°C)",
           "Tm_vs_pH": "Tm at varying pH (°C)", "dTm_solvent": "solvent-induced ΔTm (°C)",
           "Tm_aqueous": "absolute Tm, aqueous control (°C)", "Tm_solvent": "absolute Tm in solvent (°C)",
           "meltome_tm": "in-cell melting temperature (°C, TPP)",
           "brenda_ts": "T_stability (°C)", "brenda_to": "T_optimum (°C)", "brenda_tr": "T_range (°C)",
           "brenda_pho": "pH_optimum", "brenda_phs": "pH_stability", "brenda_phr": "pH_range",
           "brenda_km": "Km, Michaelis constant (µM/mM)",
           "brenda_tn": "kcat turnover number (s⁻¹)",
           "brenda_sa": "specific activity (U/mg)",
           "brenda_ki": "Ki inhibition constant (µM/mM)",
           "brenda_ic50": "IC50 inhibitor concentration (µM/mM)",
           "thermomut_ddg": "ΔΔG of mutation (kcal/mol, ThermoMutDB)",
           "thermomut_dtm": "ΔTm of mutation (°C, ThermoMutDB)"}
krows = "".join(f"<tr><td><span class='badge'>{esc(r[0])}</span> {KIND_EN.get(r[0],'')}</td>"
                f"<td>{r[1]:,}</td><td>{r[2] or 0:,}</td><td>{r[3]}</td>"
                f"<td>{esc(KIND_EN.get(r[0], ''))}</td></tr>" for r in kinds)
b = f"""<div class="note">Experimental layer: {stats_all if False else totals['experiments']:,} records from curated source databases
(FireProtDB, Meltome Atlas, BRENDA, ThermoMutDB, ProThermDB, OrganiZymeDB, pH–Tm compilation). Linked rows carry a UniProt accession;
unlinked rows retain the source wild-type hash for provenance.</div>
<div class="card"><h2>By kind</h2><table><tr><th>kind</th><th>records</th><th>linked</th><th>mean value</th></tr>{krows}</table>
<p class="muted">Full per-record browsing: download the SQLite database. Layer totals:
533,071 (FireProtDB) + 206,549 (Meltome Atlas) + 212,558 (BRENDA stability + kinetics) + 8,239 (ThermoMutDB)
+ 2,921 (ProTherm-L4) + 1,883 (pH–Tm) + 1,833 (OrganiZymeDB) = 967,054.</p>
<p class="muted">Two literature-derived layers were withdrawn and are no longer counted or served; their rows are kept in
<code>experiments_quarantine</code> in the database pending re-curation. The table-extraction layer (5,967 rows, v3.6.1): an audit
found most source papers unrelated to enzyme stability and most values not usable as the stability measure they were labelled with.
The DES stability layer (164 rows, v3.6.3) came from a single paper and is withdrawn pending re-curation.</p></div>"""
open(f"{OUT}/experiments.html", "w", encoding="utf-8").write(page("Experiments", b, "experiments"))

# ================= methods =================
col = cfg.get("collection", {})
POOL_KEY_EN = {"thermo": "thermo", "salt": "salt", "ph": "ph", "solvent": "solvent", "meso": "meso", "experiments": "experiments"}
mcards = []
for p in col.get("pools", []):
    en = p.get("en") or {}
    zh_block = f"<details><summary data-zh='中文协议原文'>Chinese protocol (原文)</summary>" \
               f"<p style='font-size:13px'><b>入选标准</b>：{esc(p.get('criteria',''))}</p>" \
               f"<p style='font-size:13px'><b>文献锚定</b>：{esc(p.get('anchoring',''))}</p>" \
               f"<p style='font-size:13px'><b>实验校准</b>：{esc(p.get('calibration',''))}</p></details>" if p.get("criteria") else ""
    en_block = ""
    if en:
        en_block = f"""<p style="font-size:13.5px"><b>Inclusion criteria</b> — {esc(en.get('criteria',''))}</p>
<p style="font-size:13.5px"><b>Literature anchoring</b> — {esc(en.get('anchoring',''))}</p>
<p style="font-size:13.5px"><b>Experimental calibration</b> — {esc(en.get('calibration',''))}</p>"""
    title = p.get("pool", "")
    mcards.append(f"<div class='card'><h2>{esc(POOL_EN.get(title, title))}</h2>{en_block}{zh_block}</div>")
b = f"""<div class="note">{esc(col.get('_intro_en',''))}</div>{''.join(mcards)}
<div class="card"><h2>Shared retrieval pipeline</h2>
<pre>1. UniProt taxonomy API — exact scientific-name resolution → taxon ID
2. Reference proteome where available, else all proteins of the taxon (REST, TSV)
3. Filter ≥50 aa, standard amino acids; MD5 exact dedup
4. Redundancy scope per pool (recorded): thermo = 30% cluster reps;
   salt / pH / solvent = 90% linclust reps; controls = exact dedup
5. Literature anchoring (v3.6.2): Europe PMC TITLE_ABS co-occurrence of the species name
   (current name plus NCBI-listed earlier names sharing the epithet) with pool-specific
   environmental terms; naming/reclassification papers name the species in the title
   together with sp. nov. / gen. nov. / comb. nov.
6. BacDive calibration: Halophily table (NaCl → M) and optimal culture pH</pre></div>
<div class="card"><h2>Growth conditions from the literature (v3.8.0)</h2>
<p style="font-size:13.5px">Growth temperature, pH and NaCl ranges and optima are read from the abstracts of the papers stored for each
species (naming and reclassification papers, growth-physiology papers, anchoring literature). A rule-based parser selects
sentences that speak about growth and state one of the three, and reads the growth range, the optimum and the limits from
each sentence together with the sentence itself.</p>
<p style="font-size:13.5px">Every statement was then reviewed sentence by sentence against its source sentence by an AI agent (ZCode), not by a
human curator: {phen_n:,} statements for {phen_sp} of the 284 environment-tolerant species were confirmed (52 species after
correcting the parsed values) and 73 candidate papers were rejected, mostly naming papers that describe another species and
only mention this one. Only confirmed statements are served; each keeps its source sentence and PMID.</p>
<p style="font-size:13.5px">An automated audit checks that every stored sentence occurs verbatim in its paper's abstract, that the paper names the
species, and that range, optimum and limits of one trait do not contradict each other. Values are shown as the paper states
them; NaCl given in % (w/v), g/l or mM is also stored in mol/l.</p></div>
<div class="card"><h2 data-zh="中文协议原文（全部组）">Chinese protocol (原文)</h2>
<details><summary data-zh='展开'>Expand</summary>
<pre>{esc(col.get('_intro',''))}</pre>
{''.join(f"<p style='font-size:13px'><b>{esc(p.get('title',''))}</b><br>{esc(p.get('criteria',''))}</p>" for p in col.get('pools', []))}
</details></div>
{afp_methods}"""
open(f"{OUT}/methods.html", "w", encoding="utf-8").write(page("Methods", b, "methods"))
print("methods ✓", flush=True)

# ================= per-species CDS FASTA downloads (v3.7.1) =================
import gzip as _gzip
os.makedirs(f"{OUT}/downloads/fasta_cds", exist_ok=True)
sid2slug = {}
for _pool in POOLS:
    for _sp in sp_by_pool.get(_pool, []):
        sid2slug[_sp["id"]] = slugify(_sp["name"])
_cur_sid, _fh = None, None
_n_files = 0
for r in db.execute("SELECT species_id, accession, nucleotide, start, stop, strand, sequence FROM gene_sequences ORDER BY species_id, accession"):
    if r["species_id"] != _cur_sid:
        if _fh: _fh.close()
        _cur_sid, _fh = r["species_id"], None
        _slug = sid2slug.get(r["species_id"])
        if _slug:
            _fh = _gzip.open(f"{OUT}/downloads/fasta_cds/{_slug}.cds.fasta.gz", "wt", compresslevel=9)
            _n_files += 1
    if _fh:
        _seq = r["sequence"] or ""
        _fh.write(">%s %s:%s-%s(%s) cds_len=%d\n%s\n" % (r["accession"], r["nucleotide"], r["start"], r["stop"], r["strand"], len(_seq), _seq))
if _fh: _fh.close()
print(f"CDS FASTA: {_n_files} species files, {sum(os.path.getsize(f'{OUT}/downloads/fasta_cds/{x}') for x in os.listdir(f'{OUT}/downloads/fasta_cds'))/1e6:.1f} MB gz", flush=True)

# ================= downloads =================
import hashlib
files = []
for root, _, fs in os.walk(f"{OUT}/downloads"):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        rel = os.path.relpath(fp, OUT)
        files.append((rel.replace(os.sep, "/"), os.path.getsize(fp)))
fa_files = [f for f in files if f[0].startswith("downloads/fasta/")]
tsv_files = [f for f in files if f[0].startswith("downloads/tsv/")]
cds_files = [f for f in files if f[0].startswith("downloads/fasta_cds/")]
crows = "".join(f"<tr><td>{esc(os.path.basename(f[0]).replace('.cds.fasta.gz',''))}</td><td><a href='{esc(f[0])}' download>{esc(f[0])}</a></td><td>{f[1]/1e6:.2f} MB</td></tr>" for f in cds_files)
frows = "".join(f"<tr><td>{esc(os.path.basename(f[0]).replace('.fasta.gz',''))}</td>"
                f"<td><a href='{esc(f[0])}' download>{esc(f[0])}</a></td><td>{f[1]/1e6:.2f} MB</td></tr>" for f in fa_files)
trows = "".join(f"<tr><td><a href='{esc(f[0])}' download>{esc(os.path.basename(f[0]))}</a></td><td>{f[1]/1024:.1f} KB</td></tr>" for f in tsv_files)
b = f"""<div class="note">Everything below is generated from the EnvTolDB SQLite database
({totals['proteins']:,} proteins, {totals['experiments']:,} measurements). Integrity: SHA-256 in
<a href="downloads/CHECKSUMS.txt">CHECKSUMS.txt</a>.</div>
<div class="card"><h2>Full database</h2>
<p style="font-size:13.5px"><a class="btn" href="downloads/dataset.db.gz" download>⬇ dataset.db.gz</a>
(gzip; uncompress → <code>sqlite3 dataset.db</code>. Schema and example queries on the <a href="api.html">API page</a>.)</p></div>
<div class="card"><h2>Per-species FASTA ({len(fa_files)} files, {sum(f[1] for f in fa_files)/1e6:.0f} MB total)</h2>
<table><tr><th>Species</th><th>File</th><th>Size</th></tr>{frows}</table></div>
<div class="card"><h2>Per-species CDS FASTA ({len(cds_files)} files, {sum(f[1] for f in cds_files)/1e6:.0f} MB total)</h2>
<table><tr><th>Species</th><th>File</th><th>Size</th></tr>{crows}</table></div>
<div class="card"><h2>Species tables TSV ({len(tsv_files)})</h2><table>{''.join(f"<tr><td>{esc(os.path.basename(f[0]))}</td><td>{f[1]/1024:.0f} KB</td></tr>" for f in tsv_files)}</table></div>
{afp_downloads}"""
open(f"{OUT}/downloads.html", "w", encoding="utf-8").write(page("Downloads", b, "downloads"))
print("downloads ✓", flush=True)

# ================= API / schema page =================
def _n(t):
    try: return f"{db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:,}"
    except sqlite3.OperationalError: return "—"
lit_counts = " / ".join(_n(t) for t in ("species_synonyms", "species_literature", "species_literature_stats"))
quar_counts = " / ".join(_n(t) for t in ("experiments_quarantine", "record_evidence_quarantine"))
gene_counts = " / ".join(_n(t) for t in ("gene_coordinates", "gene_sequences", "gene_mapping_status"))
b = f"""<div class="note">This GitHub Pages mirror is static. For programmatic access, download the SQLite
database (Downloads) — every table below is a plain SQL table. A REST API also exists on the
self-hosted instance.</div>
<div class="card"><h2>Schema</h2>
<table><tr><th>table</th><th>columns (key ones)</th><th>rows</th></tr>
<tr><td><code>species</code></td><td>name, taxon_id, pool, grade, proteome_id, n_seqs, lit_anchored, evidence_level, bacdive_value, attrs</td><td>{totals['species']}</td></tr>
<tr><td><code>proteins</code></td><td>accession, species_id, name, length, sequence, seq_sha256, source, verified, evidence, attrs</td><td>{totals['proteins']:,}</td></tr>
<tr><td><code>experiments</code></td><td>accession, kind, value, unit, condition, mutation, wt_sha256, source, source_ref</td><td>{totals['experiments']:,}</td></tr>
<tr><td><code>structures</code></td><td>accession, pool, n_residues, mean_plddt, frac_plddt70, salt_bridges_per_100</td><td>{totals['structures']:,}</td></tr>
<tr><td><code>literature</code> / <code>measurements</code> / <code>import_batches</code> / <code>audit_log</code></td>
<td>anchoring hits, BacDive-style measurements, source declarations, edit history</td><td>—</td></tr>
<tr><td><code>species_synonyms</code> / <code>species_literature</code> / <code>species_literature_stats</code></td>
<td>names searched per species; most-cited Europe PMC papers per search; hit count and exact query</td>
<td>{lit_counts}</td></tr>
<tr><td><code>gene_coordinates</code> / <code>gene_sequences</code> / <code>gene_mapping_status</code></td>
<td>genomic coordinates (NCBI IPG + EBI), verified CDS sequences, per-protein mapping status</td>
<td>{gene_counts}</td></tr>
<tr><td><code>species_literature_phenotypes</code></td>
<td>growth temperature / pH / NaCl range, optimum and limits read from paper abstracts and reviewed sentence by sentence; value, unit, sentence, PMID</td>
<td>{_n("species_literature_phenotypes")}</td></tr>
<tr><td><code>experiments_quarantine</code> / <code>record_evidence_quarantine</code></td>
<td>withdrawn records with their evidence rows — not counted or served; original ids kept</td><td>{quar_counts}</td></tr>
{afp_schema}</table></div>
<div class="card"><h2>Example queries</h2>
<pre>-- proteins of one species, longest first
sqlite3 dataset.db "SELECT accession, name, length FROM proteins p
  JOIN species s ON s.id=p.species_id WHERE s.name='Halobacterium salinarum'
  ORDER BY length DESC LIMIT 20"

-- most destabilizing solvent measurements
sqlite3 dataset.db "SELECT accession, value, condition, source_ref FROM experiments
  WHERE kind='dTm_solvent' ORDER BY value LIMIT 20"

-- proteins with structure and high salt-bridge density
sqlite3 dataset.db "SELECT accession, mean_plddt, salt_bridges_per_100 FROM structures
  WHERE salt_bridges_per_100 > 6 ORDER BY 3 DESC"

-- gene coordinates + mapping status for one protein
sqlite3 dataset.db "SELECT accession, nucleotide, start, stop, strand, mapping_status
  FROM gene_mapping_status WHERE accession='P42920'"</pre></div>
<div class="card"><h2>Self-hosted REST API (on the internal instance)</h2>
<table><tr><th>Method</th><th>Path</th><th>Description</th></tr>
<tr><td>GET</td><td><code>/api/dataset/stats</code></td><td>totals per layer and per pool</td></tr>
<tr><td>GET</td><td><code>/api/dataset/species?pool=&amp;q=&amp;limit=</code></td><td>species list</td></tr>
<tr><td>GET</td><td><code>/api/dataset/proteins?acc=&amp;motif=&amp;format=fasta</code></td><td>protein search / FASTA</td></tr>
<tr><td>GET</td><td><code>/api/dataset/export/&lt;pool&gt;.tsv</code></td><td>species TSV per pool</td></tr>
<tr><td>PATCH</td><td><code>/api/dataset/species/{id}</code></td><td>edit (admin, audit-logged)</td></tr></table></div>
<div class="card"><h2 data-zh="引用">Citation</h2>
<p style="font-size:13.5px">{esc(cfg['site'].get('citation_en', cfg['site'].get('citation','')))}</p></div>"""
open(f"{OUT}/api.html", "w", encoding="utf-8").write(page("API", b, "api"))
print("api ✓", flush=True)

# ================= Pages workflow =================
wf = """name: Deploy EnvTolDB to GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - id: deployment
        uses: actions/deploy-pages@v4
"""
open(f"{OUT}/.github/workflows/deploy.yml", "w").write(wf)
if afp_present:
    print("AFP/IBP subset", json.dumps(build_afp_site(DB, OUT)), flush=True)
db.close()
total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
nfiles = sum(len(fs) for _, _, fs in os.walk(OUT))
print(f"SITE v2 DONE → {OUT}（{total/1e6:.0f} MB, {nfiles} files）")
