"""FASE 6: report per l'astronomo.

Legge i riepiloghi delle fasi 1-5, i prodotti scaricati, le date delle interrogazioni ai cataloghi e le
tabelle dei candidati, e scrive reports/report_s<settore>_<selezione>.md (in inglese). I grafici dei
candidati assenti dai cataloghi e di quelli con persistenza non verificabile sono copiati in
reports/figures/, così il report si legge anche senza data/ (che non è nel repository).

Uso:
  python scripts/fase6.py --sample   # campione di sviluppo
  python scripts/fase6.py --all      # tutti i target (solo con frozen = true)
"""
import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import config, core, report

DATA = config.ROOT / "data"
REPORTS = config.ROOT / "reports"
PHASES = ("fase1", "fase2", "fase3", "artefatti", "fase4")


def summaries(sector: int, label: str) -> dict:
    out = {}
    for ph in PHASES + ("fase5",):
        p = DATA / f"summary_{ph}_s{sector:03d}_{label}.json"
        if p.exists():
            out[ph] = json.loads(p.read_text())
        elif ph != "fase5":  # la registrazione in Core è facoltativa per il report
            sys.exit(f"manca {p.relative_to(config.ROOT)}: esegui prima scripts/{ph}.py --{label}")
    return out


def query_window(tics: set[int]) -> dict[str, tuple[str, str]]:
    """Prima e ultima interrogazione per catalogo, ristrette ai TIC dei candidati."""
    q = json.loads((DATA / "catalogs" / "queries.json").read_text())
    out = {}
    for cat, per_tic in q.items():
        ts = sorted(v for k, v in per_tic.items() if int(k) in tics)
        if ts:
            out[cat] = (ts[0].replace("+00:00", "Z"), ts[-1].replace("+00:00", "Z"))
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    a = ap.parse_args()

    cfg = config.load()
    sector = cfg["dataset"]["sector"]
    if a.all and not cfg["frozen"]:
        sys.exit("parametri non congelati: imposta frozen = true in config/pipeline.toml prima della corsa finale")
    label = "sample" if a.sample else "all"
    t0 = time.time()

    s = summaries(sector, label)
    fp = config.fingerprint(cfg)
    stale = [ph for ph, v in s.items() if v.get("params_fingerprint") != fp]
    if stale:
        sys.exit(f"parametri cambiati dopo {', '.join(stale)}: rilancia la pipeline prima del report")

    products = json.loads((DATA / f"products_s{sector:03d}_{label}.json").read_text())
    cand = pd.read_csv(DATA / f"crossmatch_s{sector:03d}_{label}.csv", keep_default_na=False,
                       na_values=["", "nan", "NaN"])
    counts = pd.read_csv(DATA / f"artifact_counts_s{sector:03d}_{label}.csv")

    # grafici dei candidati da guardare per primi, copiati accanto al report
    fig_dir = REPORTS / "figures" / f"s{sector:03d}_{label}"
    if fig_dir.exists():
        shutil.rmtree(fig_dir)
    fig_dir.mkdir(parents=True)
    figures = {}
    pick = cand[(cand.catalog_label == "assente") | (cand.persistence == "persistenza non verificabile")]
    for tic in pick.tic.astype(int):
        found = sorted((DATA / "plots" / f"s{sector:03d}_{label}_candidati").glob(f"*_tic{tic}.png"))
        if found:
            shutil.copy2(found[0], fig_dir / found[0].name)
            figures[tic] = f"figures/{fig_dir.name}/{found[0].name}"

    meta = {"sector": sector, "label": label, "frozen": cfg["frozen"], "fingerprint": fp,
            "commit": core.git_commit(),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "min_snr": cfg["crossmatch"]["persistence_min_snr"], "match_arcsec": cfg["crossmatch"]["match_radius_arcsec"],
            "neighbor_arcsec": cfg["crossmatch"]["neighbor_radius_arcsec"],
            "sectors_max": cfg["dataset"]["persistence_sectors_max"]}
    # accordo IF/LOF sul campione di sviluppo, per confrontarlo con la corsa finale nei limiti
    dev = DATA / f"summary_fase3_s{sector:03d}_sample.json"
    if label == "all" and dev.exists():
        meta["dev_fase3"] = json.loads(dev.read_text())
    md = report.build(s, products, cand, counts, query_window(set(cand.tic.astype(int))), meta, figures)
    out = REPORTS / f"report_s{sector:03d}_{label}.md"
    out.write_text(md + "\n")

    missing = sorted(set(pick.tic.astype(int)) - set(figures))
    config.save_summary("fase6", sector, label, {
        "report": str(out.relative_to(config.ROOT)), "figures": len(figures), "figures_missing": missing,
        "duration_s": round(time.time() - t0, 1), "params_fingerprint": fp})
    print(f"report: {out.relative_to(config.ROOT)} ({len(figures)} grafici" + (f", mancanti {missing}" if missing else "") + ")")


if __name__ == "__main__":
    main()
