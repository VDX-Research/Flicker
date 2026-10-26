"""FASE 4: confronto dei candidati con SIMBAD, VSX, TOI e le binarie a eclisse TESS, eventi coincidenti e persistenza.

Le interrogazioni in rete sono salvate in data/catalogs/ (una tabella per TIC, anche vuota) e
riusate alle corse successive: i numeri non cambiano se un catalogo si aggiorna, finché non si
passa --refresh. Le regole di etichettatura stanno in src/vdxtess/crossmatch.py.

Persistenza: per ogni candidato si scaricano le curve SPOC a 2 minuti degli altri settori fino a
persistence_sectors_max (i target a 20 s hanno anche il prodotto a 2 minuti), si puliscono e si
ricalcolano le caratteristiche con gli stessi parametri del settore 103.

Uso:
  python scripts/fase4.py --sample   # campione di sviluppo
  python scripts/fase4.py --all      # tutti i target (solo con frozen = true)
"""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import config, crossmatch
from vdxtess.clean import clean, read_lc
from vdxtess.download import fetch, header_versions, lc_url
from vdxtess.features import features

DATA = config.ROOT / "data"
CAT = DATA / "catalogs"
TOI_FILE = CAT / "toi_exofop.csv"
TESS_EB = "J/ApJS/258/16/tess-ebs"  # Prša et al. 2022, ApJS 258, 16
TOI_DOWNLOADED = "2026-10-26"  # https://exofop.ipac.caltech.edu/tess/download_toi.php?output=csv
# curva a 2 minuti di un solo settore: tess<data>-s<settore>-<tic a 16 cifre>-<n>-s
OBS_ID = re.compile(r"^tess\d{13}-s(\d{4})-(\d{16})-\d{4}-s$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _retry(fn, tries=3):
    for attempt in range(tries):
        try:
            return fn()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def query_simbad(c: SkyCoord, radius: float) -> pd.DataFrame:
    from astroquery.simbad import Simbad
    s = Simbad()
    s.add_votable_fields("otype", "V")
    r = _retry(lambda: s.query_region(c, radius=radius * u.arcsec))
    if r is None or len(r) == 0:
        return pd.DataFrame(columns=["main_id", "ra", "dec", "V", "otype", "sep_arcsec"])
    df = r["main_id", "ra", "dec", "V", "otype"].to_pandas()
    df["sep_arcsec"] = c.separation(SkyCoord(df.ra.to_numpy(), df.dec.to_numpy(), unit="deg")).arcsec
    return df


def query_vsx(c: SkyCoord, radius: float) -> pd.DataFrame:
    from astroquery.vizier import Vizier
    v = Vizier(columns=["Name", "Type", "Period", "RAJ2000", "DEJ2000", "max", "min"], row_limit=-1)
    r = _retry(lambda: v.query_region(c, radius=radius * u.arcsec, catalog="B/vsx/vsx"))
    if len(r) == 0 or len(r[0]) == 0:
        return pd.DataFrame(columns=["Name", "Type", "Period", "RAJ2000", "DEJ2000", "max", "min", "sep_arcsec"])
    df = r[0].to_pandas()
    df["sep_arcsec"] = c.separation(SkyCoord(df.RAJ2000.to_numpy(), df.DEJ2000.to_numpy(), unit="deg")).arcsec
    return df


def query_tess_eb(tic: int) -> pd.DataFrame:
    """Riga del catalogo di binarie a eclisse TESS (Prša et al. 2022, settori 1-26) per il TIC."""
    from astroquery.vizier import Vizier
    v = Vizier(columns=["TIC", "Per", "BJD0", "Morph"], row_limit=-1)
    r = _retry(lambda: v.query_constraints(catalog=TESS_EB, TIC=str(tic)))
    if len(r) == 0 or len(r[0]) == 0:
        return pd.DataFrame(columns=["TIC", "Per", "BJD0", "Morph"])
    return r[0].to_pandas()


def cached_query(kind: str, tic: int, c: SkyCoord, radius: float, refresh: bool, log: dict) -> pd.DataFrame:
    """Tabella del catalogo intorno al TIC: dalla cache se c'è, altrimenti interrogata e salvata."""
    d = CAT / kind
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"tic{tic}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, keep_default_na=False, na_values=[""])
    df = query_tess_eb(tic) if kind == "tess_eb" else (query_simbad if kind == "simbad" else query_vsx)(c, radius)
    df.to_csv(path, index=False)
    log.setdefault(kind, {})[str(tic)] = now()
    return df


def sector_obs(tics: list[int], sectors: set[int]) -> pd.DataFrame:
    """obs_id delle curve SPOC a 2 minuti di un solo settore per i TIC dati."""
    from astroquery.mast import Observations
    r = _retry(lambda: Observations.query_criteria(obs_collection="TESS", provenance_name="SPOC",
                                                   dataproduct_type="timeseries",
                                                   target_name=[str(t) for t in tics]))
    df = r["obs_id", "target_name", "t_exptime", "sequence_number"].to_pandas()
    m = df.obs_id.str.extract(OBS_ID)
    df = df[m[0].notna() & (df.t_exptime == 120)].copy()
    df["sector"] = df.sequence_number.astype(int)
    df["tic"] = df.target_name.astype(int)
    return df[df.sector.isin(sectors)].drop_duplicates(["tic", "sector"])[["tic", "sector", "obs_id"]]


def sector_features(job) -> dict:
    """Scarica (se manca), pulisce e misura una curva di un altro settore."""
    tic, sector, obs_id, cfg = job
    d = DATA / "cache" / "persistence" / f"s{sector:04d}"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{obs_id}_lc.fits"
    row = {"tic": tic, "sector": sector, "obs_id": obs_id}
    try:
        if not path.exists():
            fetch(lc_url(sector, tic, obs_id), path)
        row |= header_versions(path)
        df, _ = read_lc(path)
        c = cfg["clean"]
        lc, n = clean(df, c["quality_bitmask"], c["gap_days"], c["min_segment_days"], c["min_points"])
        if lc is None:
            return row | {"error": f"esclusa in pulizia: {n['excluded']}"}
        f = features(lc, cfg["features"])
        keep = ["n_points", "n_dips", "dip_depth", "dip_snr", "t_dip", "n_flares", "flare_amp", "flare_snr",
                "t_flare", "bls_period", "bls_depth", "bls_snr", "ls_period", "ls_amp"]
        return row | {k: f.get(k, np.nan) for k in keep} | {"error": np.nan}
    except Exception as e:
        return row | {"error": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="interroga di nuovo SIMBAD, VSX e il catalogo EB TESS")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    cfg = config.load()
    sector = cfg["dataset"]["sector"]
    if a.all and not cfg["frozen"]:
        sys.exit("parametri non congelati: imposta frozen = true in config/pipeline.toml prima della corsa finale")
    label = "sample" if a.sample else "all"
    p, max_sector = cfg["crossmatch"], cfg["dataset"]["persistence_sectors_max"]

    t0 = time.time()
    cand = pd.read_csv(DATA / f"candidates_s{sector:03d}_{label}.csv", keep_default_na=False,
                       na_values=["", "nan", "NaN"])
    cand["event"] = cand.event.fillna("")
    pop = pd.read_csv(DATA / f"features_s{sector:03d}_{label}.csv")
    if "error" in pop.columns:
        pop = pop[pop.error.isna()]
    toi = pd.read_csv(TOI_FILE, comment="#")
    overlap = pd.read_csv(DATA / f"overlap_s{sector:03d}.csv").set_index("tic").other_sectors

    # 1. cataloghi
    log_path = CAT / "queries.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    labels = []
    for _, r in cand.iterrows():
        c = SkyCoord(r.ra, r.dec, unit="deg")
        s = cached_query("simbad", r.tic, c, p["neighbor_radius_arcsec"], a.refresh, log)
        v = cached_query("vsx", r.tic, c, p["neighbor_radius_arcsec"], a.refresh, log)
        e = cached_query("tess_eb", r.tic, c, 0, a.refresh, log)
        labels.append({"tic": r.tic} | crossmatch.label(r.event, s, v, toi[toi["TIC ID"] == r.tic], p, e))
    log_path.write_text(json.dumps(log, indent=1, sort_keys=True))
    out = cand.merge(pd.DataFrame(labels), on="tic").merge(crossmatch.coincidences(cand, pop, p), on="tic")

    # 2. persistenza sugli altri settori
    others = {t: crossmatch.other_sectors(overlap.get(t), sector, max_sector) for t in cand.tic}
    want = {s for v in others.values() for s in v}
    obs = sector_obs([t for t, v in others.items() if v], want) if want else pd.DataFrame(columns=["tic", "sector", "obs_id"])
    obs = obs[[s in others[t] for t, s in zip(obs.tic, obs.sector)]]
    jobs = [(int(r.tic), int(r.sector), r.obs_id, cfg) for r in obs.itertuples()]
    with ThreadPoolExecutor(a.workers) as ex:
        per = pd.DataFrame(list(ex.map(sector_features, jobs)))
    if per.empty:
        per = pd.DataFrame(columns=["tic", "sector", "error"])
    per.sort_values(["tic", "sector"]).to_csv(DATA / f"persistence_s{sector:03d}_{label}.csv", index=False,
                                              float_format="%.6g")
    pers = [{"tic": r.tic, "other_sectors": " ".join(map(str, others[r.tic]))}
            | crossmatch.persistence(r.event, others[r.tic], per[per.tic == r.tic], p) for _, r in cand.iterrows()]
    out = out.merge(pd.DataFrame(pers), on="tic")
    out.to_csv(DATA / f"crossmatch_s{sector:03d}_{label}.csv", index=False, float_format="%.6g")

    versions = per.dropna(subset=["procver"]) if "procver" in per.columns else per.iloc[:0]
    summary = {
        "candidates": len(out),
        "catalog_label": out.catalog_label.value_counts().to_dict(),
        "persistence": out.persistence.value_counts().to_dict(),
        "sospetto_sistematica": int(out.sospetto_sistematica.sum()),
        "variabile_vicina": int((out.variabile_vicina != "").sum()),
        "assente_by_persistence": out[out.catalog_label == "assente"].persistence.value_counts().to_dict(),
        "other_sector_curves": len(per), "other_sector_errors": int(per.error.notna().sum()),
        "other_sector_spoc": sorted(versions.procver.unique().tolist()),
        "other_sector_data_rel": sorted(int(x) for x in versions.data_rel.unique()),
        "toi_table_downloaded": TOI_DOWNLOADED,
        "duration_s": round(time.time() - t0, 1), "params_fingerprint": config.fingerprint(cfg),
    }
    print("confronto:", json.dumps(summary, indent=1, ensure_ascii=False))
    cols = ["rank", "tic", "event", "catalog_label", "catalog_explains", "simbad_otype", "vsx_type",
            "coinc_n", "sospetto_sistematica", "persistence"]
    print(out[cols].to_string(index=False, float_format=lambda x: f"{x:.2g}"))


if __name__ == "__main__":
    main()
