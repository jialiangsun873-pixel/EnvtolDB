#!/usr/bin/env python3
import argparse
import csv
import html
import json
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

BUILD_DATE = "2026-11-26"
EVIDENCE = {
    "native_protein_evidence": ("Native protein evidence", "蛋白本体证据", "Sequence/protein-level characterization in the source organism; not automatically a recombinant assay."),
    "reviewed_annotation": ("Reviewed annotation", "已审核注释", "Swiss-Prot reviewed entry; review status is separate from the activity assay type."),
    "direct_recombinant_activity": ("Direct recombinant activity", "重组蛋白直接活性", "A recombinant protein or defined recombinant construct was tested for ice-related activity."),
    "primary_literature_function": ("Primary literature function", "原始文献功能", "Function/structural role is supported by a primary paper; assay details remain paper-specific."),
    "transcript_prediction": ("Transcript / homology prediction", "转录/同源预测", "Transcript-level or homology-based candidate; no direct activity is asserted."),
    "database_annotation_only": ("Database annotation only", "仅数据库注释", "Genome/domain/rule-based annotation only; no direct activity is asserted."),
    "related_not_afp": ("Related stress protein, not AFP/IBP", "相关胁迫蛋白，非 AFP/IBP", "Kept as an exclusion decision, not counted as an AFP/IBP protein."),
    "search_audit": ("Search audit", "检索审计", "Documents an exclusion or evidence gap; not a positive AFP/IBP record."),
}
STATUS = {
    "included": ("Included", "纳入"),
    "species_only_prediction": ("Species-level prediction only", "仅物种级预测"),
    "quarantined": ("Quarantined", "隔离"),
    "excluded_insufficient_evidence": ("Excluded: insufficient evidence", "排除：证据不足"),
    "related_not_afp": ("Related, not AFP/IBP", "相关但非 AFP/IBP"),
}
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


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def safe_url(v):
    return v if isinstance(v, str) and v.startswith("https://") else ""


def slug(v):
    return v.replace(" ", "_").replace("/", "_")


def page(title, body, active="index", sub=False):
    afp_pre = "../" if sub else ""
    root_pre = "../../" if sub else "../"
    nav = [("index.html", "Overview", "index"), ("species/index.html", "Species & decisions", "species"),
           ("methods.html", "Evidence guide", "methods")]
    links = "".join(f'<a href="{afp_pre}{h}" class="{"on" if k==active else ""}">{t}</a>' for h,t,k in nav)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#f5f5f7"><title>{esc(title)} · EnvTolDB AFP/IBP</title><style>{CSS}</style></head><body>
<header><a class="brand" href="{afp_pre}index.html"><span>EnvTolDB <small>Independent AFP / IBP subset</small></span></a><nav>{links}</nav><a href="{root_pre}index.html">Main database ↗</a></header>
<main>{body}</main><footer>EnvTolDB AFP/IBP subset · curated {BUILD_DATE} · independent of the 14 core environmental pools · sequences and evidence remain traceable to UniProt/NCBI and primary literature.</footer>
<script>{JS}</script></body></html>"""


JS = """
function filterRows(input){const q=input.value.toLowerCase();input.closest('.card').querySelectorAll('[data-filter-row]').forEach(r=>r.style.display=r.textContent.toLowerCase().includes(q)?'':'none')}
function sortTable(th){const table=th.closest('table'),idx=Array.from(th.parentNode.children).indexOf(th),body=table.querySelector('tbody')||table,dir=th.dataset.dir==='asc'?-1:1;th.dataset.dir=dir===1?'asc':'desc';const rows=Array.from(body.querySelectorAll('tr')).filter(r=>!r.querySelector('th'));rows.sort((a,b)=>{const A=a.children[idx]?.textContent||'',B=b.children[idx]?.textContent||'';const na=parseFloat(A.replace(/,/g,'')),nb=parseFloat(B.replace(/,/g,''));return ((!isNaN(na)&&!isNaN(nb))?na-nb:A.localeCompare(B))*dir});rows.forEach(r=>body.appendChild(r))}
"""


def load(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    present = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='afp_ibp_proteins'").fetchone()[0]
    if not present:
        con.close()
        return None
    species = [dict(r) for r in con.execute("SELECT * FROM afp_ibp_species ORDER BY inclusion_status, scientific_name")]
    proteins = [dict(r) for r in con.execute("SELECT p.*,s.species_key,s.scientific_name,s.taxon_id,s.common_name,s.clade_group,s.inclusion_status,s.decision_note FROM afp_ibp_proteins p JOIN afp_ibp_species s ON s.id=p.species_id ORDER BY s.scientific_name,p.accession")]
    evidence = [dict(r) for r in con.execute("SELECT e.*,s.species_key,p.accession FROM afp_ibp_evidence e JOIN afp_ibp_species s ON s.id=e.species_id LEFT JOIN afp_ibp_proteins p ON p.id=e.protein_id ORDER BY e.id")]
    quarantine = [dict(r) for r in con.execute("SELECT * FROM afp_ibp_quarantine ORDER BY accession")]
    core = {}
    for r in con.execute("SELECT p.accession,s.name FROM proteins p JOIN species s ON s.id=p.species_id"):
        core[r["accession"]] = r["name"]
    con.close()
    return dict(species=species, proteins=proteins, evidence=evidence, quarantine=quarantine, core=core)


def evidence_badge(cls):
    label = EVIDENCE.get(cls, (cls, cls, ""))[0]
    warn = cls in {"transcript_prediction", "database_annotation_only", "search_audit"}
    bad = cls == "related_not_afp"
    return f'<span class="badge {"warn" if warn else "bad" if bad else "ok"}">{esc(label)}</span>'


def status_badge(status):
    label = STATUS.get(status, (status, status))[0]
    cls = "ok" if status == "included" else "bad" if status in {"quarantined", "excluded_insufficient_evidence"} else "warn"
    return f'<span class="badge {cls}">{esc(label)}</span>'


def ref_link(e):
    bits = []
    if e.get("pmid"):
        bits.append(f'<a href="https://europepmc.org/abstract/MED/{esc(e["pmid"])}" target="_blank" rel="noopener">PMID {esc(e["pmid"])}</a>')
    if e.get("pmcid"):
        bits.append(f'<a href="https://europepmc.org/articles/{esc(e["pmcid"])}" target="_blank" rel="noopener">{esc(e["pmcid"])}</a>')
    if e.get("doi"):
        bits.append(f'<a href="https://doi.org/{esc(e["doi"])}" target="_blank" rel="noopener">DOI {esc(e["doi"])}</a>')
    u = safe_url(e.get("url"))
    if u and not bits:
        bits.append(f'<a href="{esc(u)}" target="_blank" rel="noopener">source</a>')
    return " · ".join(bits)


def protein_row(p, prefix=""):
    return (f'<tr data-filter-row><td><a href="{prefix}protein/{esc(p["accession"])}.html"><code>{esc(p["accession"])}</code></a></td>'
            f'<td><a href="{prefix}species/{esc(p["species_key"])}.html">{esc(p["scientific_name"])}</a></td>'
            f'<td>{esc(p["protein_family"])}</td><td>{evidence_badge(p["evidence_class"])}</td>'
            f'<td>{p["length"]}</td><td>{"yes" if p["uniprot_reviewed"] else "no"}</td></tr>')


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def build_index(out, data):
    ps = data["proteins"]
    sp = data["species"]
    counts = Counter(p["evidence_class"] for p in ps)
    metazoa = sum(1 for p in ps if p["clade_group"] != "microbial_reference")
    included_species = sum(1 for s in sp if s["inclusion_status"] == "included")
    rows = "".join(protein_row(p) for p in ps)
    sp_rows = "".join(f'<tr data-filter-row><td><a href="species/{esc(s["species_key"])}.html">{esc(s["scientific_name"])}</a></td>'
                      f'<td>{esc(s["clade_group"])}</td><td>{status_badge(s["inclusion_status"])}</td><td>{esc(s["decision_note"])}</td></tr>' for s in sp)
    q_rows = "".join(f'<tr><td><code>{esc(q["accession"])}</code></td><td>{esc(q["issue_code"])}</td><td>{esc(q["reason"])}</td>'
                     f'<td><a href="{esc(safe_url(q["source_url"]))}" target="_blank" rel="noopener">source</a></td></tr>' for q in data["quarantine"])
    body = f"""<div class="hero"><h1>Antifreeze / ice-binding proteins</h1>
<p>A conservative, provenance-tracked subset of metazoan AFP/IBP records with microbial references. It is intentionally separate from the 14 core environmental pools: core species membership, protein counts, clustering balance and growth-condition records are unchanged.</p>
<div class="chips"><div class="chip"><b>{included_species}</b><span>included taxa</span></div><div class="chip"><b>{len(ps)}</b><span>accession-level records</span></div><div class="chip"><b>{metazoa}</b><span>metazoan records</span></div><div class="chip"><b>{len(data["evidence"])}</b><span>evidence rows</span></div></div></div>
<div class="note"><b>Evidence is graded, not binary.</b> Recombinant activity, native protein characterization, primary-literature function, transcript/homology prediction and database-only annotation are displayed separately. A cold habitat or an AFP keyword hit alone is not sufficient for inclusion.</div>
<div class="card"><h2>Protein functions &amp; evidence</h2><input placeholder="Filter by accession, species, family or evidence…" oninput="filterRows(this)"><p class="muted">Open a protein for its function, evidence class, limitations, sequence and literature links.</p>
<table><thead><tr><th onclick="sortTable(this)">Accession</th><th onclick="sortTable(this)">Species</th><th onclick="sortTable(this)">Family</th><th onclick="sortTable(this)">Evidence</th><th onclick="sortTable(this)">Length</th><th onclick="sortTable(this)">Reviewed</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="card"><h2>Species-level review decisions</h2><input placeholder="Filter species or decision…" oninput="filterRows(this)"><table><thead><tr><th onclick="sortTable(this)">Species</th><th>Group</th><th>Status</th><th>Decision</th></tr></thead><tbody>{sp_rows}</tbody></table></div>
<div class="card"><h2>Quarantined records</h2><p class="muted">These records are not counted or served as AFP/IBP proteins.</p><table><tr><th>Accession</th><th>Issue</th><th>Reason</th><th>Source</th></tr>{q_rows}</table></div>
<div class="card"><h2>Downloads</h2><p><a href="downloads/afp_ibp_proteins.fasta" download>Protein FASTA</a> · <a href="downloads/afp_ibp_proteins.tsv" download>Protein TSV</a> · <a href="downloads/afp_ibp.json" download>Complete subset JSON</a></p></div>"""
    (out / "index.html").write_text(page("AFP / IBP overview", body), encoding="utf-8")


def build_species_index(out, data):
    rows = "".join(f'<tr data-filter-row><td><a href="{esc(s["species_key"])}.html">{esc(s["scientific_name"])}</a></td>'
                   f'<td>{esc(s["taxon_id"] or "—")}</td><td>{esc(s["clade_group"])}</td><td>{status_badge(s["inclusion_status"])}</td>'
                   f'<td>{esc(s["decision_note"])}</td></tr>' for s in data["species"])
    body = f'<div class="card"><h2>Taxa and review decisions ({len(data["species"])})</h2><input placeholder="Filter species…" oninput="filterRows(this)"><table><thead><tr><th>Species</th><th>NCBI taxid</th><th>Group</th><th>Status</th><th>Decision</th></tr></thead><tbody>{rows}</tbody></table></div>'
    (out / "species").mkdir(parents=True, exist_ok=True)
    (out / "species" / "index.html").write_text(page("AFP species & decisions", body, "species", sub=True), encoding="utf-8")


def build_species(out, data):
    by_sp = defaultdict(list)
    by_ev = defaultdict(list)
    for p in data["proteins"]:
        by_sp[p["species_key"]].append(p)
    for e in data["evidence"]:
        by_ev[e["species_key"]].append(e)
    for s in data["species"]:
        prots = by_sp[s["species_key"]]
        evs = by_ev[s["species_key"]]
        rows = "".join(protein_row(p, "../") for p in prots) or '<tr><td colspan="6" class="muted">No accession-level AFP/IBP protein imported for this taxon.</td></tr>'
        ev_rows = "".join(f'<tr><td>{esc(e["evidence_role"])}</td><td>{evidence_badge(e["evidence_class"])}</td><td>{esc(e["statement"])}</td><td>{ref_link(e)}</td></tr>' for e in evs)
        tax_link = f'<a href="https://www.ncbi.nlm.nih.gov/taxonomy/{s["taxon_id"]}" target="_blank" rel="noopener">NCBI txid{s["taxon_id"]}</a>' if s["taxon_id"] else ""
        prot_link = f' · <a href="https://www.uniprot.org/proteomes/{esc(s["proteome_id"])}" target="_blank" rel="noopener">UniProt proteome</a>' if s["proteome_id"] else ""
        body = f"""<div class="card"><h1>{esc(s['scientific_name'])}</h1><p>{status_badge(s['inclusion_status'])} · {esc(s['clade_group'])} · {esc(s['habitat'])}</p>
<dl class="kv"><dt>Decision</dt><dd>{esc(s['decision_note'])}</dd><dt>Identity links</dt><dd>{tax_link}{prot_link}</dd></dl></div>
<div class="card"><h2>Proteins ({len(prots)})</h2><table><thead><tr><th>Accession</th><th>Species</th><th>Family</th><th>Evidence</th><th>Length</th><th>Reviewed</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="card"><h2>Evidence &amp; review trail</h2><table><tr><th>Role</th><th>Evidence class</th><th>Statement</th><th>Source</th></tr>{ev_rows}</table></div>"""
        (out / "species" / f'{s["species_key"]}.html').write_text(page(s["scientific_name"], body, "species", sub=True), encoding="utf-8")


def build_proteins(out, data):
    by_acc = defaultdict(list)
    for e in data["evidence"]:
        if e["accession"]:
            by_acc[e["accession"]].append(e)
    for p in data["proteins"]:
        evs = by_acc[p["accession"]]
        ev_rows = "".join(f'<tr><td>{esc(e["evidence_role"])}</td><td>{evidence_badge(e["evidence_class"])}</td><td>{esc(e["statement"])}</td><td>{esc(e["title"] or e["source_accession"] or "source record")}<br>{ref_link(e)}</td></tr>' for e in evs)
        core_name = data["core"].get(p["accession"])
        core_link = ""
        if core_name:
            core_link = f'<p class="note">This accession also exists in the core database as <a href="../../protein/view.html?acc={esc(p["accession"])}&amp;sp={esc(slug(core_name))}">core protein {esc(p["accession"])}</a>. The AFP function card supplements, but does not alter, that core record.</p>'
        ids = [x.strip() for x in p["structure_ids"].split(";") if x.strip()]
        struct = " · ".join(f'<a href="https://www.rcsb.org/structure/{esc(x)}" target="_blank" rel="noopener">PDB {esc(x)}</a>' for x in ids)
        nuc = ""
        if p["source_nucleotide_accession"]:
            nuc = f'<dt>Nucleotide source</dt><dd><a href="{esc(safe_url(p["ncbi_url"]))}" target="_blank" rel="noopener">{esc(p["source_nucleotide_version"])}</a> → protein <code>{esc(p["accession"])}</code></dd>'
        identity = []
        if p["uniprot_url"]:
            identity.append(f'<a href="{esc(safe_url(p["uniprot_url"]))}" target="_blank" rel="noopener">UniProt</a>')
        if p["ncbi_url"]:
            identity.append(f'<a href="{esc(safe_url(p["ncbi_url"]))}" target="_blank" rel="noopener">NCBI protein</a>')
        body = f"""<div class="card"><h1>{esc(p['accession'])} — {esc(p['protein_name'])}</h1><p><a href="../species/{esc(p['species_key'])}.html">{esc(p['scientific_name'])}</a> · {esc(p['protein_family'])} · {p['length']} aa · UniProt reviewed: <b>{'yes' if p['uniprot_reviewed'] else 'no'}</b></p>
<p>{evidence_badge(p['evidence_class'])} <span class="muted">{esc(EVIDENCE[p['evidence_class']][2])}</span></p>{core_link}</div>
<div class="grid"><div class="card"><h2>Function</h2><p>{esc(p['function_description'])}</p><h3>Activity summary</h3><p>{esc(p['activity_summary'])}</p></div>
<div class="card"><h2>Evidence boundaries</h2><dl class="kv"><dt>Activity type</dt><dd>{esc(p['activity_type'])}</dd><dt>Protein existence</dt><dd>{esc(p['protein_existence'])}</dd><dt>Gene</dt><dd>{esc(p['gene_name'] or '—')}</dd><dt>Structures</dt><dd>{struct or '—'}</dd>{nuc}<dt>Identity</dt><dd>{' · '.join(identity)}</dd></dl>
<div class="warnbox"><b>Limitations:</b> {esc(p['limitations'] or 'No additional limitation recorded; see the linked source for assay conditions.')}</div></div></div>
<div class="card"><h2>Sequence</h2><p class="muted">SHA-256 <code>{esc(p['seq_sha256'])}</code></p><pre class="seq">{esc(p['sequence'])}</pre></div>
<div class="card"><h2>Sources &amp; evidence</h2><table><tr><th>Role</th><th>Evidence</th><th>Statement</th><th>Source</th></tr>{ev_rows}</table></div>"""
        (out / "protein").mkdir(parents=True, exist_ok=True)
        (out / "protein" / f'{p["accession"]}.html').write_text(page(p["accession"], body, sub=True), encoding="utf-8")


def build_methods(out, data):
    rows = "".join(f'<tr><td>{evidence_badge(k)}</td><td>{esc(v[2])}</td></tr>' for k,v in EVIDENCE.items())
    body = f"""<div class="card"><h1>How to read AFP/IBP evidence</h1><p>Antifreeze proteins (AFPs) and ice-binding proteins (IBPs) are functionally diverse. This subset records what the source actually supports and keeps predictions visibly separate from activity measurements.</p>
<table><tr><th>Evidence class</th><th>Interpretation</th></tr>{rows}</table></div>
<div class="card"><h2>Inclusion and exclusion rules</h2><ol><li>Import accession-level sequences only when identity, organism and sequence hash can be checked.</li><li>Keep nucleotide accessions separate from protein accessions: PP898178.1 is the Antarctic <i>Adineta</i> contig; XBW52365.1 is its CDS translation.</li><li>Do not infer native AFP activity from a protein hydrolysate, a cold habitat, a generic stress protein or a keyword hit.</li><li>Quarantine species conflicts and obvious keyword false positives.</li><li>Do not add these taxa to the 14 core pools; analyze this subset independently.</li></ol></div>
<div class="card"><h2>Provenance</h2><p>Sequences: UniProtKB or NCBI GenBank. Literature: PubMed/Europe PMC records with DOI/PMID links. Every imported sequence carries a SHA-256 checksum. The SQLite importer validates the seed, records an audit batch, and compares a fingerprint of every non-AFP core table before and after the transaction.</p></div>"""
    (out / "methods.html").write_text(page("AFP evidence guide", body, "methods"), encoding="utf-8")


def build_downloads(out, data):
    d = out / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    with (d / "afp_ibp_proteins.fasta").open("w", encoding="utf-8") as f:
        for p in data["proteins"]:
            f.write(f'>{p["accession"]} {p["scientific_name"]} {p["protein_name"]}\n')
            for i in range(0, len(p["sequence"]), 60):
                f.write(p["sequence"][i:i+60] + "\n")
    fields = ["accession","scientific_name","taxon_id","protein_name","gene_name","protein_family","length","seq_sha256",
              "uniprot_reviewed","protein_existence","evidence_class","activity_type","activity_summary","function_description",
              "limitations","source_nucleotide_accession","source_db","source_release","uniprot_url","ncbi_url","structure_ids"]
    with (d / "afp_ibp_proteins.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for p in data["proteins"]:
            w.writerow(p)
    write_json(d / "afp_ibp.json", {k: data[k] for k in ("species","proteins","evidence","quarantine")})
    write_json(out / "data" / "species.json", data["species"])
    write_json(out / "data" / "proteins.json", data["proteins"])
    write_json(out / "data" / "evidence.json", data["evidence"])


def build_site(db_path, site_root):
    data = load(db_path)
    if data is None:
        return None
    out = Path(site_root) / "afp"
    out.mkdir(parents=True, exist_ok=True)
    build_index(out, data)
    build_species_index(out, data)
    build_species(out, data)
    build_proteins(out, data)
    build_methods(out, data)
    build_downloads(out, data)
    return dict(output=str(out), species=len(data["species"]), proteins=len(data["proteins"]),
                evidence=len(data["evidence"]), quarantine=len(data["quarantine"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/public/home/sjl2/datasetdb/dataset.db")
    ap.add_argument("--out", default="/public/home/sjl2/envtoldb_site")
    args = ap.parse_args()
    result = build_site(args.db, args.out)
    print(json.dumps(result or {"status": "AFP/IBP tables not present; nothing generated"}, indent=2))


if __name__ == "__main__":
    main()
