"""Lettura dei parametri e loro impronta, che finisce nelle esecuzioni registrate in Core."""
import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "config" / "pipeline.toml"


def load(path: Path = DEFAULT) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def fingerprint(params: dict) -> str:
    """sha256 dei parametri in forma canonica: due esecuzioni con la stessa impronta hanno
    usato esattamente gli stessi parametri."""
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


def save_summary(phase: str, sector: int, label: str, summary: dict) -> Path:
    """Riepilogo di una fase in data/summary_<fase>_s<settore>_<label>.json: la FASE 5 ne legge
    la durata per l'esecuzione registrata in Core."""
    path = ROOT / "data" / f"summary_{phase}_s{sector:03d}_{label}.json"
    path.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n")
    return path
