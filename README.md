# EnvTolDB — Environment-Tolerant Proteome Database

**A curated, provenance-tracked database of proteins from environment-tolerant organisms.**

[![Pages](https://img.shields.io/badge/GitHub%20Pages-Live-blue)](https://jialiangsun873-pixel.github.io/EnvtolDB/)
[![Release](https://img.shields.io/badge/Release-v3.3-green)](https://github.com/jialiangsun873-pixel/EnvtolDB/releases)

| | |
|---|---:|
| **Species** | **301** across 14 environmental dimensions |
| **Protein sequences** | **892,811** (UniProt, SHA-256 checksummed) |
| **Experimental measurements** | **681,685** (ddG / ΔTm / Tm / t½ / k_inact / pH & temp optima) |
| **AlphaFold structure records** | **150,319** (pLDDT / salt-bridge density; backfill for cold/pH/piezo/rad in progress) |
| **BRENDA enzyme parameters** | **137,038** (91,873 = 67% linked to UniProt accessions) |
| **Literature-derived records** | **4,939** (stability tables extracted from 7-dimension full-text mining) |

## What is EnvTolDB?

EnvTolDB collects and integrates protein sequences and experimental stability data from
organisms that thrive in extreme environments — thermophiles, halophiles, acidophiles,
alkaliphiles, solvent-tolerant bacteria, psychrophiles, piezophiles, radiation-resistant
organisms, metal-resistant strains, endolithic communities, xerophilic fungi,
arsenic-resistant bacteria, magnetotactic bacteria, and oligotrophic bacteria —
with mesophilic controls for comparison.

Every record is traceable:
- Sequences carry UniProt accessions (verifiable at uniprot.org) + SHA-256 checksums
- Experimental records carry DOI + source database + per-record condition details
- Literature anchoring status is recorded per species (Europe PMC co-occurrence; 176/301 species anchored)
- All edits are audit-logged with operator identity and timestamp

## Fourteen environmental dimensions

| Dimension | Species | Proteins | Structures | Experiments* |
|---|---:|---:|---:|---:|
| Thermophilic | 87 | 36,295 | 36,295 | 201 |
| Halophilic | 86 | 357,067 | 60,914 | 288 |
| Acid/Alkaliphilic | 26 | 76,342 | 69 | 190 |
| Solvent-tolerant | 14 | 99,627 | 48,912 | 783 |
| Cold-adapted | 29 | 117,277 | 0 † | 347 |
| Mesophilic control | 18 | 99,557 | 129 | 8,842 |
| Piezophilic | 5 | 10,354 | 0 † | 14 |
| Radiation-resistant | 6 | 12,073 | 4,000 † | 37 |
| Metal-resistant | 6 | 11,552 | 0 | 125 |
| Endolithic | 2 | 6 | 0 | 0 |
| Xerophilic | 4 | 738 | 0 | 914 |
| Arsenic-resistant | 7 | 32,312 | 0 | 139 |
| Magnetotactic | 5 | 23,304 | 0 | 0 |
| Oligotrophic | 6 | 16,307 | 0 | 50 |

\* Experiments attributable via UniProt accession linkage; totals across all sources are larger (see below).
† AlphaFold structures for cold/pH/piezo/rad pools are being backfilled (88,583 pre-verified models, ~90% coverage confirmed by sampling).

## Experimental layer by source

| Source | Records | Note |
|---|---:|---|
| FireProtDB | 533,071 | ddG / ΔTm mutations |
| BRENDA | 137,038 | pH/temp optimum, stability, range |
| ProThermDB | 2,921 | ΔTm (level-4 filter) |
| pH-Tm compilation | 1,883 | Curated pH-stability pairs |
| OrganiZymeDB | 1,833 | Solvent Tm for enzymes |
| Literature table extraction | 4,775 | Stability tables mined from OA full text across 7 dimensions (cold 347 / IL 1,014 / solvent 599 / piezo 1,283 / alkanotol 428 / endolithic 579 / rad 525) |
| DES literature (Radović 2024) | 164 | Deep eutectic solvent stability |

## Web interface

Visit the [live site](https://jialiangsun873-pixel.github.io/EnvtolDB/) for:
- Species browsing with sortable protein tables
- Per-solvent ΔTm aggregation with bar charts
- Collection protocol documentation (EN/中文)
- Bulk download: SQLite, per-species FASTA, per-pool TSV
- REST API (self-hosted instance) — [API docs](https://jialiangsun873-pixel.github.io/EnvtolDB/api.html)

## Repository structure

```
├── index.html                  # Dashboard (stats + 14 pool cards)
├── species/                    # 301 species pages + 14 pool index pages
├── solvents.html               # Per-solvent ΔTm aggregation
├── experiments.html            # Experimental layer overview
├── methods.html                # Collection protocols (EN/中文)
├── downloads.html              # Bulk download page
├── api.html                    # API documentation
├── downloads/                  # FASTA + TSV + CHECKSUMS
│   ├── fasta/                  #   289 species FASTA.gz
│   ├── tsv/                    #   pool TSV exports
│   └── CHECKSUMS.txt           #   SHA-256 of all downloads
└── .github/workflows/deploy.yml  # Auto-deploy on push
```

## Data sources

| Source | Records | Reference |
|---|---:|---|
| UniProtKB | 892,811 sequences | [uniprot.org](https://www.uniprot.org) |
| FireProtDB | 533,071 ddG | [Štourač et al., NAR 2021](https://doi.org/10.1093/nar/gkab799) |
| BRENDA | 137,038 enzyme parameters | [BRENDA](https://www.brenda-enzymes.org) |
| ProThermDB | 2,921 ΔTm | [Nikam et al., NAR 2021](https://doi.org/10.1093/nar/gkaa1070) |
| OrganiZymeDB | 1,833 solvent Tm | [Debruyne & Pucci, NAR 2026](https://doi.org/10.1093/nar/gkag1069) |
| Europe PMC | 135 full-text mining runs, 176 species anchored | [europepmc.org](https://europepmc.org) |
| BacDive | measured culture optima (27 species) | [Reimer et al., NAR 2022](https://doi.org/10.1093/nar/gkab799) |

## Changelog

- **v3.3 (2026-11-21)** — Round-3 expansion: arsenic (7 species), magnetotactic (5), oligotrophic (6) pools; BRENDA→UniProt accession linkage raised to 67%; strain-level taxid corrections
- **v3.2 (2026-11-21)** — metal/endolithic/xerophilic pools; EN-first UI v2
- **v3.1 (2026-11-20)** — piezo/rad pools; BRENDA integration; cold pool
- **v3.0 (2026-11-18)** — English-first UI, 8 dimension pools

## License

Code: MIT. Data: CC-BY 4.0 (with upstream source terms — see individual source databases).

## Citation

If you use EnvTolDB, please cite the EnvProGen manuscript (in preparation) and the
underlying sources listed above.
