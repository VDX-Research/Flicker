# TESS Sector 103: anomalous light-curve candidates (all targets)

Generated 2026-10-26 13:18 UTC by `scripts/fase6.py` at commit `d43bd98`, parameters fingerprint `7c11bba8442014f5`.

> Everything in this report is a **candidate for verification**, not a discovery. A label `assente` only means that no variability class was found in the four catalogues queried.

## 1. Summary

- 12,995 light curves of sector 103 were analysed; 12,919 had cleaned data and features.
- After artifact rejection 5,952 stars survived; the first 50 in the anomaly ranking are the candidates.
- Catalogue labels: **29 known** (a catalogue class explains the event), **10 known with a different class**, **11 absent** from SIMBAD, VSX, TOI and the TESS EB catalogue as variables.
- Of the 11 absent candidates, 9 show the same event type in another sector, 1 do not, and 1 cannot be checked.
- 0 candidates are flagged as a likely systematic (coincident events on the same CCD); 12 have a known variable star within 42".

## 2. Data and versions

|  |  |
|---|---|
| Sector | 103 |
| Product | SPOC light curves, 120 s cadence, PDCSAP flux |
| Data release | DR141 |
| SPOC version | `spoc-5.0.126-20251212` |
| File date (header DATE) | 2026-06-10 |
| Downloaded | 2026-10-25T23:13:02+00:00 – 2026-10-26T12:53:58+00:00 |
| Files | 12,995 (25.04 GB) |
| QUALITY bitmask rejected | 16575 |
| SIMBAD queried | 2026-10-26T00:04:52Z – 2026-10-26T13:16:16Z |
| TESS EB (Prša et al. 2022) queried | 2026-10-26T00:09:09Z – 2026-10-26T13:16:16Z |
| VSX queried | 2026-10-26T00:04:53Z – 2026-10-26T13:16:16Z |
| TOI table (ExoFOP) downloaded | 2026-10-26 |
| Other-sector curves (persistence) | 206 curves, 0 errors, data releases 38–142 |
| Other-sector SPOC versions | `spoc-5.0.9-20200827`, `spoc-5.0.10-20200904`, `spoc-5.0.11-20200915`, `spoc-5.0.13-20201001`, `spoc-5.0.16-20201026`, `spoc-5.0.20-20201120`, `spoc-5.0.22-20210121`, `spoc-5.0.23-20210212`, `spoc-5.0.35-20210626`, `spoc-5.0.96-20230729`, `spoc-5.0.98-20230826`, `spoc-5.0.99-20230915`, `spoc-5.0.100-20230922`, `spoc-5.0.122-20250630`, `spoc-5.0.123-20250818`, `spoc-5.0.124-20250919-1-g4fdf1a46a8`, `spoc-5.0.126-20251212` |

Persistence uses only SPOC light curves (2 min and 20 s) of sectors up to 104, the last with published release notes. Later sectors are not used (see section 12).

## 3. Protocol

**Tuned then frozen.** All thresholds were tuned on the development sample of 3,000 targets (seed 103, stratified by Tmag); then `frozen = true` was set and this single run on all 12,995 targets was made without changing anything.
Every phase records the parameters fingerprint; all phases of this report share `7c11bba8442014f5`.

## 4. Cleaning, features, models

|  |  |
|---|---|
| Light curves in / kept | 12,995 / 12,919 |
| Excluded | nonpositive_median: 76 |
| Cadences raw / clean | 246,502,155 / 197,457,805 (80.1%) |
| Dropped by QUALITY flags | 27,858,934 |
| Dropped as non-finite flux | 21,185,416 |
| Dropped in short segments | 0 |
| Features ok / errors | 12,919 / 0 |
| Spearman ρ, Isolation Forest vs LOF | 0.27 |
| IF/LOF overlap in top 50 / 100 / 300 | 3 / 14 / 56 |
| Driving event within 0.1 d of an edge, top vs all | 0.34 vs 0.148 |

The two models disagree substantially, so the ranking uses the mean of their percentile ranks.

## 5. Artifact rejection

Criteria are applied in order and a star is removed by the first it fails (*sequential*); *independent* counts how many stars would fail each criterion alone.

| criterion | rejects when | all, sequential | all, independent | top 50, sequential | top 50, independent |
|---|---|---|---|---|---|
| `flusso_indefinito` | robust relative scatter > `max_mad_std`: PDCSAP median close to zero | 3502 | 3502 | 14 | 14 |
| `contaminazione` | `CROWDSAP` < `min_crowdsap`: less than half the aperture flux is from the target | 2396 | 5708 | 2 | 16 |
| `sistematica_centroide` | \|r\| between flux and a centroid > `max_corr_centr` | 11 | 255 | 0 | 1 |
| `sistematica_fondo` | \|r\| between flux and background > `max_abs_corr_bkg` | 79 | 97 | 1 | 1 |
| `evento_al_bordo` | the driving event is within `min_edge_d` of a segment edge | 979 | 1707 | 7 | 8 |
| `evento_impulsive_outlier` | fraction of 'Impulsive outlier' cadences in the event >= `max_q512_frac` | 0 | 4 | 0 | 0 |
| `sopravvissute` | no criterion failed (survivors) | 5952 | — | 26 | — |

38 of the 50 candidates are also in the top 50 when the models are refit on the survivors of the star criteria only.

## 6. Catalogue labels

Labels are the pipeline codes: `noto` = known, a catalogue class explains the driving event; `noto con classe diversa` = known with a class that does not explain it; `assente` = no variability class in any catalogue queried. Persistence: `persistente` = the same event type in another sector, `non persistente` = other sectors exist but show nothing, `persistenza non verificabile` = no usable other sector.

| driving event | noto | noto con classe diversa | assente | total |
|---|---|---|---|---|
| dip | 25 | 3 | 9 | 37 |
| flare | 4 | 7 | 2 | 13 |
| total | 29 | 10 | 11 | 50 |

| persistence | candidates |
|---|---|
| persistente | 41 |
| non persistente | 6 |
| persistenza non verificabile | 3 |

## 7. Candidates absent from the catalogues (11)

Not in SIMBAD, VSX, TOI or the TESS EB catalogue as variables. The SIMBAD column is the identifier of a plain star at the position, if any.

`rank` is the position in the anomaly ranking before artifact rejection; `other sectors with event` counts sectors where the same event type reaches SNR ≥ 10.

| rank | TIC | event | SIMBAD | otype | VSX | Tmag | persistence | other sectors with event | known variable within 42" | warnings | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 183562384 | dip | HD   4292 | SB* | — | 9.44 | persistente | 4/4 sectors (S29, S69, S96, S104) | — | — | [plot](figures/s103_all/001_tic183562384.png) |
| 4 | 292292315 | dip | HD 170312 | * | — | 8.29 | persistente | 3/8 sectors (S39, S93, S102) | — | — | [plot](figures/s103_all/003_tic292292315.png) |
| 6 | 231632822 | dip | HD 201172 | * | — | 6.76 | persistente | 1/3 sectors (S104) | — | spostamento_centroide | [plot](figures/s103_all/005_tic231632822.png) |
| 10 | 370324073 | dip | TYC 8829-111-1 | SB* | — | 10.59 | persistente | 5/6 sectors (S1, S68, S95, S102, S104) | — | — | [plot](figures/s103_all/007_tic370324073.png) |
| 14 | 464846595 | dip | HD 138585 | * | — | 8.68 | persistente | 2/2 sectors (S38, S102) | — | — | [plot](figures/s103_all/010_tic464846595.png) |
| 39 | 260889990 | flare | UCAC4 114-133248 | ** | — | 11.78 | persistente | 4/5 sectors (S28, S1, S102, S104) | — | contaminazione_parziale | [plot](figures/s103_all/023_tic260889990.png) |
| 49 | 299271875 | dip | HD 145453 | * | — | 8.86 | persistente | 3/4 sectors (S39, S100, S101) | — | — | [plot](figures/s103_all/026_tic299271875.png) |
| 73 | 281597526 | flare | TYC 8469-985-1 | * | — | 10.52 | non persistente | 0/7 sectors | Gaia DR3 4921347495408879360 (ROT, 21") | — | [plot](figures/s103_all/039_tic281597526.png) |
| 85 | 469974264 | dip | — | — | — | 11.90 | persistente | 2/3 sectors (S95, S104) | — | — | [plot](figures/s103_all/046_tic469974264.png) |
| 93 | 39177520 | dip | HD 150168 | s*b | — | 5.74 | persistente | 1/4 sectors (S66) | Gaia DR3 5937811566860730368 (EB*, 23"); Gaia DR3 5937811566860730368 (E, 23") | — | [plot](figures/s103_all/049_tic39177520.png) |
| 94 | 8419033 | dip | TYC 7335-61-1 | * | — | 10.33 | persistenza non verificabile | no other sector | Gaia DR3 6013116224871328128 (ROT, 26") | — | [plot](figures/s103_all/050_tic8419033.png) |

## 8. Candidates known with a different class (10)

The target has a catalogued variability class that does not explain the driving event (for example a rotator with a dip).

| rank | TIC | event | SIMBAD | otype | VSX | Tmag | persistence | other sectors with event | known variable within 42" | warnings | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 17 | 232064182 | flare | SCR J2241-6119A | PM* | ROT | 11.82 | persistente | 6/6 sectors (S27, S28, S1, S68, S95, S104) | — | spostamento_centroide; impulsive_outlier_nell_evento | — |
| 22 | 229147922 | flare | UCAC4 208-001676 | PM* | ROT | 12.23 | persistente | 7/7 sectors (S29, S30, S2, S3, S69, S96, S104) | — | impulsive_outlier_nell_evento | — |
| 55 | 201290666 | flare | CD-60     8 | * | ROT | 9.18 | persistente | 2/2 sectors (S102, S104) | CD-60     8B (EB*, 20") | — | — |
| 61 | 263385369 | flare | HD 139966 | cC* | DCEPS(B) | 8.57 | non persistente | 0/2 sectors | V* HH Nor (EB*, 12"); HH Nor (EA/DS, 12") | contaminazione_parziale | — |
| 64 | 217667184 | dip | * iot Ara | Be* | BE | 5.34 | persistente | 2/5 sectors (S39, S104) | — | — | — |
| 66 | 36583537 | dip | CD-48 11039 | * | VAR | 10.57 | persistente | 2/2 sectors (S66, S93) | [SPB2016] SFO79  86 (Y*O, 25") | — | — |
| 67 | 350856014 | flare | * iot TrA | SB* | GDOR | 4.96 | persistente | 5/5 sectors (S66, S93, S100, S101, S102) | — | — | — |
| 78 | 455309397 | dip | * omi Lup | ** | VAR: | 4.37 | non persistente | 0/4 sectors | — | — | — |
| 80 | 325709821 | flare | * gam Ara | Be* | ACYG | 3.41 | non persistente | 0/5 sectors | Gaia DR3 5922299446337996800 (VAR, 28") | — | — |
| 82 | 394137224 | flare | 1RXS J001723.4-664507 | PM* | ROT | 10.15 | persistente | 7/7 sectors (S28, S1, S68, S95, S102, S96, S104) | — | impulsive_outlier_nell_evento | — |

## 9. Persistence not verifiable (3)

No other SPOC sector up to 104, or none readable. These candidates are **kept**; they need another sector or other photometry.

| rank | TIC | event | SIMBAD | otype | VSX | Tmag | persistence | other sectors with event | known variable within 42" | warnings | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 374813201 | dip | V* V1279 Sco | Or* | CTTS | 11.35 | persistenza non verificabile | no other sector | THA 15-24 (Or*, 27"); Sz 97 (CTTS, 27") | spostamento_centroide | [plot](figures/s103_all/013_tic374813201.png) |
| 47 | 95004705 | dip | UCAC4 296-090639 | EB* | E | 12.16 | persistenza non verificabile | no other sector | — | spostamento_centroide; contaminazione_parziale | [plot](figures/s103_all/025_tic95004705.png) |
| 94 | 8419033 | dip | TYC 7335-61-1 | * | — | 10.33 | persistenza non verificabile | no other sector | Gaia DR3 6013116224871328128 (ROT, 26") | — | [plot](figures/s103_all/050_tic8419033.png) |

Not persistent (6): other sectors exist but none shows the same event type with SNR ≥ 10: TIC 57264513 (noto), TIC 263385369 (noto con classe diversa), TIC 265435357 (noto), TIC 281597526 (assente), TIC 455309397 (noto con classe diversa), TIC 325709821 (noto con classe diversa).

## 10. Flags

| flag | candidates |
|---|---|
| `sospetto_sistematica` | 0 |
| known variable within 42" (`variabile_vicina`) | 12 |
| warning `spostamento_centroide` | 9 |
| warning `impulsive_outlier_nell_evento` | 5 |
| warning `contaminazione_parziale` | 5 |

Warnings do not reject; they say what to check by hand (pixel-level data, centroids, neighbours).

## 11. Limits

- One sector, 2-min SPOC targets only: stars without a 2-min target are not searched.
- The anomaly ranking is unsupervised: it finds what is rare in this population, not what is new. Most top-ranked stars are known variables.
- Catalogue matching is by position (5") for SIMBAD and VSX and by TIC for TOI and the TESS EB catalogue (sectors 1–26 only). Catalogues not queried (Gaia DR3 variability, ASAS-SN, ZTF, KELT) may already list some `assente` candidates. Answers are cached at the query dates above.
- TESS pixels are 21": a nearby star can be the true source. Crowding is only filtered by `CROWDSAP`; no pixel-level centroid analysis was done.
- Isolation Forest and LOF agree weakly (Spearman ρ 0.27, 3 of the top 50 shared), less than on the development sample (ρ 0.53, 10 shared): the candidate list depends on the choice of model, and other anomalous stars sit just below the cut.
- Persistence checks only the same event type with SNR ≥ 10, and only in sectors up to 104.
- Thresholds were tuned on the development sample.

## 12. VDX Core and next version

- Registered in VDX Core: run id 2 (created), 50/50 results accepted, plots attached 50 + 0 already present, dataset linked: yes.
- v2: add sectors after 104 (105–107 have data on MAST) to the persistence check once their release notes are published; query Gaia DR3 variability and ASAS-SN; pixel-level centroid tests for the absent candidates.

