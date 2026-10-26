# TESS Sector 103: anomalous light-curve candidates (development sample)

Generated 2026-10-26 11:59 UTC by `scripts/fase6.py` at commit `57ebce4`, parameters fingerprint `b8cb320b43cbd27f`.

> Everything in this report is a **candidate for verification**, not a discovery. A label `assente` only means that no variability class was found in the four catalogues queried.

## 1. Summary

- 3,000 light curves of sector 103 were analysed; 2,980 had cleaned data and features.
- After artifact rejection 1,354 stars survived; the first 50 in the anomaly ranking are the candidates.
- Catalogue labels: **31 known** (a catalogue class explains the event), **13 known with a different class**, **6 absent** from SIMBAD, VSX, TOI and the TESS EB catalogue as variables.
- Of the 6 absent candidates, 5 show the same event type in another sector, 0 do not, and 1 cannot be checked.
- 0 candidates are flagged as a likely systematic (coincident events on the same CCD); 14 have a known variable star within 42".
- This is the **development sample**: parameters were tuned on it, so its numbers are not an unbiased estimate. The final run on all targets uses the same parameters, frozen.

## 2. Data and versions

|  |  |
|---|---|
| Sector | 103 |
| Product | SPOC light curves, 120 s cadence, PDCSAP flux |
| Data release | DR141 |
| SPOC version | `spoc-5.0.126-20251212` |
| File date (header DATE) | 2026-06-10 |
| Downloaded | 2026-10-25T23:13:02+00:00 – 2026-10-25T23:19:51+00:00 |
| Files | 3,000 (5.78 GB) |
| QUALITY bitmask rejected | 16575 |
| SIMBAD queried | 2026-10-26T00:04:52Z – 2026-10-26T00:05:38Z |
| TESS EB (Prša et al. 2022) queried | 2026-10-26T00:09:09Z – 2026-10-26T00:09:31Z |
| VSX queried | 2026-10-26T00:04:53Z – 2026-10-26T00:05:39Z |
| TOI table (ExoFOP) downloaded | 2026-10-26 |
| Other-sector curves (persistence) | 190 curves, 0 errors, data releases 38–142 |
| Other-sector SPOC versions | `spoc-5.0.9-20200827`, `spoc-5.0.10-20200904`, `spoc-5.0.11-20200915`, `spoc-5.0.13-20201001`, `spoc-5.0.22-20210121`, `spoc-5.0.23-20210212`, `spoc-5.0.35-20210626`, `spoc-5.0.96-20230729`, `spoc-5.0.98-20230826`, `spoc-5.0.99-20230915`, `spoc-5.0.100-20230922`, `spoc-5.0.122-20250630`, `spoc-5.0.123-20250818`, `spoc-5.0.124-20250919-1-g4fdf1a46a8`, `spoc-5.0.126-20251212` |

Persistence uses only SPOC light curves (2 min and 20 s) of sectors up to 104, the last with published release notes. Later sectors are not used (see section 12).

## 3. Protocol

Development sample of 3,000 targets (seed 103, stratified by Tmag). All thresholds were tuned on it. `frozen = false`.
Every phase records the parameters fingerprint; all phases of this report share `b8cb320b43cbd27f`.

## 4. Cleaning, features, models

|  |  |
|---|---|
| Light curves in / kept | 3,000 / 2,980 |
| Excluded | nonpositive_median: 20 |
| Cadences raw / clean | 56,907,000 / 45,597,416 (80.1%) |
| Dropped by QUALITY flags | 6,430,417 |
| Dropped as non-finite flux | 4,879,167 |
| Dropped in short segments | 0 |
| Features ok / errors | 2,980 / 0 |
| Spearman ρ, Isolation Forest vs LOF | 0.53 |
| IF/LOF overlap in top 50 / 100 / 300 | 10 / 23 / 83 |
| Driving event within 0.1 d of an edge, top vs all | 0.26 vs 0.153 |

The two models disagree substantially, so the ranking uses the mean of their percentile ranks.

## 5. Artifact rejection

Criteria are applied in order and a star is removed by the first it fails (*sequential*); *independent* counts how many stars would fail each criterion alone.

| criterion | rejects when | all, sequential | all, independent | top 50, sequential | top 50, independent |
|---|---|---|---|---|---|
| `flusso_indefinito` | robust relative scatter > `max_mad_std`: PDCSAP median close to zero | 811 | 811 | 11 | 11 |
| `contaminazione` | `CROWDSAP` < `min_crowdsap`: less than half the aperture flux is from the target | 550 | 1312 | 3 | 14 |
| `sistematica_centroide` | \|r\| between flux and a centroid > `max_corr_centr` | 2 | 51 | 0 | 0 |
| `sistematica_fondo` | \|r\| between flux and background > `max_abs_corr_bkg` | 25 | 30 | 3 | 3 |
| `evento_al_bordo` | the driving event is within `min_edge_d` of a segment edge | 238 | 414 | 4 | 6 |
| `evento_impulsive_outlier` | fraction of 'Impulsive outlier' cadences in the event >= `max_q512_frac` | 0 | 1 | 0 | 0 |
| `sopravvissute` | no criterion failed (survivors) | 1354 | — | 29 | — |

36 of the 50 candidates are also in the top 50 when the models are refit on the survivors of the star criteria only.

## 6. Catalogue labels

Labels are the pipeline codes: `noto` = known, a catalogue class explains the driving event; `noto con classe diversa` = known with a class that does not explain it; `assente` = no variability class in any catalogue queried. Persistence: `persistente` = the same event type in another sector, `non persistente` = other sectors exist but show nothing, `persistenza non verificabile` = no usable other sector.

| driving event | noto | noto con classe diversa | assente | total |
|---|---|---|---|---|
| dip | 24 | 7 | 5 | 36 |
| flare | 7 | 6 | 1 | 14 |
| total | 31 | 13 | 6 | 50 |

| persistence | candidates |
|---|---|
| persistente | 44 |
| non persistente | 3 |
| persistenza non verificabile | 3 |

## 7. Candidates absent from the catalogues (6)

Not in SIMBAD, VSX, TOI or the TESS EB catalogue as variables. The SIMBAD column is the identifier of a plain star at the position, if any.

`rank` is the position in the anomaly ranking before artifact rejection; `other sectors with event` counts sectors where the same event type reaches SNR ≥ 10.

| rank | TIC | event | SIMBAD | otype | VSX | Tmag | persistence | other sectors with event | known variable within 42" | warnings | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 292292315 | dip | HD 170312 | * | — | 8.29 | persistente | 3/8 sectors (S39, S93, S102) | — | — | [plot](figures/s103_sample/002_tic292292315.png) |
| 31 | 149064422 | flare | Gaia DR3 6007435426246132736 | * | — | 12.18 | persistenza non verificabile | no other sector | — | — | [plot](figures/s103_sample/019_tic149064422.png) |
| 37 | 469974264 | dip | — | — | — | 11.90 | persistente | 2/3 sectors (S95, S104) | — | — | [plot](figures/s103_sample/023_tic469974264.png) |
| 45 | 410151515 | dip | HD 214554 | * | — | 8.31 | persistente | 8/8 sectors (S28, S67, S68, S94, S95, S101, S102, S104) | — | — | [plot](figures/s103_sample/027_tic410151515.png) |
| 47 | 142329176 | dip | HD 137217 | * | — | 8.61 | persistente | 1/1 sectors (S102) | — | — | [plot](figures/s103_sample/028_tic142329176.png) |
| 81 | 138188560 | dip | HD 136505 | * | — | 5.67 | persistente | 3/4 sectors (S38, S12, S102) | Gaia DR3 5889651377041608448 (DSCT\|GDOR\|SXPHE, 37"); Gaia DR3 5889651308322116864 (ROT, 15") | — | [plot](figures/s103_sample/038_tic138188560.png) |

## 8. Candidates known with a different class (13)

The target has a catalogued variability class that does not explain the driving event (for example a rotator with a dip).

| rank | TIC | event | SIMBAD | otype | VSX | Tmag | persistence | other sectors with event | known variable within 42" | warnings | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | 201290666 | flare | CD-60     8 | * | ROT | 9.18 | persistente | 2/2 sectors (S102, S104) | CD-60     8B (EB*, 20") | — | — |
| 18 | 263385369 | flare | HD 139966 | cC* | DCEPS(B) | 8.57 | non persistente | 0/2 sectors | V* HH Nor (EB*, 12"); HH Nor (EA/DS, 12") | contaminazione_parziale | — |
| 43 | 246957312 | dip | HD 152235 | s*b | ELL: | 4.33 | persistente | 1/1 sectors (S39) | CXOU J165359.8-415935 (Y*O, 13"); Gaia DR3 5966501497401307008 (L, 21") | — | — |
| 58 | 360541225 | dip | V* MO TrA | LP* | SRB | 4.65 | persistente | 7/7 sectors (S39, S66, S65, S93, S100, S101, S102) | Gaia DR3 5822188882581056896 (ROT, 22") | — | — |
| 79 | 122162363 | dip | V* HR Lup | a2* | SXARI | 5.86 | non persistente | 0/4 sectors | — | — | — |
| 87 | 2743109 | flare | HD 147558 | Pu* | DSCT\|GDOR\|SXPHE | 7.98 | persistente | 1/4 sectors (S93) | Gaia DR3 5941489742482330752 (RR*, 30"); ASTEP V-0907 (Ro*, 36"); Gaia DR3 5941492697433852160 (DSCT\|GDOR\|SXPHE, 36"); Gaia DR3 5941489742482330752 (RRC, 30") | — | — |
| 93 | 229807000 | flare | 1RXS J232857.5-680225 | PM* | ROT | 10.80 | persistente | 8/9 sectors (S27, S28, S1, S67, S68, S94, S95, S102) | — | — | — |
| 97 | 197960398 | flare | 1RXS J231318.1-493322 | PM* | ROT | 11.47 | persistente | 6/6 sectors (S28, S68, S95, S102, S96, S104) | — | — | — |
| 100 | 364361425 | dip | HD 146219 | * | RS | 8.93 | persistente | 2/2 sectors (S39, S65) | — | — | — |
| 101 | 344237828 | dip | HD 150898 | s*b | — | 5.67 | persistente | 2/6 sectors (S12, S100) | — | — | — |
| 102 | 281741629 | flare | CD-56   152 | Be* | BE | 10.51 | persistente | 1/6 sectors (S2) | — | — | — |
| 109 | 281763691 | dip | V* BU Phe | LP* | SRB | 4.87 | persistente | 7/9 sectors (S28, S1, S68, S2, S95, S96, S104) | — | — | — |
| 110 | 58749494 | dip | WRAY 15-1392 | Em* | MISC | 10.89 | persistente | 1/1 sectors (S12) | — | — | — |

## 9. Persistence not verifiable (3)

No other SPOC sector up to 104, or none readable. These candidates are **kept**; they need another sector or other photometry.

| rank | TIC | event | SIMBAD | otype | VSX | Tmag | persistence | other sectors with event | known variable within 42" | warnings | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 31 | 149064422 | flare | Gaia DR3 6007435426246132736 | * | — | 12.18 | persistenza non verificabile | no other sector | — | — | [plot](figures/s103_sample/019_tic149064422.png) |
| 71 | 374457616 | flare | V* HO Lup | Or* | INT | 11.77 | persistenza non verificabile | no other sector | V* HO Lup B (Y*O, 2"); V* HO Lup A (Or*, 1") | — | [plot](figures/s103_sample/033_tic374457616.png) |
| 84 | 374644882 | dip | Sz  95 | TT* | YSO | 12.83 | persistenza non verificabile | no other sector | — | contaminazione_parziale | [plot](figures/s103_sample/039_tic374644882.png) |

Not persistent (3): other sectors exist but none shows the same event type with SNR ≥ 10: TIC 263385369 (noto con classe diversa), TIC 281728276 (noto), TIC 122162363 (noto con classe diversa).

## 10. Flags

| flag | candidates |
|---|---|
| `sospetto_sistematica` | 0 |
| known variable within 42" (`variabile_vicina`) | 14 |
| warning `contaminazione_parziale` | 7 |
| warning `spostamento_centroide` | 6 |
| warning `impulsive_outlier_nell_evento` | 5 |

Warnings do not reject; they say what to check by hand (pixel-level data, centroids, neighbours).

## 11. Limits

- One sector, 2-min SPOC targets only: stars without a 2-min target are not searched.
- The anomaly ranking is unsupervised: it finds what is rare in this population, not what is new. Most top-ranked stars are known variables.
- Catalogue matching is by position (5") for SIMBAD and VSX and by TIC for TOI and the TESS EB catalogue (sectors 1–26 only). Catalogues not queried (Gaia DR3 variability, ASAS-SN, ZTF, KELT) may already list some `assente` candidates. Answers are cached at the query dates above.
- TESS pixels are 21": a nearby star can be the true source. Crowding is only filtered by `CROWDSAP`; no pixel-level centroid analysis was done.
- Persistence checks only the same event type with SNR ≥ 10, and only in sectors up to 104.
- Thresholds were tuned on the development sample. The sample numbers are therefore optimistic.

## 12. VDX Core and next version

- Registered in VDX Core: run id 1 (duplicate), 50/50 results accepted, plots attached 0 + 50 already present, dataset linked: no.
- Pipeline log messages from the send (Italian, verbatim):
  - `dataset rifiutato: custom.dataset is outside this source's scope; crealo dalla console con externalId tess-s103-spoc-2min-dr141`
  - `50 risultati rifiutati con extra (property "extra": unknown property "tic_id"): inviati senza`
- v2: add sectors after 104 (105–107 have data on MAST) to the persistence check once their release notes are published; query Gaia DR3 variability and ASAS-SN; pixel-level centroid tests for the absent candidates.

