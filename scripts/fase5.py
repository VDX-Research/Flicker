"""FASE 5: registrazione in VDX Core (modulo Research) di dataset, esecuzione e candidati.

Ordine degli invii:
1. il Dataset (custom.dataset) scritto dalla FASE 1 in data/outbox/;
2. l'Esecuzione (evento custom.run) con commit, parametri, stelle analizzate, durata ed esito;
3. un Risultato (custom.result) per candidato, legato all'esecuzione, con il grafico allegato.

Gli invii ripetuti non duplicano: il dataset e i risultati sono riconosciuti per externalId,
l'esecuzione per key (commit, impronta dei parametri, settore, selezione), i grafici per contenuto.
Il token del progetto non può creare il dataset (va creato dalla console Research con lo stesso
externalId), ma può collegarlo: se il collegamento fallisce l'esecuzione è legata solo al progetto.
Se Core rifiuta `extra` dei risultati, si inviano senza.

Uso:
  python scripts/fase5.py --sample [--dry-run]   # campione di sviluppo
  python scripts/fase5.py --all [--dry-run]      # tutti i target (solo con frozen = true)
--dry-run scrive i messaggi in data/outbox/ senza inviare nulla.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# src/ esplicito: in una cartella sincronizzata con iCloud il .pth editable viene nascosto e ignorato
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vdxtess import config, core

DATA = config.ROOT / "data"
PHASES = ("fase1", "fase2", "fase3", "artefatti", "fase4")


def summaries(sector: int, label: str) -> dict:
    out = {}
    for ph in PHASES:
        p = DATA / f"summary_{ph}_s{sector:03d}_{label}.json"
        if not p.exists():
            sys.exit(f"manca {p.relative_to(config.ROOT)}: esegui prima scripts/{ph}.py --{label}")
        out[ph] = json.loads(p.read_text())
    return out


def plot_for(sector: int, label: str, tic: int) -> Path | None:
    found = sorted((DATA / "plots" / f"s{sector:03d}_{label}_candidati").glob(f"*_tic{tic}.png"))
    return found[0] if found else None


def rejected(res: dict) -> dict[int, str]:
    return {x["index"]: str(x.get("error")) for x in res.get("rejected", [])}


def write_log(log: dict, sector: int, label: str, commit: str) -> None:
    runs = DATA / "runs"
    runs.mkdir(exist_ok=True)
    (runs / f"core_s{sector:03d}_{label}_{commit}.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", action="store_true")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="scrive solo data/outbox/, nessun invio")
    a = ap.parse_args()

    cfg = config.load()
    sector = cfg["dataset"]["sector"]
    if a.all and not cfg["frozen"]:
        sys.exit("parametri non congelati: imposta frozen = true in config/pipeline.toml prima della corsa finale")
    label = "sample" if a.sample else "all"
    t0 = time.time()

    core.load_env()
    project = os.environ.get("PROJECT_ID")
    s = summaries(sector, label)
    fp = config.fingerprint(cfg)
    stale = [ph for ph, v in s.items() if v.get("params_fingerprint") != fp]
    if stale:
        sys.exit(f"parametri cambiati dopo {', '.join(stale)}: rilancia la pipeline prima di registrarla")
    commit = core.git_commit()
    if commit.endswith("-dirty") and not a.dry_run:
        sys.exit(f"codice con modifiche non registrate ({commit}): fai il commit prima di inviare")

    products = json.loads((DATA / f"products_s{sector:03d}_{label}.json").read_text())
    cand = pd.read_csv(DATA / f"crossmatch_s{sector:03d}_{label}.csv", keep_default_na=False,
                       na_values=["", "nan", "NaN"])
    dataset_box = DATA / "outbox" / f"dataset_s{sector:03d}.json"
    dataset_msgs = json.loads(dataset_box.read_text())["messages"] if dataset_box.exists() else []
    releases = products["data_release"]  # lista delle data release presenti nelle intestazioni
    if len(releases) != 1:
        sys.exit(f"curve di più data release {releases}: il dataset non è univoco")
    ds_id = core.dataset_id(sector, releases[0])

    items = s["fase2"]["ok"]
    duration = sum(v["duration_s"] for v in s.values())
    outcome = "partial" if s["fase2"]["errors"] or s["fase4"]["other_sector_errors"] else "ok"
    params = cfg | {"label": label}

    if a.dry_run or not project:
        run = core.run_message(commit, fp, sector, label, params, items, duration, outcome, project or "PROJECT_ID",
                               ds_id if dataset_msgs else None)
        res = [core.result_message(r, sector, 0) for r in cand.to_dict("records")]
        print("outbox:", core.write_outbox([run] + res, f"run_s{sector:03d}_{label}"))
        if not project:
            print("PROJECT_ID mancante in .env: niente invio")
        return

    c = core.client()
    if c is None:
        sys.exit("VDX_CORE_URL o VDX_TOKEN mancanti in .env")
    log = {"sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "core": os.environ["VDX_CORE_URL"],
           "commit": commit, "params_fingerprint": fp, "label": label, "warnings": []}

    # 1. dataset
    dataset = None
    if dataset_msgs:
        r = c.send(dataset_msgs)
        # il token del progetto può solo collegare il dataset, non crearlo: se Core lo rifiuta lo si
        # collega comunque per externalId, nel caso sia stato creato dalla console
        dataset = ds_id
        if rejected(r):
            log["dataset"] = {"rejected": rejected(r)[0]}
        else:
            log["dataset"] = r["results"][0]
    else:
        log["warnings"].append("nessun messaggio di dataset in data/outbox/: esegui scripts/fase1.py")

    # 2. esecuzione
    run_msg = core.run_message(commit, fp, sector, label, params, items, duration, outcome, project, dataset)
    r = c.send([run_msg])
    if rejected(r) and dataset:
        log["warnings"].append(f"esecuzione rifiutata con il dataset ({rejected(r)[0]}): inviata senza; "
                               f"crea il dataset dalla console con externalId {ds_id}")
        dataset = None
        r = c.send([core.run_message(commit, fp, sector, label, params, items, duration, outcome, project)])
    if rejected(r):
        err = rejected(r)[0]
        log["warnings"].append(f"esecuzione rifiutata: {err}")
        write_log(log, sector, label, commit)
        hint = ("; il token non è di una source Research (module \"custom\"): creala in Core da "
                "/admin/engine (Sorgente pipeline Research) o con scripts/create-research-source.ts") if "subject is required" in err else ""
        sys.exit(f"esecuzione rifiutata: {err}{hint}")
    log["run"] = r["results"][0]
    run_id = int(log["run"]["id"])

    # 3. risultati
    rows = cand.to_dict("records")
    r = c.send([core.result_message(x, sector, run_id) for x in rows])
    bad = rejected(r)
    if bad:
        log["warnings"].append(f"{len(bad)} risultati rifiutati con extra ({next(iter(bad.values()))}): inviati senza")
        retry = sorted(bad)
        r2 = c.send([core.result_message(rows[i], sector, run_id, with_extra=False) for i in retry])
        r["results"] += [{**x, "index": retry[x["index"]]} for x in r2["results"]]
        bad = {retry[i]: e for i, e in rejected(r2).items()}
    log["results"] = {"sent": len(rows), "accepted": len(rows) - len(bad),
                      "status": pd.Series([x.get("status") for x in r["results"]]).value_counts().to_dict(),
                      "rejected": {int(rows[i]["tic"]): e for i, e in bad.items()}}

    # 4. grafici
    att = {"attached": 0, "duplicate": 0, "missing": [], "errors": {}}
    for x in rows:
        tic = int(x["tic"])
        p = plot_for(sector, label, tic)
        if p is None:
            att["missing"].append(tic)
            continue
        try:
            d = c.attach(str(p), core.ref("custom.result", core.result_id(sector, tic)))
            att["duplicate" if d.get("status") == "duplicate" else "attached"] += 1
        except Exception as e:
            att["errors"][tic] = f"{type(e).__name__}: {e}"
    log["plots"] = att

    if log["results"]["rejected"] or att["missing"] or att["errors"]:
        log["warnings"].append("invio incompleto: vedi results.rejected e plots")
    write_log(log, sector, label, commit)
    config.save_summary("fase5", sector, label, {
        "run_id": run_id, "run_status": log["run"].get("status"), "dataset_linked": dataset is not None,
        "results": log["results"], "plots": {k: v if isinstance(v, int) else len(v) for k, v in att.items()},
        "warnings": log["warnings"], "duration_s": round(time.time() - t0, 1), "params_fingerprint": fp})
    print("core:", json.dumps({k: log[k] for k in ("run", "results", "plots", "warnings")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
