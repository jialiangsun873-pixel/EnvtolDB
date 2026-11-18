#!/usr/bin/env python3
"""EnvTolDB 静态站生成器：dataset.db + config.json → site/（GitHub Pages 可直接部署）。

产出：
  index.html                 仪表盘
  species/<slug>.html ×231   物种页（含该物种全部蛋白表 + FASTA 下载）
  solvents.html              按溶剂聚合的 ΔTm 统计
  experiments.html           实验参数总览
  methods.html               采集方法（来自 config.json collection）
  api-docs.html              API 文档（镜像内网站点）
  downloads/                 每池物种 TSV / 每物种 FASTA.gz / dataset.db.gz
  .nojekyll                  GH Pages 关闭 Jekyll
  .github/workflows/deploy.yml  Pages 自动部署
"""
import csv, gzip, html, json, os, re, sqlite3, datetime
from collections import defaultdict
from statistics import median

DB = "/public/home/sjl2/datasetdb/dataset.db"
CFG = "/public/home/sjl2/datasetdb/config.json"
OUT = "/public/home/sjl2/envtoldb_site/site"
NOW = datetime.datetime.now().strftime("%Y-%m-%d")

cfg = json.load(open(CFG, encoding="utf-8"))
db = sqlite3.connect(DB, timeout=60)
db.row_factory = sqlite3.Row
db.execute("PRAGMA busy_timeout=60000")

POOLS = {p["key"]: p["label"] for p in cfg["pools"]}
os.makedirs(f"{OUT}/species", exist_ok=True)
os.makedirs(f"{OUT}/downloads/fasta", exist_ok=True)
os.makedirs(f"{OUT}/downloads/tsv", exist_ok=True)
os.makedirs(f"{OUT}/.github/workflows", exist_ok=True)
open(f"{OUT}/.nojekyll", "w").close()

def esc(s): return html.escape(str(s if s is not None else ""))
def slugify(name): return name.replace(" ", "_").replace("/", "_")

STYLE = """
body{font-family:-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',sans-serif;margin:0;background:#f5f8fc;color:#0c1726}
header{background:#f5f8fc;border-bottom:1px solid #dce5ef;padding:14px 28px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
header a{color:#48596e;text-decoration:none;margin-left:16px;font-size:14px}
header a:hover{color:#0c1726}
main{max-width:1160px;margin:0 auto;padding:22px 18px 60px}
h1{font-size:22px;margin:0 0 6px}h2{font-size:16px;color:#17324d}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 20px}
.kpi{flex:1;min-width:170px;background:#fff;border:1px solid #dce5ef;border-radius:6px;padding:14px 16px}
.kpi b{font-size:24px;display:block}
.kpi span{font-size:12px;color:#5f7086}
.card{background:#fff;border:1px solid #dce5ef;border-radius:6px;padding:16px 18px;margin-bottom:18px}
table{border-collapse:collapse;width:100%;font-size:13px}
th{background:#eef3f9;text-align:left;padding:6px 8px;border-bottom:1.5px solid #dce5ef}
td{padding:5px 8px;border-bottom:1px solid #e6eef7}
tr:hover td{background:#f0f6fc}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#e6eef7;color:#48596e}
.b-ok{background:#e4f4ee;color:#146a50}.b-no{background:#fdeef0;color:#c4424f}
.muted{color:#5f7086;font-size:12px}
input,select,button,textarea{font-size:13px;padding:4px 8px;border:1px solid #dce5ef;border-radius:4px;background:#fff;color:#0c1726;font-family:inherit}
textarea{width:100%;min-height:110px;font-family:monospace}
button{background:#0c1726;color:#fff;border:none;cursor:pointer}
pre{background:#eef3f9;padding:10px;border-radius:4px;font-size:12px;overflow:auto;max-height:340px}
code{font-family:ui-monospace,monospace;font-size:12px;background:#eef3f9;padding:1px 5px;border-radius:3px}
a{color:#1f6fd0}
footer{max-width:1160px;margin:20px auto;padding:0 18px;color:#5f7086;font-size:12px}
.note{background:#e4f4ee;border:1px solid #bfe3d6;color:#146a50;padding:8px 14px;border-radius:4px;margin-bottom:16px;font-size:13px}
"""

ANCH_OK = '<span class="badge b-ok">已锚定</span>'
ANCH_NO = '<span class="badge b-no">未锚定</span>'

def page(title, body, active=""):
    nav_items = [("index.html", "总览"), ("species/", "物种"), ("solvents.html", "溶剂统计"),
                 ("experiments.html", "实验参数"), ("methods.html", "采集方法"),
                 ("downloads.html", "下载"), ("api-docs.html", "API")]
    def _nav(h, t):
        style = ' style="font-weight:700;color:#0c1726"' if h == active else ""
        return f'<a href="{h}"{style}>{t}</a>'
    nav = "".join(_nav(h, t) for h, t in nav_items)
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · EnvTolDB</title><style>{STYLE}</style></head><body>
<header><div><b style="font-size:18px">EnvTolDB</b> <span class="muted">环境耐受蛋白数据库 · Environment-Tolerant Proteome Database</span></div>
<nav>{nav}</nav></header>
<main>{body}
<p class="muted" style="text-align:center">EnvTolDB · 每条序列带 UniProt accession 与 sha256 校验和 · 更新 {NOW}</p></main>
<footer>引用：EnvProGen 论文（撰写中）；数据来源 UniProtKB · BacDive · OrganiZymeDB · FireProtDB · ProThermDB · Europe PMC。</footer>
</body></html>"""

stats_all = {}
for k, sql in [
    ("species", "SELECT COUNT(*) FROM species"),
    ("proteins", "SELECT COUNT(*) FROM proteins"),
    ("structures", "SELECT COUNT(*) FROM structures"),
    ("experiments", "SELECT COUNT(*) FROM experiments"),
    ("verified", "SELECT COUNT(*) FROM proteins WHERE verified=1"),
]:
    stats_all[k] = db.execute(sql).fetchone()[0]

# ================= index =================
pool_cards = []
for p in cfg["pools"]:
    key = p["key"]
    n_sp, n_seq = db.execute("SELECT COUNT(*), COALESCE(SUM(n_seqs),0) FROM species WHERE pool=?", (key,)).fetchone()
    n_pr = db.execute("""SELECT COUNT(*) FROM proteins p JOIN species s ON s.id=p.species_id WHERE s.pool=?""", (key,)).fetchone()[0]
    n_st = db.execute("""SELECT COUNT(*) FROM structures st JOIN species s ON s.id=st_species_of(st.accession) WHERE 0""") if False else [None]
    n_st = db.execute("""SELECT COUNT(*) FROM structures st JOIN proteins p ON p.accession=st.accession
        JOIN species s ON s.id=p.species_id WHERE s.pool=?""", (key,)).fetchone()[0]
    pool_cards.append(f"""<div class="kpi"><b>{n_sp}</b><span>{esc(p['label'])} · {n_seq:,} 序列 ·
        入库蛋白 {n_pr:,} · 结构 {n_st:,}</span>
        <div style="margin-top:6px"><a href="species/{key}.html">浏览 {esc(p['label'])} 组 →</a></div></div>""")

per_pool_rows = "".join(
    f"<tr><td>{esc(p['key'])}</td><td>{esc(p['label'])}</td><td>{esc(p.get('description',''))}</td></tr>"
    for p in cfg["pools"])
idx_body = f"""<div class="note">{esc(cfg['site'].get('notice','').format(n_pools=len(cfg['pools']), n_species=stats_all['species'], n_proteins=stats_all['proteins']))}</div>
<div class="kpis">
<div class="kpi"><b>{stats_all['species']}</b><span>物种（5 个环境组 + 中温对照）</span></div>
<div class="kpi"><b>{stats_all['proteins']:,}</b><span>UniProt 蛋白序列（每条带 sha256）</span></div>
<div class="kpi"><b>{stats_all['experiments']:,}</b><span>实验测量（ddG / ΔTm / Tm-pH / 溶剂 Tm）</span></div>
<div class="kpi"><b>{stats_all['structures']:,}</b><span>AlphaFold 结构记录（pLDDT / 盐桥密度）</span></div>
</div>
<div class="card"><h2>环境组</h2><table><tr><th>key</th><th>名称</th><th>说明</th></tr>{per_pool_rows}</table></div>
<div class="card"><h2>如何使用本站</h2>
<p style="font-size:13px">① <a href="species/">按物种浏览</a>：每个物种页列出全部入库蛋白（含 pLDDT/盐桥）与 FASTA 下载；
② <a href="solvents.html">溶剂统计</a>：17 种有机溶剂的 ΔTm 聚合；
③ <a href="downloads.html">下载</a>：整库 SQLite、每池 TSV、每物种 FASTA；
④ 批量/程序化访问请下载 SQLite 后本地 SQL 查询（schema 见 <a href="api-docs.html">API 文档</a>页）。</p></div>
<div class="card"><h2>核验声明</h2><p style="font-size:13px">
每条序列可通过 accession 在 uniprot.org 打开官方条目比对；SHA-256 用于完整性校验；
人工核验记录（verified）必须附带核验证据；所有导入批次记录来源声明与时间。</p></div>
<div class="card"><h2>引用</h2><p style="font-size:13px">{esc(cfg['site'].get('citation',''))}</p></div>"""
open(f"{OUT}/index.html", "w", encoding="utf-8").write(page("总览", idx_body, "index.html"))
print("index.html ✓", flush=True)

# ================= 物种总览页（按池分组的四个列表页）=================
sp_by_pool = defaultdict(list)
for r in db.execute("SELECT * FROM species ORDER BY pool, name"):
    sp_by_pool[r["pool"]].append(dict(r))
for pool, items in sp_by_pool.items():
    trs = "".join(
        f"<tr><td><a href='{slugify(r['name'])}.html'>{esc(r['name'])}</a></td>"
        f"<td>{esc(r['grade'] or '—')}</td><td>{r['n_seqs'] or 0:,}</td>"
        f"<td>{ANCH_OK if r['lit_anchored'] else ANCH_NO}</td>"
        f"<td>{esc(r['evidence_level'] or '—')}</td></tr>" for r in items)
    b = f"""<div class="card"><h2>{esc(POOLS.get(pool, pool))}（{len(items)} 物种）</h2>
<table><tr><th>物种</th><th>分级</th><th>序列</th><th>文献锚定</th><th>证据等级</th></tr>{trs}</table></div>"""
    open(f"{OUT}/species/{pool}.html", "w", encoding="utf-8").write(page(f"{pool} 物种", b, "species"))
print("species index pages ✓", flush=True)

# ================= 每物种页 + FASTA =================
prot_cols = "p.accession, p.name, p.length, p.verified"
n_struct = db.execute("SELECT COUNT(*) FROM structures").fetchone()[0]
acc2struct = {}
if n_struct:
    for r in db.execute("""SELECT st.accession, st.mean_plddt, st.salt_bridges_per_100 FROM structures st"""):
        acc2struct[r["accession"]] = (r["mean_plddt"], r["salt_bridges_per_100"])
acc2expn = defaultdict(int)
for r in db.execute("SELECT accession, COUNT(*) c FROM experiments WHERE accession IS NOT NULL GROUP BY accession"):
    acc2expn[r["accession"]] = r["c"]

count = 0
for pool, items in sp_by_pool.items():
    for sp in items:
        slug = slugify(sp["name"])
        sid = sp["id"]
        prots = db.execute(f"SELECT {prot_cols} FROM proteins p WHERE p.species_id=? ORDER BY p.length DESC", (sid,)).fetchall()
        n_exp = db.execute("""SELECT COUNT(*) FROM experiments e JOIN proteins p ON p.accession=e.accession
            WHERE p.species_id=?""", (sid,)).fetchone()[0]
        trs = []
        fasta_rows = []
        for p in prots:
            st = acc2struct.get(p["accession"])
            st_txt = f"{st[0]:.1f}" if st else "—"
            exp_txt = str(acc2expn.get(p["accession"], 0))
            v = '<span class="badge b-ok">✓</span>' if p["verified"] else ""
            trs.append(f"<tr><td><code>{esc(p['accession'])}</code></td><td>{esc((p['name'] or '')[:60])}</td>"
                       f"<td>{p['length']}</td><td>{st_txt}</td><td>{exp_txt}</td><td>{v}</td></tr>")
            fasta_rows.append(f">{p['accession']} {p['name']}\n{db.execute('SELECT sequence FROM proteins WHERE accession=?', (p['accession'],)).fetchone()[0]}")
        gz_path = f"{OUT}/downloads/fasta/{slug}.fasta.gz"
        if not os.path.exists(gz_path):
            with gzip.open(gz_path, "wt") as f:
                for acc, name, seq in db.execute(
                    "SELECT accession, name, sequence FROM proteins WHERE species_id=? ORDER BY accession", (sid,)):
                    f.write(f">{acc} {name}\n{seq}\n")
        lit = '<span class="badge b-ok">已锚定</span>' if sp["lit_anchored"] else '<span class="badge b-no">未锚定</span>'
        prov = []
        if sp["proteome_id"]: prov.append(f"<a href='https://www.uniprot.org/proteomes/{esc(sp['proteome_id'])}' target='_blank' rel='noopener'>UniProt 蛋白组 {esc(sp['proteome_id'])}</a>")
        if sp["taxon_id"]: prov.append(f"<a href='https://www.ncbi.nlm.nih.gov/taxonomy/{esc(sp['taxon_id'])}' target='_blank' rel='noopener'>NCBI taxid {esc(sp['taxon_id'])}</a>")
        prov.append(f"<a href='https://europepmc.org/search?query=%22{slugify(sp['name'])}%22' target='_blank' rel='noopener'>Europe PMC 文献</a>")
        b = f"""<div class="card"><h2>{esc(sp['name'])}</h2>
<p style="font-size:13px">{esc(POOLS.get(sp['pool'], sp['pool']))} · 分级 {esc(sp['grade'] or '—')} ·
入库蛋白 <b>{len(prots):,}</b> · 实验记录 {n_exp} · {lit}
{('· BacDive ' + esc(sp['bacdive_value']) + ' ' + esc(sp['bacdive_unit'])) if sp['bacdive_value'] is not None else ''}</p>
<p class="muted">来源核验：{' · '.join(prov)} ·
<a href="../downloads/fasta/{slug}.fasta.gz">FASTA 下载 (.gz)</a></p>
<p class="muted">{esc(sp['evidence_note'] or '')} {esc(sp['notes'] or '')}</p></div>
<div class="card"><h2>蛋白列表（{len(prots):,} 条，按长度降序）</h2>
<input id="q" placeholder="页内过滤：accession / 名称…" onkeyup="flt()" style="width:280px;margin-bottom:8px">
<table id="t"><tr><th>accession</th><th>蛋白</th><th>长度</th><th>mean pLDDT</th><th>实验记录</th><th>核验</th></tr>
{''.join(trs)}</table>
<script>function flt(){{var q=document.getElementById('q').value.toLowerCase();var trs=document.getElementById('t').getElementsByTagName('tr');for(var i=1;i<trs.length;i++){{trs[i].style.display=trs[i].textContent.toLowerCase().indexOf(q)>-1?'':'none';}}}}</script></div>"""
        open(f"{OUT}/species/{slug}.html", "w", encoding="utf-8").write(page(sp["name"], b, "species"))
        count += 1
        if count % 20 == 0: print(f"  species {count}/231", flush=True)
print(f"species pages ✓ ({count})", flush=True)

# ================= 溶剂聚合页 =================
sol = defaultdict(list)
for r in db.execute("SELECT solvent, value FROM experiments WHERE kind='dTm_solvent' AND solvent != '' AND value IS NOT NULL"):
    sol[r["solvent"]].append(r["value"])
srows = "".join(f"<tr><td>{esc(s)}</td><td>{len(v)}</td><td><b>{median(v):+.1f}</b></td>"
                f"<td>{min(v):+.1f} ~ {max(v):+.1f}</td>"
                f"<td>{sum(1 for x in v if x < 0)}/{len(v)}</td></tr>"
                for s, v in sorted(sol.items(), key=lambda kv: median(kv[1])))
b = f"""<div class="ds-note note">有机溶剂对蛋白热稳定性的影响（OrganiZymeDB 实验测量；负值 = 去稳定）。
排序按 median ΔTm 升序。条件详情（浓度/pH/温度）与逐条记录请下载 SQLite 本地查询。</div>
<div class="card"><h2>按溶剂聚合（{len(sol)} 种溶剂）</h2><table>
<tr><th>溶剂</th><th>n</th><th>median ΔTm (°C)</th><th>范围</th><th>去稳定占比</th></tr>{srows}</table></div>"""
open(f"{OUT}/solvents.html", "w", encoding="utf-8").write(page("溶剂统计", b, "solvents"))

# ================= 实验参数总览页 =================
kinds = db.execute("SELECT kind, COUNT(*), SUM(accession IS NOT NULL), ROUND(AVG(value),1) FROM experiments GROUP BY kind ORDER BY 2 DESC").fetchall()
krows = "".join(f"<tr><td><span class='badge'>{esc(r[0])}</span></td><td>{r[1]:,}</td><td>{r[2] or 0:,}</td><td>{r[3]}</td></tr>" for r in kinds)
b = f"""<div class="note">实验参数层共 {stats_all['experiments']:,} 条。逐条检索（含条件/突变/来源）请下载 SQLite 本地查询；
本页为聚合视图。</div>
<div class="card"><h2>按类型</h2><table><tr><th>kind</th><th>条数</th><th>挂接 accession</th><th>均值</th></tr>{krows}</table>
<p class="muted">ddG 未挂接行保留 wt_sha256（FireProtDB 源野生型序列哈希），可回溯源文件核对；挂接率低反映该库以常温菌为主，非数据错误。</p></div>"""
open(f"{OUT}/experiments.html", "w", encoding="utf-8").write(page("实验参数", b, "experiments"))

# ================= 采集方法页 =================
col = cfg.get("collection", {})
cards = "".join(f"""<div class="card"><h2>{esc(p.get('title', p.get('pool','')))}</h2>
<p style="font-size:13px"><b>入选标准</b>：{esc(p.get('criteria',''))}</p>
<p style="font-size:13px"><b>文献锚定</b>：{esc(p.get('anchoring',''))}</p>
<p style="font-size:13px"><b>实验校准</b>：{esc(p.get('calibration',''))}</p></div>""" for p in col.get("pools", []))
b = f"""<div class="note">{esc(col.get('_intro',''))}</div>{cards}"""
open(f"{OUT}/methods.html", "w", encoding="utf-8").write(page("采集方法", b, "methods"))

# ================= API 文档镜像页 =================
b = f"""<div class="card"><h2>API（自托管实例）</h2>
<p style="font-size:13px">完整 REST API 随自托管实例提供（登录后 <code>/dataset/api</code> 查看）。
本 GitHub Pages 镜像为静态只读版：提供浏览、聚合与下载；程序化检索请下载数据文件本地查询。</p></div>
<div class="card"><h2>本地查询示例（下载 SQLite 后）</h2>
<pre>sqlite3 dataset.db "SELECT kind, COUNT(*) FROM experiments GROUP BY kind"
sqlite3 dataset.db "SELECT accession, mean_plddt, salt_bridges_per_100 FROM structures
                    WHERE salt_bridges_per_100 > 6 ORDER BY 3 DESC LIMIT 20"</pre></div>
<div class="card"><h2>数据字典</h2><table><tr><th>字段</th><th>说明</th></tr>
{''.join(f"<tr><td><code>{esc(d['field'])}</code></td><td>{esc(d['meaning'])}</td></tr>" for d in cfg.get('data_dictionary', []))}</table></div>
<div class="card"><h2>引用</h2><p style="font-size:13px">{esc(cfg['site'].get('citation',''))}</p></div>"""
open(f"{OUT}/api-docs.html", "w", encoding="utf-8").write(page("API", b, "api"))

# ================= 下载页 + TSV 导出 =================
for pool in POOLS:
    rows = db.execute("SELECT * FROM species WHERE pool=? ORDER BY name", (pool,)).fetchall()
    cols = ["name","taxon_id","pool","subgroup","grade","proteome_id","n_seqs","lit_anchored",
            "evidence_level","bacdive_value","bacdive_unit","notes"]
    with open(f"{OUT}/downloads/tsv/species_{pool}.tsv", "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r[c] is None else str(r[c]) for c in cols])
print("tsv exports ✓", flush=True)

db_dz = f"{OUT}/downloads/dataset.db.gz"
if not os.path.exists(db_dz):
    src = open("/public/home/sjl2/datasetdb/dataset.db", "rb")
    with gzip.open(db_dz, "wb", compresslevel=6) as f:
        for chunk in iter(lambda: src.read(1 << 22), b""):
            f.write(chunk)
    src.close()
sz_db = os.path.getsize(db_dz) / 1e6
sz_fa = sum(os.path.getsize(f"{OUT}/downloads/fasta/{f}") for f in os.listdir(f"{OUT}/downloads/fasta")) / 1e6
dl_rows = "".join(
    f"<tr><td>每池物种表 TSV</td><td><a href='tsv/species_{p}.tsv'>species_{p}.tsv</a></td><td>{esc(POOLS[p])}</td></tr>" for p in POOLS)
b = f"""<div class="card"><h2>数据下载</h2>
<table><tr><th>内容</th><th>文件</th><th>说明</th></tr>
<tr><td>整库 SQLite（含全部序列）</td><td><a href="dataset.db.gz">dataset.db.gz</a>（{sz_db:.0f} MB，解压后 ~500MB）</td><td>推荐：本地 sqlite3 直接 SQL 查询</td></tr>
<tr><td>每物种 FASTA</td><td>downloads/fasta/&lt;物种&gt;.fasta.gz（合计 {sz_fa:.0f} MB）</td><td>231 个文件，各物种页也有直链</td></tr>
{dl_rows}
</table>
<p class="muted">SHA-256 校验：见 repo 内 CHECKSUMS 文件。序列变更后整库重新发布并更新校验。</p></div>"""
open(f"{OUT}/downloads.html", "w", encoding="utf-8").write(page("下载", b, "downloads"))

# CHECKSUMS
import hashlib
lines = []
for root, _, fs in os.walk(f"{OUT}/downloads"):
    for f in sorted(fs):
        fp = os.path.join(root, f)
        h = hashlib.sha256()
        with open(fp, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        lines.append(f"{h.hexdigest()}  {os.path.relpath(fp, OUT)}")
open(f"{OUT}/downloads/CHECKSUMS.txt", "w").write("\n".join(lines) + "\n")
print("downloads + CHECKSUMS ✓", flush=True)

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
print(f"SITE DONE → {OUT}（{total/1e6:.0f} MB, {sum(len(fs) for _,_,fs in os.walk(OUT))} 文件）")
