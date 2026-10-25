"""Scarico delle curve SPOC dall'archivio MAST, con cache locale e manifest verificabile."""
import hashlib
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from astropy.io import fits

BASE = "https://archive.stsci.edu/missions/tess/tid"


def lc_url(sector: int, tic: int, obs_id: str) -> str:
    """URL diretto del file *_lc.fits: TIC a 16 cifre diviso in quattro blocchi da 4."""
    t = f"{tic:016d}"
    return f"{BASE}/s{sector:04d}/{t[0:4]}/{t[4:8]}/{t[8:12]}/{t[12:16]}/{obs_id}_lc.fits"


def header_versions(path: Path) -> dict:
    """Versioni del prodotto lette dall'header primario."""
    with fits.open(path, memmap=False) as h:
        p = h[0].header
        return {"data_rel": int(p["DATA_REL"]), "procver": p["PROCVER"], "file_date": p["DATE"]}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(url: str, dest: Path, retries: int = 4) -> None:
    tmp = dest.with_suffix(".part")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                while b := r.read(1 << 20):
                    f.write(b)
            tmp.rename(dest)
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def download_one(sector: int, tic: int, obs_id: str, cache: Path, data_release: int) -> dict:
    """Scarica (se manca o è illeggibile) e verifica una curva. Rifiuta release diverse."""
    dest = cache / f"{obs_id}_lc.fits"
    fresh = False
    try:
        v = header_versions(dest)
    except Exception:
        fetch(lc_url(sector, tic, obs_id), dest)
        v = header_versions(dest)
        fresh = True
    if v["data_rel"] != data_release:
        raise ValueError(f"TIC {tic}: DATA_REL {v['data_rel']} invece di {data_release}")
    st = dest.stat()
    return {"tic": tic, "file": dest.name, "bytes": st.st_size, "sha256": sha256(dest),
            "downloaded_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "fresh": fresh, **v}


def download(targets: pd.DataFrame, sector: int, cache: Path, data_release: int, workers: int = 8) -> pd.DataFrame:
    """Scarica tutte le curve di `targets` (colonne tic, obs_id). Restituisce il manifest;
    le curve fallite compaiono con la colonna `error`."""
    cache.mkdir(parents=True, exist_ok=True)
    rows = []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(download_one, sector, int(t.tic), t.obs_id, cache, data_release): t.tic
                for t in targets.itertuples()}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append({"tic": futs[f], "error": str(e)})
            if i % 500 == 0:
                print(f"  {i}/{len(futs)}", flush=True)
    return pd.DataFrame(rows).sort_values("tic").reset_index(drop=True)
