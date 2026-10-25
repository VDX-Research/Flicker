"""FASE 2: caratteristiche per TIC sulle curve pulite della FASE 1.

Uso:
  python scripts/fase2.py --sample   # campione di sviluppo
  python scripts/fase2.py --all      # tutti i target (solo con frozen = true)
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import config
from vdxtess.features import MODEL_FEATURES, features

DATA = config.ROOT / "data"
# metadati della FASE 1 portati nella tabella delle caratteristiche
META = ["tic", "tmag_hdr", "teff", "radius", "ra", "dec", "camera", "ccd", "crowdsap", "flfrcsap", "cdpp1_0"]


def _features(args):
    path, p = args
    try:
        return features(pd.read_parquet(path), p)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    cfg = config.load()
    sector = cfg["dataset"]["sector"]
    if a.all and not cfg["frozen"]:
        sys.exit("parametri non congelati: imposta frozen = true in config/pipeline.toml prima della corsa finale")
    label = "sample" if a.sample else "all"

    meta = pd.read_csv(DATA / f"clean_s{sector:03d}_{label}.csv")
    meta = meta[meta.excluded.fillna("") == ""]
    clean = DATA / "cache" / "clean" / f"s{sector:04d}"
    jobs = [(clean / f"tic{t}.parquet", cfg["features"]) for t in meta.tic]
    print(f"curve pulite: {len(jobs)}")

    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(_features, jobs, chunksize=10))
    f = pd.concat([meta[META].reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    if "error" not in f.columns:
        f["error"] = pd.NA
    out = DATA / f"features_s{sector:03d}_{label}.csv"
    f.to_csv(out, index=False, float_format="%.6g")

    ok = f[f.error.isna()]
    summary = {"curves": len(f), "ok": len(ok), "errors": int(f.error.notna().sum()),
               "nonfinite_model_features": int((~np.isfinite(ok[MODEL_FEATURES].astype(float))).any(axis=1).sum()),
               "duration_s": round(time.time() - t0, 1), "params_fingerprint": config.fingerprint(cfg)}
    print("caratteristiche:", json.dumps(summary, indent=1))
    print(f"scritto {out}")
    q = ok[MODEL_FEATURES].describe(percentiles=[0.01, 0.5, 0.99]).T[["1%", "50%", "99%", "max"]]
    print(q.to_string(float_format=lambda x: f"{x:.4g}"))


if __name__ == "__main__":
    main()
