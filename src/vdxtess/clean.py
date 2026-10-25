"""Pulizia delle curve PDCSAP: flag di qualità, valori non finiti, buchi, normalizzazione.

Niente detrending né sigma-clipping: toglierebbero proprio i segnali anomali che cerchiamo.
Le colonne di centroide, fondo e QUALITY restano, servono alla fase di scarto degli artefatti.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits

HEADER_KEYS = {"TESSMAG": "tmag_hdr", "TEFF": "teff", "RADIUS": "radius", "RA_OBJ": "ra", "DEC_OBJ": "dec",
               "CAMERA": "camera", "CCD": "ccd"}
LC_KEYS = {"CROWDSAP": "crowdsap", "FLFRCSAP": "flfrcsap", "CDPP0_5": "cdpp0_5", "CDPP1_0": "cdpp1_0",
           "CDPP2_0": "cdpp2_0", "TSTART": "tstart", "TSTOP": "tstop"}
COLUMNS = ["TIME", "PDCSAP_FLUX", "PDCSAP_FLUX_ERR", "SAP_FLUX", "SAP_BKG", "QUALITY",
           "MOM_CENTR1", "MOM_CENTR2", "POS_CORR1", "POS_CORR2"]


def read_lc(path: Path) -> tuple[pd.DataFrame, dict]:
    with fits.open(path, memmap=False) as h:
        p, e = h[0].header, h[1].header
        meta = {v: p.get(k) for k, v in HEADER_KEYS.items()} | {v: e.get(k) for k, v in LC_KEYS.items()}
        meta["tic"] = int(p["TICID"])
        d = h[1].data
        df = pd.DataFrame({c.lower(): np.asarray(d[c]).astype(np.float64 if c != "QUALITY" else np.int32)
                           for c in COLUMNS})
    return df, meta


def segments(time: np.ndarray, gap_days: float) -> np.ndarray:
    """Indice di segmento per ogni punto (time ordinato): un buco > gap_days apre un segmento nuovo."""
    return np.concatenate([[0], np.cumsum(np.diff(time) > gap_days)]).astype(np.int32)


def clean(df: pd.DataFrame, bitmask: int, gap_days: float, min_segment_days: float,
          min_points: int) -> tuple[pd.DataFrame | None, dict]:
    """Curva pulita (o None se troppo corta) e conteggio dei punti tolti da ogni passo.

    Passi, in ordine: (1) cadenze con un bit di `bitmask` in QUALITY; (2) tempo o flusso non
    finiti; (3) segmenti più brevi di min_segment_days. Poi ogni segmento è diviso per la sua
    mediana (flusso relativo, ~1) e la curva è esclusa se restano meno di min_points punti."""
    n = {"n_raw": len(df)}
    d = df[(df.quality & bitmask) == 0]
    n["drop_quality"] = n["n_raw"] - len(d)
    ok = np.isfinite(d.time) & np.isfinite(d.pdcsap_flux) & np.isfinite(d.pdcsap_flux_err)
    n["drop_nonfinite"] = int((~ok).sum())
    d = d[ok].sort_values("time").reset_index(drop=True)
    d["segment"] = segments(d.time.to_numpy(), gap_days)
    span = d.groupby("segment").time.agg(lambda t: t.max() - t.min())
    keep = span.index[span >= min_segment_days]
    before = len(d)
    d = d[d.segment.isin(keep)].copy()
    n["drop_short_segment"] = before - len(d)
    d["segment"] = segments(d.time.to_numpy(), gap_days)
    n["n_segments"] = int(d.segment.nunique())
    n["n_clean"] = len(d)
    if len(d) < min_points:
        n["excluded"] = "too_few_points"
        return None, n
    med = d.groupby("segment").pdcsap_flux.transform("median")
    if (med <= 0).any():
        n["excluded"] = "nonpositive_median"
        return None, n
    d["flux"] = d.pdcsap_flux / med
    d["flux_err"] = d.pdcsap_flux_err / med
    n["excluded"] = ""
    return d, n


def clean_file(path: Path, out_dir: Path, p: dict) -> dict:
    """Pulisce un file e salva la curva in parquet; restituisce metadati e conteggi."""
    df, meta = read_lc(path)
    d, n = clean(df, p["quality_bitmask"], p["gap_days"], p["min_segment_days"], p["min_points"])
    if d is not None:
        cols = ["time", "flux", "flux_err", "segment", "quality", "sap_flux", "sap_bkg",
                "mom_centr1", "mom_centr2", "pos_corr1", "pos_corr2"]
        d[cols].to_parquet(out_dir / f"tic{meta['tic']}.parquet", index=False)
    return meta | n | {"file": path.name}
