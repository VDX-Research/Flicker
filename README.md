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

## Usage

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[test]"
.venv/bin/python -m pytest

.venv/bin/python scripts/sector_overlap.py    # persistence: other sectors per TIC
.venv/bin/python scripts/fase1.py --sample    # development sample
.venv/bin/python scripts/fase1.py --all       # final run, only with frozen = true
.venv/bin/python scripts/fase2.py --sample    # features on the cleaned curves
```

Downloaded light curves (`data/cache/lc/`, ~1.9 MB each, ~25 GB total) and cleaned light curves
(`data/cache/clean/`, parquet) are stored in local cache and not tracked in the repository.

## VDX Core

Results are ingested into the VDX Core Research module via `vdx-core-client`. With the environment
variables `VDX_CORE_URL` and `VDX_TOKEN` (project source token, from
`scripts/create-research-source.ts` in Core), messages are dispatched; without them, they are written to
`data/outbox/` and can be sent later: ingestion is idempotent (objects by external ID,
executions by key).

macOS note: if the repository resides in a folder synced with iCloud (Desktop), the editable installation's
`.pth` file receives the `hidden` attribute flag and Python 3.12 ignores it. For this reason,
the scripts and pytest automatically add `src/` to `sys.path`.

## Phases

- PHASE 0: literature review, `docs/literature.md`
- PHASE 1: data, cleaning, cache, Core Dataset
- PHASE 2: per-TIC features and artifact diagnostics
