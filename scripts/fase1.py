"""FASE 1: target del settore, campione di sviluppo, scarico, pulizia, registrazione del Dataset.

Uso:
  python scripts/fase1.py --sample   # campione stratificato di sviluppo (~3k)
  python scripts/fase1.py --all      # tutti i target (solo con frozen = true)
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import config, core
from vdxtess.clean import clean_file
from vdxtess.download import download
from vdxtess.sample import stratified_sample
from vdxtess.targets import sector_targets, tic_magnitudes

DATA = config.ROOT / "data"


def targets(sector: int, cadence: int) -> pd.DataFrame:
    path = DATA / f"targets_s{sector:03d}.csv"
    if path.exists():
        return pd.read_csv(path)
    t = sector_targets(sector, cadence)
    t = t.merge(tic_magnitudes(t.tic.tolist()), on="tic", how="left")
    t.to_csv(path, index=False)
    return t


def _clean(args):
    path, out, p = args
    try:
        return clean_file(path, out, p)
    except Exception as e:
        return {"file": path.name, "excluded": f"error: {e}"}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    cfg = config.load()
    ds, cl = cfg["dataset"], cfg["clean"]
    sector = ds["sector"]
    if a.all and not cfg["frozen"]:
        sys.exit("parametri non congelati: imposta frozen = true in config/pipeline.toml prima della corsa finale")

    t0 = time.time()
    t = targets(sector, ds["cadence_s"])
    print(f"target S{sector} a {ds['cadence_s']} s: {len(t)} (senza Tmag: {t.tmag.isna().sum()})")
    if a.sample:
        s = cfg["sample"]
        t = stratified_sample(t, s["size"], s["seed"], s["tmag_edges"])
        t.to_csv(DATA / f"sample_s{sector:03d}.csv", index=False)
        print(f"campione: {len(t)} target, per classe di Tmag: {t.stratum.value_counts().sort_index().tolist()}")
    label = "sample" if a.sample else "all"

    cache = DATA / "cache" / "lc" / f"s{sector:04d}"
    m = download(t, sector, cache, ds["data_release"], a.workers)
    err = m[m.error.notna()] if "error" in m.columns else m.iloc[:0]
    m.to_csv(DATA / f"manifest_s{sector:03d}_{label}.csv", index=False)
    print(f"scaricati/verificati: {len(m) - len(err)}, errori: {len(err)}")

    out = DATA / "cache" / "clean" / f"s{sector:04d}"
    out.mkdir(parents=True, exist_ok=True)
    ok = m.drop(index=err.index)
    jobs = [(cache / f, out, cl) for f in ok.file]
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(_clean, jobs, chunksize=50))
    meta = pd.DataFrame(rows)
    meta.to_csv(DATA / f"clean_s{sector:03d}_{label}.csv", index=False)
    kept = meta[meta.excluded.fillna("") == ""]
    summary = {k: int(meta[k].sum()) for k in ("n_raw", "drop_quality", "drop_nonfinite", "drop_short_segment", "n_clean")}
    summary["curves_in"] = len(meta)
    summary["curves_kept"] = len(kept)
    summary["excluded"] = meta.excluded.fillna("").replace("", pd.NA).dropna().value_counts().to_dict()
    summary["n_files"], summary["bytes"] = len(ok), int(ok.bytes.sum())

    # versioni dei prodotti e date di scarico: vanno nel README e nel report
    ok = ok.astype({"data_rel": int})
    products = {
        "sector": sector, "cadence_s": ds["cadence_s"],
        "data_release": sorted(ok.data_rel.unique().tolist()),
        "spoc_version": sorted(ok.procver.unique().tolist()),
        "file_date": sorted(ok.file_date.unique().tolist()),
        "downloaded_from": ok.downloaded_at.min(), "downloaded_to": ok.downloaded_at.max(),
        "n_files": len(ok), "bytes": int(ok.bytes.sum()),
        "quality_bitmask": cl["quality_bitmask"], "params_fingerprint": config.fingerprint(cfg),
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (DATA / f"products_s{sector:03d}_{label}.json").write_text(json.dumps(products, indent=2))
    print("prodotti:", json.dumps({k: products[k] for k in ("data_release", "spoc_version", "downloaded_from", "downloaded_to")}))

    if len(products["spoc_version"]) == 1:
        msg = core.dataset_message(sector, ds["data_release"], products["spoc_version"][0], len(ok), products["bytes"])
        print("dataset (outbox, lo invia la FASE 5):", core.write_outbox([msg], f"dataset_s{sector:03d}"))

    summary |= {"duration_s": round(time.time() - t0, 1), "params_fingerprint": products["params_fingerprint"]}
    config.save_summary("fase1", sector, label, summary)
    print("pulizia:", json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
