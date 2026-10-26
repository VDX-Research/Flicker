"""FASE 3: due metodi unsupervised, confronto, ranking e grafici dei primi top_n.

Uso:
  python scripts/fase3.py --sample   # campione di sviluppo
  python scripts/fase3.py --all      # tutti i target (solo con frozen = true)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import config, plots
from vdxtess.models import rank

DATA = config.ROOT / "data"
TMAG_BINS = [0, 10, 13, 16, 18, 21]


def composition(top: pd.DataFrame, allr: pd.DataFrame, edge_d: float) -> dict:
    """Di che cosa è fatto il gruppo dei primi: magnitudine ed eventi ai bordi, contro il totale."""
    def tmag(x):
        return pd.cut(x.tmag_hdr, TMAG_BINS).value_counts(normalize=True).sort_index().round(3)

    def edge(x):
        near = (x.diag_dip_edge_d < edge_d) | (x.diag_flare_edge_d < edge_d)
        return round(float(near.mean()), 3)

    return {"tmag_top": {str(k): v for k, v in tmag(top).items()},
            "tmag_all": {str(k): v for k, v in tmag(allr).items()},
            f"event_within_{edge_d:g}d_of_edge_top": edge(top),
            f"event_within_{edge_d:g}d_of_edge_all": edge(allr)}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--no-plots", action="store_true")
    a = ap.parse_args()

    cfg = config.load()
    sector = cfg["dataset"]["sector"]
    if a.all and not cfg["frozen"]:
        sys.exit("parametri non congelati: imposta frozen = true in config/pipeline.toml prima della corsa finale")
    label = "sample" if a.sample else "all"
    p = cfg["models"]

    f = pd.read_csv(DATA / f"features_s{sector:03d}_{label}.csv")
    f = f[f.error.isna()].reset_index(drop=True)
    t0 = time.time()
    r, cmp = rank(f, p)
    out = DATA / f"ranking_s{sector:03d}_{label}.csv"
    r.to_csv(out, index=False, float_format="%.6g")

    top = r.head(p["top_n"])
    summary = {"curves": len(r), **cmp, **composition(top, r, 0.1),
               "duration_s": round(time.time() - t0, 1), "params_fingerprint": config.fingerprint(cfg)}
    config.save_summary("fase3", sector, label, summary)
    print("modelli:", json.dumps(summary, indent=1))
    print(f"scritto {out}")
    cols = ["rank", "tic", "tmag_hdr", "prank_if", "prank_lof", "drivers"]
    print(top[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    if a.no_plots:
        return
    clean = DATA / "cache" / "clean" / f"s{sector:04d}"
    pdir = DATA / "plots" / f"s{sector:03d}_{label}"
    pdir.mkdir(parents=True, exist_ok=True)
    for _, row in top.iterrows():
        d = pd.read_parquet(clean / f"tic{row.tic}.parquet")
        title = (f"#{row['rank']}  TIC {row.tic}  Tmag {row.tmag_hdr:.2f}  settore {sector}  "
                 f"IF {row.prank_if:.3f}  LOF {row.prank_lof:.3f}\n{row.drivers}")
        plots.candidate(d, row, cfg["features"], pdir / f"{row['rank']:03d}_tic{row.tic}.png", title)
    print(f"grafici: {len(top)} in {pdir}")


if __name__ == "__main__":
    main()
