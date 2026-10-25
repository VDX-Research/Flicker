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
