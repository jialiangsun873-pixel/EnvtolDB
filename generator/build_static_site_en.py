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

DB = "/public/home/sjl2/datasetdb/dataset.db"
CFG = "/public/home/sjl2/datasetdb/config.json"
OUT = "/public/home/sjl2/envtoldb_site"          # repo root = site root
NOW = datetime.datetime.now().strftime("%Y-%m-%d")
RELEASE = "v3.1"

cfg = json.load(open(CFG, encoding="utf-8"))
db = sqlite3.connect(DB, timeout=60)
db.row_factory = sqlite3.Row
db.execute("PRAGMA busy_timeout=60000")

POOLS = {p["key"]: p for p in cfg["pools"]}
POOL_EN = {"thermo": "Thermophilic", "salt": "Halophilic", "ph": "Acid/Alkaliphilic", "metal": "Metal-resistant", "endolithic": "Endolithic", "xerophilic": "Xerophilic", "cold": "Cold-adapted", "piezo": "Piezophilic", "rad": "Radiation-resistant",
           "solvent": "Solvent-tolerant", "meso": "Mesophilic controls", "cold": "Cold-adapted",
           "arsenic": "Arsenic-resistant", "magnetotactic": "Magnetotactic", "oligotrophic": "Oligotrophic"}
POOL_ZH = {"thermo": "嗜热", "salt": "耐盐", "ph": "耐酸碱", "solvent": "耐溶剂", "meso": "中温对照", "cold": "嗜冷", "piezo": "嗜压", "rad": "耐辐射", "metal": "耐重金属", "endolithic": "石内内生", "xerophilic": "耐干燥",
           "arsenic": "耐砷", "magnetotactic": "趋磁", "oligotrophic": "耐贫营养"}

for sub in ("species", "protein", "downloads/fasta", "downloads/tsv", ".github/workflows"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
open(f"{OUT}/.nojekyll", "w").close()

ANCH_OK = '<span class="badge b-ok">yes</span>'
ANCH_NO = '<span class="badge b-no">no</span>'
V_OK = '<span class="badge b-ok">✓</span>'

def esc(s): return html.escape(str(s if s is not None else ""))
def slugify(name): return name.replace(" ", "_").replace("/", "_")

# ---------------- shared chrome ----------------
CSS = """
:root{--ink:#13233b;--soft:#43597a;--faint:#7285a0;--line:#d9e4f0;--bg:#f5f8fc;--card:#fff;
 --accent:#1668dc;--accent-ink:#0d4bb5;--ok:#17805f;--ok-bg:#e4f4ee;--no:#c4424f;--no-bg:#fdeef0;
 --radius:8px;--shadow:0 1px 3px rgba(15,40,80,.08)}
*{box-sizing:border-box}
body{font-family:Inter,-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',sans-serif;margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.55}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);padding:10px 26px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:9px;font-size:17px;font-weight:700;color:var(--ink)}
.brand svg{width:26px;height:26px;color:var(--accent)}
.brand small{display:block;font-weight:400;font-size:11px;color:var(--faint);margin-top:-2px}
nav{display:flex;gap:2px;flex-wrap:wrap}
nav a{padding:5px 11px;border-radius:6px;color:var(--soft);font-size:13.5px}
nav a:hover{background:#eef3f9;color:var(--ink);text-decoration:none}
nav a.on{background:#e7f0fb;color:var(--accent-ink);font-weight:600}
.hdr-right{margin-left:auto;display:flex;align-items:center;gap:10px}
.langbtn{border:1px solid var(--line);background:#fff;border-radius:6px;padding:4px 10px;font-size:12.5px;cursor:pointer;color:var(--soft)}
.gh{font-size:12.5px;color:var(--soft);border:1px solid var(--line);border-radius:6px;padding:4px 10px}
.gh:hover{color:var(--ink)}
main{max-width:1140px;margin:0 auto;padding:26px 18px 70px}
.hero{background:linear-gradient(180deg,#eef4fb,#f8fbff);border:1px solid var(--line);border-radius:var(--radius);padding:34px 34px 26px;margin-bottom:22px}
.hero h1{font-size:30px;margin:0 0 4px;letter-spacing:-.3px}
.hero .tag{font-size:15px;color:var(--soft);margin-bottom:16px}
.badge-line{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.rel{background:var(--accent);color:#fff;font-size:12px;padding:3px 10px;border-radius:12px;font-weight:600}
.rel2{background:#fff;border:1px solid var(--line);color:var(--soft);font-size:12px;padding:3px 10px;border-radius:12px}
.srch{display:flex;gap:8px;max-width:560px}
.srch input{flex:1;padding:10px 14px;font-size:14px;border:1.5px solid #b9cbe2;border-radius:8px}
.srch input:focus{outline:2px solid #9cc3e5;border-color:var(--accent)}
.srch button{padding:10px 20px;font-size:14px;border-radius:8px;background:var(--accent);color:#fff;border:none;cursor:pointer;font-weight:600}
.hint{font-size:12px;color:var(--faint);margin-top:6px}
.chips{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}
.chip{background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 16px;min-width:150px}
.chip b{font-size:21px;display:block}
.chip span{font-size:11.5px;color:var(--faint)}
h2.sec{font-size:19px;margin:26px 0 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px}
.pcard b{font-size:15px}.pcard .n{font-size:24px;font-weight:700;display:block;margin:2px 0}
.pcard .m{font-size:12px;color:var(--faint);display:block;margin-bottom:8px}
table{border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
th{background:#eef3f9;text-align:left;padding:8px 10px;font-weight:600;white-space:nowrap;cursor:pointer;user-select:none}
th:hover{background:#e2ecf6}
td{padding:6px 10px;border-bottom:1px solid #ecf2f8}
tr:hover td{background:#f4f8fd}
.badge{display:inline-block;padding:1px 9px;border-radius:11px;font-size:11.5px;white-space:nowrap}
.b-ok{background:var(--ok-bg);color:#146a50}.b-no{background:#fdeef0;color:#c4424f}
.b-grade{background:#e7f0fb;color:var(--accent-ink)}
.bar{height:12px;border-radius:6px;display:inline-block;vertical-align:middle}
.bar-neg{background:#e58a93}.bar-pos{background:#7bbf9e}
.muted{color:var(--faint);font-size:12.5px}
.note{background:#e4f4ee;border:1px solid #bfe3d6;color:#146a50;padding:9px 14px;border-radius:6px;margin-bottom:16px;font-size:13.5px}
.err{background:#fdeef0;border:1px solid #f3c6cb;color:#c4424f;padding:8px 14px;border-radius:6px;margin-bottom:14px;font-size:13px}
code{font-family:ui-monospace,'JetBrains Mono',monospace;font-size:12px;background:#eef3f9;padding:1px 5px;border-radius:3px}
pre{background:#eef3f9;padding:12px;border-radius:6px;font-size:12.5px;overflow:auto;max-height:360px}
input,button{font-size:13.5px;padding:7px 11px;border:1px solid #b9cbe2;border-radius:6px;background:#fff;color:var(--ink);font-family:inherit}
button{background:var(--accent);color:#fff;border:none;cursor:pointer;font-weight:600}
button:hover{background:var(--accent-ink)}
details{border:1px solid var(--line);border-radius:6px;padding:10px 14px;margin:8px 0;background:#fff}
summary{cursor:pointer;font-weight:600;font-size:13.5px}
.crumb{font-size:12.5px;color:var(--faint);margin-bottom:14px}
.crumb a{color:var(--faint)}
footer{max-width:1140px;margin:30px auto 50px;padding:16px 18px;border-top:1px solid var(--line);color:var(--faint);font-size:12.5px}
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
}
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
             ("solvents.html", "Solvents", "溶剂统计"), ("experiments.html", "Experiments", "实验参数"),
             ("methods.html", "Methods", "采集方法"), ("downloads.html", "Downloads", "下载"),
             ("api.html", "API", "API")]
    nav = "".join(
        f'<a href="{pre}{h}" class="{"on" if k==active else ""}" data-zh="{zh}">{t}</a>'
        for h, t, k, zh in [(h, t, k, zh) for (h, t, k, zh) in
                            [(i[0], i[1], i[2], i[3]) for i in
                             [("index.html","Overview","","总览"),("species/index.html","Species","","物种"),
                              ("solvents.html","Solvents","","溶剂统计"),("experiments.html","Experiments","","实验参数"),
                              ("methods.html","Methods","","采集方法"),("downloads.html","Downloads","","下载"),
                              ("api.html","API","","API")]]])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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

# ================= index =================
notice_en = cfg["site"].get("notice_en", "").format(n_pools=len(POOLS), n_species=totals["species"], n_proteins=totals["proteins"])
notice_zh = cfg["site"].get("notice", "").format(n_pools=len(POOLS), n_species=totals["species"], n_proteins=totals["proteins"])

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
  <div class="badge-line"><span class="rel">Release {esc(RELEASE)}</span><span class="rel2">Data as of 2026-11-16</span><span class="rel2">Source: UniProtKB 2026_01</span></div>
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
 <th onclick="sortTable(this)">Anchored</th><th onclick="sortTable(this)">Evidence level</th></tr></thead>
<tbody>{''.join(f'<tr data-sp-row><td><a href="{slugify(r["name"])}.html">{esc(r["name"])}</a></td>'
    f'<td>{POOL_EN.get(r["pool"], esc(r["pool"]))}</td><td>{esc(r["grade"] or "—")}</td>'
    f'<td>{(r["n_seqs"] or 0):,}</td>'
    f'<td>{ANCH_OK if r["lit_anchored"] else ANCH_NO}</td>'
    f'<td>{esc(r["evidence_level"] or "—")}</td></tr>' for r in all_species)}</tbody></table></div>"""
open(f"{OUT}/species/index.html", "w", encoding="utf-8").write(page("Species", body, "species"))
print("species index ✓", flush=True)

# ================= pool pages =================
for pool in POOLS:
    items = sp_by_pool.get(pool, [])
    trs = "".join(
        f'<tr data-sp-row><td><a href="{slugify(r["name"])}.html">{esc(r["name"])}</a></td>'
        f'<td>{esc(r["grade"] or "—")}</td><td>{(r["n_seqs"] or 0):,}</td>'
        f'<td>{ANCH_OK if r["lit_anchored"] else ANCH_NO}</td></tr>' for r in items)
    en = POOLS.get(pool, {}).get("en") or (cfg["collection"]["pools"][list(POOL_EN).index(pool)].get("en") if False else {})
    b = f'<div class="card"><h2>{esc(POOL_EN.get(pool, pool))} — {len(items)} organisms</h2><table>' \
        '<tr><th>Species</th><th>Grade</th><th>Sequences</th><th>Anchored</th></tr>' + trs + '</table></div>'
    open(f"{OUT}/species/{pool}.html", "w", encoding="utf-8").write(page(POOL_EN.get(pool, pool), b, "species"))
print("pool pages ✓", flush=True)

# ================= per-species pages =================
PROTEIN_PAGES = {r[0] for r in db.execute(
    "SELECT DISTINCT accession FROM experiments WHERE accession IS NOT NULL AND EXISTS (SELECT 1 FROM proteins p WHERE p.accession=experiments.accession)")}
print(f"蛋白详情页: {len(PROTEIN_PAGES):,}", flush=True)
acc2struct = {}
for r in db.execute("SELECT accession, mean_plddt, salt_bridges_per_100 FROM structures"):
    acc2struct[r["accession"]] = (r["mean_plddt"], r["salt_bridges_per_100"])
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
              "dTm_solvent": "dTm_solv", "Tm_aqueous": "Tm_aq", "Tm_solvent": "Tm_solv",
              "des_k_inact": "k_inact", "des_t_half": "t½"}
acc2params = defaultdict(list)
for r in db.execute("""SELECT accession, kind, value, unit FROM experiments
  WHERE accession IS NOT NULL AND value IS NOT NULL
  AND (kind LIKE 'brenda_%' OR kind IN ('meltome_tm','thermomut_ddg','thermomut_dtm','ddG','dTm_protherm','Tm_vs_pH','dTm_solvent','Tm_aqueous','Tm_solvent','des_k_inact','des_t_half'))
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

count = 0
for pool, items in sp_by_pool.items():
    for sp in items:
        slug = slugify(sp["name"])
        prots = db.execute("SELECT accession, name, length, verified FROM proteins WHERE species_id=? ORDER BY length DESC",
                           (sp["id"],)).fetchall()
        n_exp = sum(acc2exp.get(p["accession"], 0) for p in prots)
        trs = []
        for p in prots:
            st = acc2struct.get(p["accession"])
            v = V_OK if p["verified"] else ""
            plist = acc2params.get(p["accession"])
            ptxt = (" · ".join(plist) + (f" (+{acc2exp[p['accession']]+1-len(plist)} more exp)" if acc2exp[p["accession"]] > len([x for x in plist if not x.startswith("EC ")]) else "")) if plist else f"<span style='color:#b6bfca'>0 exp</span>"
            acc_cell = (f"<a href='../protein/{esc(p['accession'])}.html'><code>{esc(p['accession'])}</code></a>"
                        if p["accession"] in PROTEIN_PAGES else f"<code>{esc(p['accession'])}</code>")
            trs.append(f"<tr><td>{acc_cell}</td><td>{esc((p['name'] or '')[:64])}</td>"
                       f"<td>{p['length']}</td><td>{f'{st[0]:.1f}' if st else '—'}</td>"
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
<p><a class="btn" href="{gz_rel}" download>⬇ FASTA (.fasta.gz)</a></p></div>
<div class="card"><h2>Proteins ({len(prots):,})</h2>
<input placeholder="Filter proteins…" oninput="filterSpecies(this)" style="width:300px;margin-bottom:10px">
<table><thead><tr><th onclick="sortTable(this)">Accession</th><th onclick="sortTable(this)">Protein</th>
<th onclick="sortTable(this)">Length ▾</th><th onclick="sortTable(this)">mean pLDDT</th><th onclick="sortTable(this)">Experimental parameters</th><th onclick="sortTable(this)">Verified</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
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
# ================= protein detail pages =================
import time as _time
_t0p = _time.time()
ipg = {}
try:
    for line in open("/public/home/sjl2/datasetdb/gene_seqs/ipg_map.tsv"):
        p_ = line.rstrip("\n").split("\t")
        if len(p_) >= 5 and p_[1] != "MISS" and p_[0] not in ipg:
            ipg[p_[0]] = (p_[1], p_[2], p_[3], p_[4])
except FileNotFoundError:
    pass
print(f"IPG 坐标可用: {len(ipg):,}", flush=True)

uni_base = "https://www.uniprot.org/uniprotkb/"
af_base = "https://alphafold.ebi.ac.uk/"
for acc in sorted(PROTEIN_PAGES):
    prow = db.execute("SELECT name, length, sequence, verified FROM proteins WHERE accession=?", (acc,)).fetchone()
    if not prow:
        continue
    pname, plen, pseq, pver = prow
    exp_rows = db.execute("""SELECT kind, value, unit, condition, source, source_ref, evidence
        FROM experiments WHERE accession=? AND value IS NOT NULL ORDER BY kind""", (acc,)).fetchall()
    ec_rows = db.execute("""SELECT ec, confidence, protein_name, gene_name, enzyme_function FROM clean_ec
        WHERE accession=? ORDER BY confidence DESC""", (acc,)).fetchall()
    st = acc2struct.get(acc)
    n_exp_all = acc2exp.get(acc, 0)
    erows = "".join(
        f"<tr><td>{esc(KIND_SHORT.get(k, k))}</td><td><b>{val:g}</b> {esc(u or '')}</td>"
        f"<td style='font-size:12px'>{esc(c[:160] if c else '')}</td>"
        f"<td style='font-size:12px'>{esc(src2)}{('<br><span style=color:#6b7a8d>' + esc(ref[:70]) + '</span>') if ref else ''}</td></tr>"
        for k, val, u, c, src2, ref, ev in exp_rows)
    ec_html = ""
    if ec_rows:
        ec_html = "<div class='card'><h2>CLEAN predicted EC functions</h2><table><tr><th>EC</th><th>confidence</th><th>protein</th><th>gene</th><th>function</th></tr>" + "".join(
            f"<tr><td><a href='https://www.rhea-db.org/searchresults?query={ec}' target=_blank rel=noopener><code>{ec}</code></a></td>"
            f"<td>{(cf or 0):.2f}</td><td style='font-size:12px'>{esc(pn[:80])}</td><td style='font-size:12px'>{esc(gn)}</td>"
            f"<td style='font-size:12px'>{esc(fn2[:120])}</td></tr>"
            for ec, cf, pn, gn, fn2 in ec_rows) + "</table></div>"
    seq_html = ""
    if pseq:
        wrapped = "<br>".join(pseq[i:i+60] for i in range(0, len(pseq), 60))
        seq_html = f"<div class='card'><h2>Sequence ({len(pseq)} aa)</h2><code style='font-size:11px;word-break:break-all'>{wrapped}</code></div>"
    gene_html = ""
    if acc in ipg:
        nt, s0, s1, strand = ipg[acc]
        gene_html = (f"<div class='card'><h2>Gene (CDS coordinates)</h2>"
                     f"<p><code>{nt}</code> {s0}–{s1} ({'+' if strand=='+' else '−'} strand, {int(s1)-int(s0)+1 if s0 and s1 else '?'} nt) · "
                     f"<a href='https://www.ncbi.nlm.nih.gov/nuccore/{nt}?report=fasta&from={s0}&to={s1}&strand=2' target=_blank rel=noopener>CDS FASTA at NCBI</a> · "
                     f"gene-sequence layer collecting (IPG pipeline)</p></div>")
    else:
        gene_html = ("<div class='card'><h2>Gene</h2><p class='muted'>Genome mapping in progress "
                     "(NCBI IPG pipeline running; this protein has no RefSeq CDS mapping yet).</p></div>")
    links = (f"<a href='{uni_base}{acc}' target=_blank rel=noopener>UniProt</a> · "
             f"<a href='{af_base}search?query={acc}' target=_blank rel=noopener>AlphaFold</a> · "
             f"<a href='https://www.ncbi.nlm.nih.gov/protein/{acc}' target=_blank rel=noopener>NCBI</a> · "
             f"<a href='https://europepmc.org/search?query={acc}' target=_blank rel=noopener>Europe PMC</a>")
    body = f"""<div class="card"><h2>{esc(acc)} — {esc(pname or '')}</h2>
<p style="font-size:14px">length <b>{plen}</b> aa · verified {V_OK if pver else '<span class="badge b-no">no</span>'} ·
{('mean pLDDT <b>' + f"{st[0]:.1f}" + '</b> · salt bridges/100 <b>' + f"{st[1]:.2f}" + '</b>') if st else 'no structure record'} ·
<b>{n_exp_all}</b> experiment-linked records · {links}</p>
<p class="muted">All experimental records for this protein, across sources, with per-record conditions and DOIs.</p></div>
{f"<div class='card'><h2>Experimental records ({len(exp_rows)})</h2><table><tr><th>kind</th><th>value</th><th>conditions</th><th>source / ref</th></tr>{erows}</table></div>" if exp_rows else "<div class='card'><h2>Experimental records</h2><p class='muted'>No measured parameters link to this protein yet.</p></div>"}
{ec_html}
{gene_html}
{seq_html}"""
    open(f"{OUT}/protein/{acc}.html", "w", encoding="utf-8").write(
        page(f"{acc} — {(pname or '')[:40]}", body, "species", crumb=True, subdir=True))

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
           "thermomut_dtm": "ΔTm of mutation (°C, ThermoMutDB)",
           "salt_tab_tab": "salt stability table value", "arsenic_tab_tab": "arsenic stability table value",
           "magnetotactic_tab_tab": "magnetotactic stability table value",
           "oligotrophic_tab_tab": "oligotrophic stability table value",
           "des_k_inact": "k_inact in DES (DES literature)",
           "des_t_half": "t½ in DES (min, DES literature)"}
krows = "".join(f"<tr><td><span class='badge'>{esc(r[0])}</span> {KIND_EN.get(r[0],'')}</td>"
                f"<td>{r[1]:,}</td><td>{r[2] or 0:,}</td><td>{r[3]}</td>"
                f"<td>{esc(KIND_EN.get(r[0], ''))}</td></tr>" for r in kinds)
des_n = db.execute("SELECT COUNT(*) FROM experiments WHERE kind LIKE 'des_%'").fetchone()[0]
b = f"""<div class="note">Experimental layer: {stats_all if False else totals['experiments']:,} records from four sources
(OrganiZymeDB, FireProtDB, ProThermDB-L4, pH–Tm compilation). Linked rows carry a UniProt accession;
unlinked rows retain the source wild-type hash for provenance.</div>
<div class="card"><h2>By kind</h2><table><tr><th>kind</th><th>records</th><th>linked</th><th>mean value</th></tr>{krows}</table>
<p class="muted">Full per-record browsing: download the SQLite database. Layer totals:
533,071 (FireProtDB) + 206,549 (Meltome Atlas) + 212,538 (BRENDA stability + kinetics) + 8,239 (ThermoMutDB)
+ 2,921 (ProTherm-L4) + 1,883 (pH–Tm) + 1,833 (OrganiZymeDB) + 5,967 (literature table mining) + 164 (DES) ≈ 973,000.</p></div>
<div class="card"><h2>Deep-eutectic-solvent (DES) subset</h2>
<p style="font-size:13.5px">{des_n} records from 3 dehydrogenases (ADH-A, Lk-ADH, GDH) across 11 ChCl/betaine-based
DES systems (water 10–50 wt %, 30 °C incubation): <code>des_k_inact</code> (82) and <code>des_t_half</code> (82).
53 records carry UniProt accessions; the GDH arm is <code>needs_review</code> pending plasmid-level identification.</p></div>"""
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
5. Literature anchoring: Europe PMC co-occurrence (species × environment terms, title/abstract)
6. BacDive calibration: Halophily table (NaCl → M) and optimal culture pH</pre></div>
<div class="card"><h2 data-zh="中文协议原文（全部组）">Chinese protocol (原文)</h2>
<details><summary data-zh='展开'>Expand</summary>
<pre>{esc(col.get('_intro',''))}</pre>
{''.join(f"<p style='font-size:13px'><b>{esc(p.get('title',''))}</b><br>{esc(p.get('criteria',''))}</p>" for p in col.get('pools', []))}
</details></div>"""
open(f"{OUT}/methods.html", "w", encoding="utf-8").write(page("Methods", b, "methods"))
print("methods ✓", flush=True)

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
<div class="card"><h2>Species tables TSV ({len(tsv_files)})</h2><table>{''.join(f"<tr><td>{esc(os.path.basename(f[0]))}</td><td>{f[1]/1024:.0f} KB</td></tr>" for f in tsv_files)}</table></div>"""
open(f"{OUT}/downloads.html", "w", encoding="utf-8").write(page("Downloads", b, "downloads"))
print("downloads ✓", flush=True)

# ================= API / schema page =================
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
<td>anchoring hits, BacDive-style measurements, source declarations, edit history</td><td>—</td></tr></table></div>
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
  WHERE salt_bridges_per_100 > 6 ORDER BY 3 DESC"</pre></div>
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
db.close()
total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
nfiles = sum(len(fs) for _, _, fs in os.walk(OUT))
print(f"SITE v2 DONE → {OUT}（{total/1e6:.0f} MB, {nfiles} files）")
