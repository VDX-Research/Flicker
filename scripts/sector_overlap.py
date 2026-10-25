"""Frazione di TIC 2-min del settore 103 osservati anche in altri settori SPOC.

Uso: python scripts/sector_overlap.py [--sector 103] [--out data/overlap_s103.csv]
"""
import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from astroquery.mast import Observations

# Settori usati per la persistenza: solo quelli con note di rilascio pubblicate (<= 104).
# I settori 105-107 hanno già dati su MAST ma non ancora le note: esclusi dalla v1.
MAX_SECTOR = 104
# "recenti" = anno 8 rolled (99-104); "vecchi" = qualsiasi settore < 99.
RECENT = set(range(99, MAX_SECTOR + 1))
YEAR7 = set(range(91, 98))
YEARS1_5 = set(range(1, 70))


def sector_targets(sector: int) -> pd.DataFrame:
    r = Observations.query_criteria(obs_collection="TESS", provenance_name="SPOC",
                                    dataproduct_type="timeseries", sequence_number=sector)
    df = r["target_name", "t_exptime", "sequence_number"].to_pandas()
    return df


def other_sectors(tics: list[str], chunk: int = 400) -> pd.DataFrame:
    out = []
    for i in range(0, len(tics), chunk):
        for attempt in range(3):
            try:
                r = Observations.query_criteria(obs_collection="TESS", provenance_name="SPOC",
                                                dataproduct_type="timeseries",
                                                target_name=tics[i:i + chunk])
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"query fallita per il blocco {i}")
        out.append(r["target_name", "t_exptime", "sequence_number"].to_pandas())
    return pd.concat(out, ignore_index=True)


def summarize(obs: pd.DataFrame, tics: list[str], sector: int) -> dict:
    """obs: righe (target_name, sequence_number) di qualunque cadenza SPOC."""
    o = obs[(obs.sequence_number != sector) & (obs.sequence_number <= MAX_SECTOR)]
    per = o.groupby("target_name").sequence_number.apply(set)
    per = per.reindex(tics).apply(lambda s: s if isinstance(s, set) else set())
    recent = per.apply(lambda s: bool(s & (RECENT - {sector})))
    old = per.apply(lambda s: any(x < min(RECENT) for x in s))
    y7 = per.apply(lambda s: bool(s & YEAR7))
    y15 = per.apply(lambda s: bool(s & YEARS1_5))
    n = len(tics)
    return {"n": n, "recent": int(recent.sum()), "old": int(old.sum()),
            "year7": int(y7.sum()), "years1_5": int(y15.sum()),
            "any": int((recent | old).sum()), "both": int((recent & old).sum()),
            "none": int(n - (recent | old).sum()),
            "n_other_median": float(np.median(per.apply(len)))}, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sector", type=int, default=103)
    ap.add_argument("--out", default="data/overlap_s103.csv")
    a = ap.parse_args()
    s = sector_targets(a.sector)
    tics = sorted(s.loc[s.t_exptime == 120, "target_name"].unique())
    obs = other_sectors(tics)
    stats, per = summarize(obs, tics, a.sector)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"tic": per.index, "other_sectors": per.apply(lambda x: " ".join(map(str, sorted(x))))}
                 ).to_csv(a.out, index=False)
    for k, v in stats.items():
        print(f"{k}: {v}" + (f"  ({100 * v / stats['n']:.1f}%)" if k not in ("n", "n_other_median") else ""))


if __name__ == "__main__":
    main()
