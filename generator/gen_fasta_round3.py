#!/usr/bin/env python3
"""为轮3三新池 18 物种生成 downloads/fasta/{slug}.fasta.gz。"""
import gzip, os, sqlite3
DB = "/public/home/sjl2/datasetdb/dataset.db"
OUT = "/public/home/sjl2/envtoldb_site"
db = sqlite3.connect(DB)
pools = ("arsenic","magnetotactic","oligotrophic")
rows = db.execute(f"SELECT id, name FROM species WHERE pool IN {pools}").fetchall()
n = 0
for sid, name in rows:
    slug = name.replace(" ", "_").replace("/", "_")
    fp = f"{OUT}/downloads/fasta/{slug}.fasta.gz"
    if os.path.exists(fp):
        print("[skip] exists:", slug); continue
    buf = []
    for acc, pname, seq in db.execute("SELECT accession, name, sequence FROM proteins WHERE species_id=? ORDER BY accession", (sid,)):
        buf.append(f">{acc} {pname or ''}\n{seq}")
    with gzip.open(fp, "wt") as f:
        f.write("\n".join(buf) + "\n")
    print(f"[ok] {slug}: {len(buf):,} seqs, {os.path.getsize(fp)/1e6:.1f} MB")
    n += 1
print(f"生成 {n} 个 FASTA")
db.close()
