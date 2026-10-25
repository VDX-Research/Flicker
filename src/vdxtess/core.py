"""Registrazione in VDX Core (modulo Research). Senza credenziali i messaggi finiscono in un
file di outbox, da inviare più tardi con lo stesso contenuto: l'invio è idempotente."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from vdx_core_client import Client, obj

from .config import ROOT

OUTBOX = ROOT / "data" / "outbox"


def dataset_message(sector: int, data_release: int, procver: str, n_curves: int, size_bytes: int) -> dict:
    return obj(
        "custom.dataset", f"tess-s{sector:03d}-spoc-2min-dr{data_release}",
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


def client() -> Client | None:
    url, token = os.environ.get("VDX_CORE_URL"), os.environ.get("VDX_TOKEN")
    return Client(url, token) if url and token else None


def deliver(messages: list, name: str) -> str:
    """Invia a Core se ci sono le credenziali, altrimenti scrive l'outbox. Restituisce dove è finito."""
    c = client()
    if c is not None:
        c.send(messages)
        return "core"
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / f"{name}.json"
    path.write_text(json.dumps({"written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "messages": messages}, indent=2, ensure_ascii=False))
    return str(path.relative_to(ROOT))
