"""Scarto esplicito degli artefatti sul ranking della FASE 3, con il conteggio per criterio.

Uso:
  python scripts/artefatti.py --sample   # campione di sviluppo
  python scripts/artefatti.py --all      # tutti i target (solo con frozen = true)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import artifacts, config, plots
from vdxtess.models import rank

DATA = config.ROOT / "data"
TOPS = [50, 300]
STAR_CRITERIA = ["flusso_indefinito", "contaminazione", "sistematica_centroide", "sistematica_fondo"]


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
    p, top_n = cfg["artifacts"], cfg["models"]["top_n"]

    t0 = time.time()
    r = pd.read_csv(DATA / f"ranking_s{sector:03d}_{label}.csv")
    out = artifacts.apply(r, p)
    out.to_csv(DATA / f"artifacts_s{sector:03d}_{label}.csv", index=False, float_format="%.6g")
    c = artifacts.counts(out, p, TOPS)
    c.to_csv(DATA / f"artifact_counts_s{sector:03d}_{label}.csv", index=False)
    cand = out[out.artifact_reason == ""].head(top_n)
    cand.to_csv(DATA / f"candidates_s{sector:03d}_{label}.csv", index=False, float_format="%.6g")

    # sensibilità: ripetere i modelli solo sulle stelle che passano i criteri sulla stella cambia
    # la scala robusta e i vicini; quanti candidati restano gli stessi?
    keep = ~out.artifact_reason.isin(STAR_CRITERIA)
    r2, _ = rank(r[keep].drop(columns=["rank", "score_if", "score_lof", "prank_if", "prank_lof",
                                       "prank_combined", "drivers"]).reset_index(drop=True), cfg["models"])
    cand2 = artifacts.apply(r2, p).query("artifact_reason == ''").head(top_n)
    shared = len(set(cand.tic) & set(cand2.tic))

    summary = {"curves": len(out), "candidates": len(cand), "rerank_on_star_survivors_shared": shared,
               "duration_s": round(time.time() - t0, 1), "params_fingerprint": config.fingerprint(cfg)}
    config.save_summary("artefatti", sector, label, summary)
    print("scarto:", json.dumps(summary, indent=1))
    print(c.drop(columns="description").to_string(index=False))
    cols = ["rank", "tic", "tmag_hdr", "event", "warnings", "drivers"]
    print(cand[cols].to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    if a.no_plots:
        return
    clean = DATA / "cache" / "clean" / f"s{sector:04d}"
    pdir = DATA / "plots" / f"s{sector:03d}_{label}_candidati"
    pdir.mkdir(parents=True, exist_ok=True)
    for i, (_, row) in enumerate(cand.iterrows(), 1):
        d = pd.read_parquet(clean / f"tic{row.tic}.parquet")
        warn = f"  avvisi: {row.warnings}" if row.warnings else ""
        title = (f"candidato {i} (rango {row['rank']})  TIC {row.tic}  Tmag {row.tmag_hdr:.2f}  settore {sector}"
                 f"{warn}\n{row.drivers}")
        plots.candidate(d, row, cfg["features"], pdir / f"{i:03d}_tic{row.tic}.png", title)
    print(f"grafici: {len(cand)} in {pdir}")


if __name__ == "__main__":
    main()
