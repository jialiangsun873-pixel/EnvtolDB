# EnvTolDB — Environment-Tolerant Proteome Database

环境耐受蛋白数据库 · A curated, queryable database of proteins from
environment-tolerant organisms (thermophilic, halophilic, acidophilic,
alkaliphilic, solvent-tolerant) with mesophilic controls.

[![Deploy](https://github.com/OWNER/REPO/actions/workflows/deploy.yml/badge.svg)](../../actions)

| Layer | Records |
|---|---:|
| Species (5 groups + controls) | 231 |
| UniProt protein sequences (SHA-256 checksummed) | 668,888 |
| Experimental measurements (ddG / ΔTm / Tm-vs-pH / solvent Tm) | 539,708 |
| AlphaFold structure records (pLDDT / salt-bridge density) | 146,319 |

## Site (GitHub Pages)

`site/` is the complete static site — enable **Settings → Pages → Deploy from
branch (main / root)** and it goes live. Contains: dashboard, 231 species pages
(full protein tables, FASTA downloads), solvent aggregation, experimental layer
summary, collection protocols, downloads (SQLite + TSV + FASTA).

## Rebuild from source database

```bash
python3 generator/build_static_site.py   # reads /public/home/sjl2/datasetdb/dataset.db
# adapt DB path at the top of the script, then commit the regenerated site/
```

## Bulk access

- `site/downloads/dataset.db.gz` — full SQLite (~250MB gz / ~500MB raw); query
  locally: `sqlite3 dataset.db "SELECT ..."` (schema in `site/api-docs.html`)
- `site/downloads/fasta/*.fasta.gz` — per-species FASTA
- `site/downloads/tsv/*.tsv` — per-pool species tables
- `site/downloads/CHECKSUMS.txt` — SHA-256 of every download

## Citation

EnvProGen manuscript (in preparation). Sources: UniProtKB, BacDive,
OrganiZymeDB (Debruyne & Pucci, NAR 2026), FireProtDB (Štourač et al., NAR 2021),
ProThermDB (Nikam et al., NAR 2021), Europe PMC.

## License

MIT (code & site); data released under CC-BY 4.0 with upstream source terms.
