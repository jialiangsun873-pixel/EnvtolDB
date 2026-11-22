# EnvTolDB — Environment-Tolerant Proteome Database

**A curated, provenance-tracked database of proteins from environment-tolerant organisms.**

[![Pages](https://img.shields.io/badge/GitHub%20Pages-Live-blue)](https://jialiangsun873-pixel.github.io/EnvtolDB/)
[![Release](https://img.shields.io/badge/Release-v3.4-green)](https://github.com/jialiangsun873-pixel/EnvtolDB/releases)

| | |
|---|---:|
| **Species** | **301** across 14 environmental dimensions |
| **Protein sequences** | **892,811** (UniProt, SHA-256 checksummed) |
| **Experimental measurements** | **964,946** (ddG / ΔTm / Tm / t½ / pH & temp optima / kinetics / in-cell melt temps) |
| **CLEAN EC annotations** | **2,438,069** (AI-predicted EC numbers, 4,941 unique EC, 52% at confidence ≥0.9) |
| **AlphaFold structure records** | **233,922** (pLDDT / salt-bridge density; all four new pools backfilled) |
| **BRENDA enzyme parameters** | **212,538** (stability + Km / kcat / Ki / IC50 / specific activity; 67% linked) |
| **Identity annotations** | **1,320** (metal-ion dependence / inhibitors / oxygen sensitivity) |

## What is EnvTolDB?

EnvTolDB collects and integrates protein sequences, gene-protein-EC linkages and experimental
stability data from organisms that thrive in extreme environments — thermophiles, halophiles,
acidophiles, alkaliphiles, solvent-tolerant bacteria, psychrophiles, piezophiles,
radiation-resistant organisms, metal-resistant strains, endolithic communities, xerophilic fungi,
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
| Halophilic | 86 | 357,067 | 60,914 | 301 |
| Acid/Alkaliphilic | 26 | 76,342 | 24,408 | 191 |
| Solvent-tolerant | 14 | 99,627 | 48,912 | 798 |
| Cold-adapted | 29 | 117,277 | 42,777 | 347 |
| Mesophilic control | 18 | 99,557 | 129 | 16,661 |
| Piezophilic | 5 | 10,354 | 8,254 | 14 |
| Radiation-resistant | 6 | 12,073 | 11,903 | 37 |
| Metal-resistant | 6 | 11,552 | 0 | 125 |
| Endolithic | 2 | 6 | 0 | 0 |
| Xerophilic | 4 | 738 | 0 | 925 |
| Arsenic-resistant | 7 | 32,312 | 0 | 2,010 |
| Magnetotactic | 5 | 23,304 | 0 | 0 |
| Oligotrophic | 6 | 16,307 | 0 | 64 |

\* Experiments attributable via UniProt accession linkage; full-layer totals are larger (see below).
All four 2026 pools (cold/pH/piezo/rad) now carry AlphaFold structure backfills.

## Experimental layer by source

| Source | Records | Note |
|---|---:|---|
| FireProtDB | 533,071 | ddG / ΔTm mutations |
| ThermoMutDB | 8,239 | ddG / dTm (2.0, 250 proteins, [Xavier/Rodrigues NAR](http://thermomutdb.pathotrack.health)) |
| Meltome Atlas | 206,549 | In-cell melting temperatures, 48,698 proteins × 14 organisms (Jarzab 2020) |
| BRENDA (stability + optima) | 137,038 | T_stab / T_opt / pH optima-stability-range |
| BRENDA (kinetics, v3) | 75,520 | Km 27,880 / IC50 15,974 / kcat 14,061 / Ki 8,988 / specific activity 8,617 |
| ProThermDB | 2,921 | ΔTm (100% SIFTS accession-linked) |
| pH-Tm compilation | 1,883 | Curated pH-stability pairs |
| OrganiZymeDB | 1,833 | Solvent Tm for enzymes |
| Literature table extraction | 5,967 | Stability tables mined from OA full text across 11 dimensions |
| DES literature (Radović 2024) | 164 | Deep eutectic solvent stability |

Plus: 2,438,069 CLEAN EC predictions (NAR 2026, contrastive-learning enzyme annotation,
52% at confidence ≥0.9) and 1,320 BRENDA identity annotations (metal-ion dependence,
inhibitors, oxygen sensitivity).

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
| Meltome Atlas | 206,549 in-cell Tm | [Jarzab et al., Nat Methods 2020](https://doi.org/10.1038/s41592-020-0801-4) |
| BRENDA | 212,538 enzyme parameters | [BRENDA](https://www.brenda-enzymes.org) |
| CLEAN DB | 2,438,069 EC predictions | [Yuan et al., NAR 2026](https://academic.oup.com/nar/advance-article/doi/10.1093/nar/gkag1003/8916836) |
| ProThermDB | 2,921 ΔTm | [Nikam et al., NAR 2021](https://doi.org/10.1093/nar/gkaa1070) |
| OrganiZymeDB | 1,833 solvent Tm | [Debruyne & Pucci, NAR 2026](https://doi.org/10.1093/nar/gkag1069) |
| Europe PMC | 135 full-text mining runs, 176 species anchored | [europepmc.org](https://europepmc.org) |
| BacDive | measured culture optima (27 species) | [Reimer et al., NAR 2022](https://doi.org/10.1093/nar/gkab799) |

## Changelog

- **v3.4.1 (2026-11-23)** — ThermoMutDB 2.0 import (+8,239 ddG/dTm, 250 proteins)
- **v3.4 (2026-11-23)** — Meltome Atlas in-cell melt temperatures (+206,549); BRENDA v3 kinetics (+75,520: Km/kcat/Ki/IC50/SA); identity layer (metal/inhibitor/oxygen, 1,320); CLEAN EC predictions (2.44M); structure backfill for all four new pools (structures 146K→234K); ProThermDB 100% SIFTS-linked; 4-dimension literature extraction (salt/arsenic/magnetotactic/oligotrophic, +1,192)
- **v3.3 (2026-11-21)** — arsenic (7), magnetotactic (5), oligotrophic (6) pools; BRENDA→UniProt 67%
- **v3.2 (2026-11-21)** — metal/endolithic/xerophilic pools; EN-first UI v2
- **v3.1 (2026-11-20)** — piezo/rad pools; BRENDA integration; cold pool
- **v3.0 (2026-11-18)** — English-first UI, 8 dimension pools

## License

Code: MIT. Data: CC-BY 4.0 (with upstream source terms — see individual source databases).

## Citation

If you use EnvTolDB, please cite the EnvProGen manuscript (in preparation) and the
underlying sources listed above.
