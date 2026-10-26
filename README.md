# vdx-research-tess

Reproducible VDX Research pipeline that searches TESS Sector 103 light curves for
anomalously behaving objects not yet cataloged. The output is a list of
**candidates for verification**, not discoveries.

## Data

| | |
|---|---|
| Sector | 103 (Year 8) |
| Product | 2-minute SPOC light curves (`*_lc.fits`), PDCSAP flux |
| Data release | DR141 (`DATA_REL = 141`, release notes DRN141) |
| SPOC version | `spoc-5.0.126-20251212` |
| File timestamp (header `DATE`) | 2026-06-10 |
| Download | development sample: 2026-10-25 (23:13–23:19 UTC), from `archive.stsci.edu/missions/tess/tid/s0103/`; final run: timestamp in `data/products_s103_all.json` |
| Targets | 13,000 light curves at 120 s (plus 2,566 at 20 s, unused) |

Versions are read from the header of each downloaded file and saved to
`data/products_s103_<sample|all>.json`; the manifest `data/manifest_s103_<...>.csv` records
for each light curve the file size, sha256, download date, `DATA_REL`, and `PROCVER`. Downloads reject
files with a data release different from the one specified in `config/pipeline.toml`.

### Persistence across other sectors

The persistence check only uses SPOC light curves (2-min and 20-s) from sectors with published
release notes, i.e., up to Sector 104 (`scripts/sector_overlap.py`, results in
`data/overlap_s103.csv`). Out of the 13,000 TICs in Sector 103:

| other SPOC sectors (≤ 104) | TIC | % |
|---|---|---|
| Year 8, sectors 99–104 | 9,550 | 73.5 |
| Year 7, sectors 91–97 | 3,687 | 28.4 |
| Years 1–5, sectors 1–69 | 6,583 | 50.6 |
| at least one | 11,033 | 84.9 |
| none | 1,967 | 15.1 |

Sectors 105–107 already have light curves on MAST but not yet release notes: they are excluded from
this version because all data used must be citable. They may be utilized in a second
version. Candidates with no other sectors are labeled "persistence not verifiable",
remain in the list, and have a dedicated section in the report.

## Protocol: development sample, then frozen parameters

1. All thresholds and parameters (`config/pipeline.toml`) are decided **solely** on a development
   sample of 3,000 targets, extracted reproducibly: seed 103, stratified by
   TESS magnitude (`tmag_edges` bins, proportional allocation via the largest remainder
   method). The sample is in `data/sample_s103.csv`.
2. Once the pipeline is stable, `frozen = true` is set and a **single** final run is executed across
   all 13,000 targets without altering anything further. The script rejects `--all` if the parameters
   are not frozen, and every execution logs the hash (sha256) of the parameters used.

## Cleaning (PHASE 1)

For each light curve, in order, with the number of cadences removed by each step recorded in the summary
`data/clean_s103_<...>.csv`:

1. **Quality flags**: cadences matching any bit of mask 16575 in `QUALITY` are discarded, i.e., the
   lightkurve 2.6 default (17087) minus "Impulsive outlier" (512). An impulsive outlier may
   be a genuine short event: it is retained and evaluated during the artifact rejection phase.
2. **Non-finite values** in time, flux, or error (including cadences affected by scattered light, which
   SPOC already sets to NaN in PDCSAP).
3. **Gaps**: a gap greater than 0.5 days separates two segments; fragments shorter than 0.5
   days are discarded.
4. **Normalization**: each segment is divided by its median.
5. Light curves with fewer than 1,000 valid cadences are excluded, as well as curves with a flux median ≤ 0
   in any segment (over-subtracted background: non-normalizable).

On the development sample (3,000 curves, 18,969 cadences each, 3 segments): quality flags remove an
average of 2,144 cadences (11.3%), non-finite values 1,626 (8.6%), short fragments 0; leaving an
average of 15,199 cadences. 20 curves were excluded, all due to median ≤ 0, all faint stars
(Tmag 13.6–20.6, median 18.6). 2,980 remain.

Note on the sample: 34% of targets in the sector (4,400) have Tmag ≥ 16 (stars from Gaia DR2, up to
Tmag 20.8). They belong to the single bin Tmag ≥ 13, where extraction is random, meaning their
proportion in the sample is representative; PHASE 2 thresholds will account for this.

No detrending and no sigma-clipping: they would remove the anomalous signals we are looking for.
Centroids, background, and `QUALITY` are preserved in the cleaned curve for artifact rejection.

## Features (PHASE 2)

`src/vdxtess/features.py`, parameters in `[features]` of `config/pipeline.toml`, output
`data/features_s103_<...>.csv` (one row per TIC, with Tmag, Teff, radius, position, camera/CCD,
`CROWDSAP`, `FLFRCSAP` and CDPP from the header). Four interpretable groups, which are the inputs to the models
(`MODEL_FEATURES`):

| group | computed on | features |
|---|---|---|
| variability and distribution | cleaned curve, not detrended | `std`, `mad_std`, `noise_ratio` (MAD / median error, ~1 for a constant star), `p2p_std` (point-to-point noise), `amp_90`, `amp_98` (5–95 and 1–99 percentile ranges), `skew`, `kurt`, `eta` (von Neumann ratio, ~2 for white noise, ≪ 2 for coherent variability) |
| periodogram | 10-min bins | Lomb-Scargle between 0.05 and 13 d: `ls_period`, `ls_power`, `ls_amp` |
| transit-like dips | curve flattened by a 1-day running median (per segment, reflected edges), 10-min bins | BLS between 0.5 and 13 d, durations 1–8 h, errors = robust noise of the binned curve: `bls_period`, `bls_depth`, `bls_duration_h`, `bls_snr` |
| isolated events | flattened curve | at least 3 consecutive cadences beyond 4 robust σ, below (dips) or above (flares) the baseline; a single point does not count: `n_dips`, `dip_depth`, `dip_snr`, `dip_duration_h` and the same for `flare_*`, for the strongest event |

Flattening is used only for BLS and the events: it removes variability slower than one day, and with it
dimmings longer than a few hours, which remain visible in the first group (asymmetry, amplitude).

Diagnostic columns (`diag_*`, `t_*`) are not model inputs: they feed the explicit
artifact rejection phase. They are: the correlation of the flattened flux with the centroids (`diag_corr_centr`) and
with the background (`diag_corr_bkg`); for the strongest dip and flare, the distance from the nearest segment edge
(`diag_*_edge_d`), the number of "Impulsive outlier" cadences (`diag_*_q512`) and the centroid shift
during the event relative to the out-of-event scatter (`diag_*_centr_shift`); the BLS edge distance
(`diag_bls_edge_d`). Tests on synthetic curves are in `tests/test_features.py`: a null curve, a sinusoid, a box transit, a flare,
a single outlier, and a dip with a centroid shift.

On the development sample (2,980 curves, 149 s with 8 processes, no errors, all features finite):

- **Faint stars dominate the amplitudes.** The median `mad_std` grows from 0.0009 (Tmag ≤ 10) to 1.1
  (Tmag > 18) while `noise_ratio` stays ~0.93: for faint stars the flux is consistent with noise, and the absolute
  amplitudes (`std` up to 274) reflect a median close to zero, not variability. 362 curves have `std` > 1,
  all with Tmag ≥ 16. PHASE 3 must use noise-relative or robustly scaled features, otherwise the
  models will single out faint stars.
- **Events cluster at segment edges.** 16% of curves have at least one dip and 19% at least one flare, but
  305 of 487 dips and 249 of 557 flares lie within 0.1 d of a segment edge, and 54 and 82 respectively contain
  "Impulsive outlier" cadences. These are the first artifact rejection criteria.
- BLS: 34% of curves have `bls_snr` < 7, the level of the synthetic null curve (4.4–5.6).

## Models and ranking (PHASE 3)

`src/vdxtess/models.py`, parameters in `[models]` of `config/pipeline.toml`, output
`data/ranking_s103_<...>.csv` and plots in `data/plots/s103_<...>/` (not tracked).

- **Inputs** (`design_matrix`): 19 columns, all dimensionless or in units of the point-to-point noise
  (`p2p_std`): e.g. `std/p2p_std`, `amp_90/p2p_std`, `amp_98/amp_90` (tail weight), asinh of skewness and
  kurtosis, log of `eta`, periods, BLS SNR, log1p of the event counts and SNRs. A faint star that is pure
  noise and a bright star that is pure noise get the same row (tested). Then `RobustScaler`
  (median 0, IQR 1).
- **Two methods**, chosen because they look at different things:
  - Isolation Forest (500 trees, 256 samples, seed 103) finds global anomalies, with extreme values in a few features;
  - Local Outlier Factor (50 neighbours) finds local anomalies: unusual combinations relative to the
    nearest neighbours.
- **Ranking**: the mean of the two percentile ranks (1 = most anomalous). Ties are broken by the Isolation
  Forest score, then by TIC, so the order is deterministic. For each star, `drivers` lists the three features
  furthest from the median, so the reason is readable.
- **Plots** for the first `top_n` = 50: raw curve and 10-min bins; flattened curve with the strongest dip
  and flare marked; Lomb-Scargle periodogram; BLS phase fold.

On the development sample (2,980 curves, < 1 s):

| comparison IF vs LOF | value |
|---|---|
| Spearman rank correlation | 0.53 |
| shared in top 50 / 100 / 300 | 10 / 23 / 83 |

The agreement is moderate: the two methods disagree on most of the top, as expected from what each
measures, and the combined rank rewards the objects that both consider unusual. Composition of the top 50
compared with all curves:

| Tmag | ≤ 10 | 10–13 | 13–16 | 16–18 | > 18 |
|---|---|---|---|---|---|
| top 50 | 40% | 32% | 6% | 4% | 18% |
| all | 35.7% | 16.2% | 14.1% | 15.9% | 18.0% |

Noise normalization works: faint stars are not over-represented. The first ten are dominated by heavy
tails with strong negative skewness (eclipsing-binary-like light curves) or positive skewness with high
kurtosis (flare-like). Signals that need the artifact rejection phase:

- **Events at segment edges**: 26% of the top 50 have the strongest dip or flare within 0.1 d of an edge,
  against 15.3% of all curves.
- **Near-zero median flux**: 11 of the top 50 (all Tmag ≥ 17) have a relative scatter `mad_std` > 0.3,
  i.e. a PDCSAP median close to zero after background subtraction. Dividing by a running median that
  approaches zero produces spikes of hundreds to thousands, which show up as dips and flares
  (e.g. TIC 144639753, TIC 1816731414). In the whole sample, 811 curves (27%) are in this regime.

The ranking is a list of objects to look at, ordered by how unusual they are. It contains known variable
stars and artifacts. It is not a list of discoveries.

## Artifact rejection

`src/vdxtess/artifacts.py`, thresholds in `[artifacts]` of `config/pipeline.toml`, script
`scripts/artefatti.py`. Outputs:

- `data/artifacts_s103_<...>.csv`: the ranking plus the driving event, the rejection reason
  (`artifact_reason`, empty if the star passes) and the warnings;
- `data/artifact_counts_s103_<...>.csv`: counts per criterion;
- `data/candidates_s103_<...>.csv`: the first `top_n` = 50 survivors in rank order;
- plots in `data/plots/s103_<...>_candidati/`.

The criteria are applied in a fixed order. A star is rejected by the **first** criterion it fails. Each criterion is
counted in two ways:

- **sequential**: how many stars it removes after the previous criteria. These counts plus the survivors sum to the total.
- **independent**: how many stars would fail it on its own.

This makes two runs with different thresholds comparable criterion by criterion. A missing diagnostic (NaN) never rejects.

| # | code | rejects when | threshold |
|---|---|---|---|
| 1 | `flusso_indefinito` | relative scatter `mad_std` > threshold: PDCSAP median close to zero | 0.3 |
| 2 | `contaminazione` | `CROWDSAP` < threshold: less than half of the flux in the aperture belongs to the target | 0.5 |
| 3 | `sistematica_centroide` | correlation of the flattened flux with the centroids > threshold | 0.5 |
| 4 | `sistematica_fondo` | \|correlation of the flattened flux with the background\| > threshold | 0.3 |
| 5 | `evento_al_bordo` | the driving event lies within the threshold of a segment edge | 0.1 d |
| 6 | `evento_impulsive_outlier` | fraction of "Impulsive outlier" (bit 512) cadences in the driving event ≥ threshold | 0.5 |

Criteria 1–4 apply to the star. Criteria 5–6 apply only to the **driving event**, which is read from the first entry of
`drivers`:

- a dip, flare or BLS feature gives that event;
- a shape feature (skewness, tails, amplitude) gives a dip if the skewness is negative and a flare if it is positive;
- otherwise there is no driving event (e.g. periodic variability) and criteria 5–6 do not apply.

So a flare at an edge does not reject an eclipsing binary that was ranked for its eclipses.

**Warnings** do not reject; they say what to check by hand:

- `spostamento_centroide`: centroid shift during the event > 20 σ out of event;
- `impulsive_outlier_nell_evento`: at least one cadence with bit 512 in the event;
- `contaminazione_parziale`: `CROWDSAP` < 0.8.

**Why the thresholds and the warnings are set this way.** All thresholds were decided on the development sample and
then frozen with the rest of the parameters (Protocol).

- *Centroid shift (warning only).* The shift is measured in units of the out-of-event scatter, so it grows with the
  event SNR. Deep eclipses on bright stars exceed any fixed threshold even when they are on target.
- *Bit 512 (warning; the fraction criterion removes nothing on the sample).* SPOC flags the peaks of real flares
  with bit 512 too. The fraction criterion is still documented and counted, so the full run can be compared with
  the sample.
- *`sistematica_fondo`, \|r\| > 0.3.* Curves above this value are strongly over-represented at the top of the ranking:
  20 of the top 300, against 30 in the whole sample.
- *`sistematica_centroide`, 0.5.* The median correlation with the centroids grows towards faint stars, so a lower
  threshold would mostly remove faint stars.

On the development sample (2,980 curves):

| criterion | all, sequential | all, independent | top 300, seq. | top 300, ind. | top 50, seq. | top 50, ind. |
|---|---|---|---|---|---|---|
| `flusso_indefinito` | 811 | 811 | 50 | 50 | 11 | 11 |
| `contaminazione` | 550 | 1,312 | 30 | 80 | 3 | 14 |
| `sistematica_centroide` | 2 | 51 | 2 | 2 | 0 | 0 |
| `sistematica_fondo` | 25 | 30 | 17 | 20 | 3 | 3 |
| `evento_al_bordo` | 238 | 414 | 72 | 105 | 4 | 6 |
| `evento_impulsive_outlier` | 0 | 1 | 0 | 0 | 0 | 0 |
| survivors | 1,354 | | 129 | | 29 | |

The 50 candidates (the first 50 survivors, ranks 1–110 of the ranking):

- by driving event: 36 dips and 14 flares;
- by Tmag: 26 at ≤ 10, 22 at 10–13, 2 at 13–16, none fainter than 16;
- warnings: 13 have at least one (6 centroid shift, 5 bit 512 in the event, 7 partial contamination).

The rejection removes the faint stars with an undefined flux, which made up 18% of the top 50 before.

Sensitivity check: re-running the models only on the stars that pass criteria 1–4 changes the robust scaling and the
neighbours. The first 50 survivors of that ranking share 36 of 50 with the candidates.

The candidates are still candidates. Many will be known variable stars (eclipsing binaries, flare stars); the
cross-match is PHASE 4.

## Cross-match, systematics and persistence (PHASE 4)

Code: `src/vdxtess/crossmatch.py` (pure functions, tested without network) and `scripts/fase4.py`
(queries, cache, other-sector downloads). Parameters: `[crossmatch]` in `config/pipeline.toml`.

**Catalogues.** For each candidate:

| Catalogue | Access | Joined by |
|---|---|---|
| SIMBAD (`otype`, `V`) | astroquery 0.4.11, cone of 42" | nearest object within 5" |
| VSX (`B/vsx/vsx`) | VizieR, cone of 42" | nearest object within 5" |
| TOI (ExoFOP) | `data/catalogs/toi_exofop.csv`, downloaded 2026-10-26 | TIC ID |
| TESS eclipsing binaries (Prša et al. 2022, `J/ApJS/258/16`, sectors 1–26) | VizieR | TIC ID |

Every answer, empty ones included, is cached per TIC in `data/catalogs/{simbad,vsx,tess_eb}/`, and the query
time is in `data/catalogs/queries.json`. Re-runs reuse the cache, so the labels do not change when a
catalogue is updated. `--refresh` queries the catalogues again.

**Label** (`catalog_label`), for the event that drives the score (`dip`, `flare` or `bls`):

- `noto`: a catalogue gives the target a class that explains the event.
  - Dip and BLS: SIMBAD EB\*, Or\*, TT\*, Y\*O, Ae\*, Pl; VSX types E\* (except ELL), UXOR, IN\*, \*TTS,
    YSO, DIP; any TOI; any TESS EB.
  - Flare: SIMBAD Fl\*, Er\*, BY\*, RS\*, TT\*, Or\*, Y\*O, CV\*, No\*; VSX UV, FLARE, BY, RS, IN\*,
    \*TTS, YSO, UG, NL, N, ZAND, CV.
  - SIMBAD candidate classes (`EB?`, `Y*?`, `V*?`) count as the class. VSX compound types (`EA/DM`,
    `BY+UV`, `ROT:`) are split, and the `:` uncertainty mark is ignored.
- `noto con classe diversa`: the target has a variability class, but that class does not explain the event.
  An example is a rotator (ROT) with a dip.
- `assente`: no variability class in any of the four catalogues. The target can still appear as a plain
  star (`*`, `PM*`, `SB*`, `s*b`, `Em*`...).

A known variable star farther than 5" but within 42" (2 TESS pixels) is not the target, but it can
contaminate the aperture. It is listed in `variabile_vicina`.

**Coincident events (systematics).** For each dip or flare, the code counts the other stars on the same
camera/CCD whose strongest event of the same type falls within ±0.05 d. That count is compared with a
Poisson expectation: λ = (events on the CCD) × 2 × 0.05 d / (time span). With p < 0.001 the event is
`sospetto_sistematica`. The probability does not depend on the size of the population, so the same
threshold holds for the sample and for all targets.

**Persistence.** The other SPOC sectors of each candidate (up to `persistence_sectors_max`, from
`data/overlap_s103.csv`) are downloaded as 2-min light curves to `data/cache/persistence/`. 20-s targets
also have the 2-min product. Each curve is cleaned and its features recomputed with the same parameters as
sector 103. The labels are:

- `persistente`: the same event type is detected with SNR ≥ 10 in at least one other sector.
- `non persistente`: other sectors exist, but none of them has such a detection.
- `persistenza non verificabile`: there is no other sector, or none is readable. These candidates are kept
  and reported separately.

Other-sector products used on the sample: 190 curves with 0 errors, SPOC spoc-5.0.9-20200827 to
spoc-5.0.126-20251212, data releases 38–142. Sectors 105–107 are not used. They are noted for a v2.

**Sample results** (50 candidates, parameters fingerprint `b8cb320b43cbd27f`):

| | noto | noto con classe diversa | assente |
|---|---|---|---|
| dip | 24 | 7 | 5 |
| flare | 7 | 6 | 1 |
| total | 31 | 13 | 6 |

- Persistence: 44 persistente, 3 non persistente, 3 persistenza non verificabile.
- 0 `sospetto_sistematica`; 14 with a known variable star within 42".
- The TESS EB catalogue changes two candidates from `assente` to `noto`: TIC 133701671 (P = 4.70 d) and
  TIC 382308684 (P = 9.07 d).

The 6 `assente` candidates are not in SIMBAD, VSX, TOI or the TESS EB catalogue as variables. They are
**candidates, not discoveries**:

| rank | TIC | event | SIMBAD | Tmag | persistence | note |
|---|---|---|---|---|---|---|
| 2 | 292292315 | dip | HD 170312 | 8.29 | persistente | |
| 31 | 149064422 | flare | Gaia DR3 6007435426246132736 | 12.18 | non verificabile | no other sector |
| 37 | 469974264 | dip | — | 11.90 | persistente | no SIMBAD object within 5" |
| 45 | 410151515 | dip | HD 214554 | 8.31 | persistente | |
| 47 | 142329176 | dip | HD 137217 | 8.61 | persistente | |
| 81 | 138188560 | dip | HD 136505 | 5.67 | persistente | variables at 15" (ROT) and 37" (DSCT\|GDOR\|SXPHE) |

Five of the six are bright stars with dips that persist across sectors. The most likely explanation is
eclipsing binaries that have not yet been catalogued, or that are listed in catalogues not queried here.
For TIC 138188560, the 15" neighbour also has to be excluded as the source.

## Usage

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[test]"
.venv/bin/python -m pytest

.venv/bin/python scripts/sector_overlap.py    # persistence: other sectors per TIC
.venv/bin/python scripts/fase1.py --sample    # development sample
.venv/bin/python scripts/fase1.py --all       # final run, only with frozen = true
.venv/bin/python scripts/fase2.py --sample    # features on the cleaned curves
.venv/bin/python scripts/fase3.py --sample    # models, ranking, plots of the top 50
.venv/bin/python scripts/artefatti.py --sample  # artifact rejection, counts, 50 candidates with plots
.venv/bin/python scripts/fase4.py --sample      # cross-match SIMBAD/VSX/TOI/TESS EB, coincidences, persistence
.venv/bin/python scripts/fase5.py --sample --dry-run  # Core messages to data/outbox/, nothing sent
.venv/bin/python scripts/fase5.py --sample      # register dataset, run and candidates in VDX Core
```

Downloaded light curves (`data/cache/lc/`, ~1.9 MB each, ~25 GB total) and cleaned light curves
(`data/cache/clean/`, parquet) are stored in local cache and not tracked in the repository.

## VDX Core (PHASE 5)

`scripts/fase5.py` registers the pipeline in the VDX Core Research module via `vdx-core-client`.
It reads `VDX_CORE_URL`, `VDX_TOKEN` (project source token, from `scripts/create-research-source.ts`
in Core) and `PROJECT_ID` from the environment or from the repository's `.env` (not tracked).
Earlier phases never send anything: PHASE 1 only writes the Dataset message to `data/outbox/`.

What is sent, in order:

1. **Dataset** (`custom.dataset`, external ID `tess-s103-spoc-2min-dr141`): sector, data release,
   SPOC version, number of curves and size. If Core rejects it, the run is linked to the project only
   and the dataset must be created from the console with that external ID.
2. **Run** (`custom.run` event): git commit, all parameters of `config/pipeline.toml`, number of
   stars analysed (curves with features), total duration of PHASES 1-4, outcome (`ok`, or `partial`
   if some curves or other-sector downloads failed). The key is
   `<commit>:<params fingerprint>:S<sector>:<sample|all>`.
3. **Results** (`custom.result`, external ID `s103-tic-<TIC>`): one per candidate, with the score
   (combined percentile rank), the catalog reference (`known` / `known_other` / `absent`), the run id,
   a note (driving event, catalogs, systematics, persistence) and the candidate plot attached.
   `review` is only a default (`to_review`): re-sending never overwrites a review done in Core.

Re-running is idempotent: objects are matched by external ID, the run by key and attachments by
content, so nothing is duplicated. The final run on all targets updates the results of the
sample candidates with the same TIC and links them to the new run. The script refuses to send
from a working tree with uncommitted changes (the commit hash must identify the code) or if the
parameters changed after any phase. A log of each send is written to `data/runs/`.

macOS note: if the repository resides in a folder synced with iCloud (Desktop), the editable installation's
`.pth` file receives the `hidden` attribute flag and Python 3.12 ignores it. For this reason,
the scripts and pytest automatically add `src/` to `sys.path`.

## Phases

- PHASE 0: literature review, `docs/literature.md`
- PHASE 1: data, cleaning, cache, Core Dataset
- PHASE 2: per-TIC features and artifact diagnostics
- PHASE 3: Isolation Forest and LOF, comparison, ranking, plots
- Artifact rejection: explicit criteria, counts per criterion, candidates
- PHASE 4: SIMBAD/VSX/TOI/TESS EB cross-match, coincident events, persistence
- PHASE 5: registration in VDX Core (dataset, run, results with plots)
