# EnvTolDB — Environment-Tolerant Proteome Database

**A curated, provenance-tracked database of proteins from environment-tolerant organisms.**

[![Pages](https://img.shields.io/badge/GitHub%20Pages-Live-blue)](https://jialiangsun873-pixel.github.io/EnvtolDB/)
[![Release](https://img.shields.io/badge/Release-v3.2-green)](https://github.com/jialiangsun873-pixel/EnvtolDB/releases/tag/v3.1)

| | |
|---|---:|
| **Species** | **271** across 8 environmental dimensions |
| **Protein sequences** | **808,592** (UniProt, SHA-256 checksummed) |
| **Experimental measurements** | **681,685** (ddG / ΔTm / Tm / t½ / k_inact, from 6 sources) |
| **AlphaFold structure records** | **146,319** (pLDDT / salt-bridge density) |
| **BRENDA enzyme parameters** | **137,038** (pH/temp optimum, stability, range) |
| **BacDive strain phenotypes** | **4,047** (OGT / salinity / isolation source) |

## What is EnvTolDB?

EnvTolDB collects and integrates protein sequences and experimental stability data from
organisms that thrive in extreme environments — thermophiles, halophiles, acidophiles,
alkaliphiles, solvent-tolerant bacteria, psychrophiles, piezophiles, and
radiation-resistant organisms — with mesophilic controls for comparison.

Every record is traceable:
- Sequences carry UniProt accessions (verifiable at uniprot.org) + SHA-256 checksums
- Experimental records carry DOI + source database + per-record condition details
- Literature anchoring status is recorded per species (Europe PMC co-occurrence)
- All edits are audit-logged with operator identity and timestamp

## Eight environmental dimensions

| Dimension | Species | Proteins | Structures | Experiments |
|---|---:|---:|---:|---:|
| Thermophilic | 87 | 36,295 | 36,295 | 2 |
| Halophilic | 86 | 357,067 | 60,914 | 185 |
| Acid/Alkaliphilic | 26 | 76,342 | 69 | 177 |
| Solvent-tolerant | 14 | 99,627 | 48,912 | 190 |
| Cold-adapted | 29 | 117,277 | 0 | 347 |
| Mesophilic control | 18 | 99,557 | 129 | 2,080 |
| Piezophilic | 5 | 10,354 | 0 | 0 |
| Radiation-resistant | 6 | 12,073 | 0 | 0 |

## Web interface

Visit the [live site](https://jialiangsun873-pixel.github.io/EnvtolDB/) for:
- Species browsing with sortable protein tables
- Per-solvent ΔTm aggregation with bar charts
- Collection protocol documentation (EN/中文)
- Bulk download: SQLite, per-species FASTA, per-pool TSV
- REST API (self-hosted instance) — [API docs](https://jialiangsun873-pixel.github.io/EnvtolDB/api.html)

## Repository structure

```
├── index.html                  # Dashboard (stats + pool cards)
├── species/                    # 271 species pages + pool index pages
├── solvents.html               # Per-solvent ΔTm aggregation
├── experiments.html            # Experimental layer overview
├── methods.html                # Collection protocols (EN/中文)
├── downloads.html              # Bulk download page
├── api.html                    # API documentation
├── downloads/                  # FASTA + TSV + CHECKSUMS
│   ├── fasta/                  #   260 species FASTA.gz
│   ├── tsv/                    #   5 pool TSV exports
│   └── CHECKSUMS.txt           #   SHA-256 of all downloads
└── .github/workflows/deploy.yml  # Auto-deploy on push
```

## Data sources

| Source | Records | Reference |
|---|---:|---|
| UniProtKB | 786,165 sequences | [uniprot.org](https://www.uniprot.org) |
| FireProtDB | 533,071 ddG | [Štourač et al., NAR 2021](https://doi.org/10.1093/nar/gkab799) |
| BRENDA | 137,038 enzyme parameters | [BRENDA](https://www.brenda-enzymes.org) |
| ProThermDB | 2,921 ΔTm | [Nikam et al., NAR 2021](https://doi.org/10.1093/nar/gkaa1070) |
| OrganiZymeDB | 1,833 solvent Tm | [Debruyne & Pucci, NAR 2026](https://doi.org/10.1093/nar/gkag1069) |
| BacDive | 4,047 strains | [Reimer et al., NAR 2022](https://doi.org/10.1093/nar/gkab799) |
| Europe PMC | 135 anchoring records | [europepmc.org](https://europepmc.org) |

## License

Code: MIT. Data: CC-BY 4.0 (with upstream source terms — see individual source databases).

## Citation

If you use EnvTolDB, please cite the EnvProGen manuscript (in preparation) and the
underlying sources listed above.
