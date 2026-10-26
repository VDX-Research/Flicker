"""Registrazione in VDX Core (modulo Research): il Dataset, l'Esecuzione e i suoi Risultati.

Le funzioni *_message costruiscono i messaggi senza rete (tests/test_core.py); l'invio lo fa
scripts/fase5.py. Senza credenziali i messaggi finiscono in data/outbox/, da inviare più tardi
con lo stesso contenuto: dataset e risultati sono riconosciuti per externalId, l'esecuzione per
key, quindi ripetere un invio aggiorna gli stessi oggetti invece di duplicarli.
"""
import json
import math
import os
import subprocess
from datetime import datetime, timezone

from vdx_core_client import Client, event, obj, ref

from .config import ROOT

OUTBOX = ROOT / "data" / "outbox"
# etichetta di catalogo della FASE 4 -> property `reference` di custom.result
REFERENCE = {"noto": "known", "noto con classe diversa": "known_other", "assente": "absent"}


def load_env(path=ROOT / ".env") -> None:
    """Variabili da .env del repo, senza sovrascrivere quelle già impostate. Un VDX_CORE_URL
    senza schema diventa https://."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    url = os.environ.get("VDX_CORE_URL")
    if url and "://" not in url:
        os.environ["VDX_CORE_URL"] = "https://" + url


def client() -> Client | None:
    url, token = os.environ.get("VDX_CORE_URL"), os.environ.get("VDX_TOKEN")
    return Client(url, token) if url and token else None


def git_commit() -> str:
    """Hash corto di HEAD, con "-dirty" se il codice versionato ha modifiche non registrate."""
    git = ["git", "-C", str(ROOT)]
    h = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(git + ["status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    return h + ("-dirty" if dirty else "")


def dataset_id(sector: int, data_release: int) -> str:
    return f"tess-s{sector:03d}-spoc-2min-dr{data_release}"


def dataset_message(sector: int, data_release: int, procver: str, n_curves: int, size_bytes: int) -> dict:
    return obj(
        "custom.dataset", dataset_id(sector, data_release),
        name=f"TESS S{sector} SPOC 2-min (DR{data_release})",
        properties={
            "source": "MAST, TESS SPOC light curves",
            "description": (f"Curve di luce PDCSAP a 2 minuti del settore {sector}, data release {data_release}, "
                            f"pipeline {procver}. Pulite con config/pipeline.toml di vdx-research-tess."),
            "size": f"{n_curves} curve, {size_bytes / 1e9:.1f} GB",
            "url": f"https://archive.stsci.edu/missions/tess/tid/s{sector:04d}/",
            "license": "Dati pubblici NASA/MAST; citare TESS SPOC (Jenkins et al. 2016) e la release note DRN"
                       f"{data_release}",
        })


def run_key(commit: str, fingerprint: str, sector: int, label: str) -> str:
    """Stesso codice, stessi parametri, stesso settore e stessa selezione: stessa esecuzione."""
    return f"{commit}:{fingerprint}:S{sector}:{label}"


def run_message(commit: str, fingerprint: str, sector: int, label: str, params: dict, items: int,
                duration_s: float, outcome: str, project: str, dataset: str | None = None) -> dict:
    objects = [project] + ([ref("custom.dataset", dataset)] if dataset else [])
    payload = {"commit": commit, "params": params, "items": int(items), "duration_s": round(float(duration_s), 1),
               "outcome": outcome}
    return event("custom.run", key=run_key(commit, fingerprint, sector, label), payload=payload, objects=objects)


def result_id(sector: int, tic: int) -> str:
    """Un risultato per TIC e settore: la corsa su tutti i target aggiorna quello del campione."""
    return f"s{sector:03d}-tic-{int(tic)}"


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def _fmt(v, spec=".3g"):
    v = _clean(v)
    return "" if v is None or v == "" else (format(v, spec) if isinstance(v, float) else str(v))


def result_note(r: dict) -> str:
    """Nota leggibile in Core: evento guida, cataloghi, controlli sui falsi segnali."""
    parts = [f"Candidato, rank {int(r['rank'])} in S{int(r['sector'])}" if "sector" in r else f"Candidato, rank {int(r['rank'])}",
             f"evento guida: {_fmt(r.get('event')) or 'nessuno'}",
             f"guidato da: {_fmt(r.get('drivers'))}",
             f"catalogo: {r['catalog_label']}" + (f" ({r['catalog_explains']})" if _fmt(r.get("catalog_explains")) else "")]
    if _fmt(r.get("simbad_id")):
        parts.append(f"SIMBAD: {r['simbad_id']} [{_fmt(r.get('simbad_otype'))}]")
    if _fmt(r.get("vsx_name")):
        parts.append(f"VSX: {r['vsx_name']} [{_fmt(r.get('vsx_type'))}]")
    if _fmt(r.get("toi")):
        parts.append(f"TOI {r['toi']} {_fmt(r.get('toi_disposition'))}".strip())
    if _fmt(r.get("variabile_vicina")):
        parts.append(f"variabile vicina: {r['variabile_vicina']}")
    if bool(r.get("sospetto_sistematica")):
        parts.append("sospetto sistematica: evento coincidente con altre stelle del CCD")
    parts.append(f"persistenza: {r['persistence']}" + (f" ({r['persistence_detail']})" if _fmt(r.get("persistence_detail")) else ""))
    if _fmt(r.get("warnings")):
        parts.append(f"avvisi: {r['warnings']}")
    return "; ".join(parts)


def result_message(r: dict, sector: int, run_id: int, with_extra: bool = True) -> dict:
    """Riga di data/crossmatch_*.csv -> custom.result. `review` sta solo nei defaults: un nuovo
    invio non tocca la revisione fatta in Core."""
    tic = int(r["tic"])
    props = {"score": round(float(r["prank_combined"]), 6), "reference": REFERENCE[r["catalog_label"]],
             "run": int(run_id), "note": result_note(r | {"sector": sector})}
    if with_extra:
        props["extra"] = {"tic_id": tic}
    return obj("custom.result", result_id(sector, tic), name=f"TIC {tic}", properties=props,
               defaults={"review": "to_review"})


def write_outbox(messages: list, name: str) -> str:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / f"{name}.json"
    path.write_text(json.dumps({"written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "messages": messages}, indent=2, ensure_ascii=False))
    return str(path.relative_to(ROOT))
