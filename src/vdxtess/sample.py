"""Campione di sviluppo riproducibile, stratificato per magnitudine."""
import numpy as np
import pandas as pd


def allocate(counts: np.ndarray, n: int) -> np.ndarray:
    """Quote proporzionali intere che sommano a n (metodo dei resti maggiori; a parità di resto
    vince la classe con l'indice minore, così il risultato non dipende dal caso)."""
    counts = np.asarray(counts, dtype=int)
    if n > counts.sum():
        raise ValueError("campione più grande della popolazione")
    exact = counts * n / counts.sum()
    k = np.floor(exact).astype(int)
    rest = n - k.sum()
    order = np.lexsort((np.arange(len(counts)), -(exact - k)))
    k[order[:rest]] += 1
    return np.minimum(k, counts)


def stratified_sample(df: pd.DataFrame, n: int, seed: int, edges: list[float], col: str = "tmag") -> pd.DataFrame:
    """n righe di df estratte per classi di `col` (limiti `edges`), proporzionali alla
    popolazione di ogni classe. Stesso df, n e seed danno sempre lo stesso campione: le righe
    sono ordinate per tic prima di estrarre. Le righe senza `col` non entrano nel campione."""
    d = df.dropna(subset=[col]).sort_values("tic").reset_index(drop=True)
    stratum = pd.cut(d[col], bins=edges, labels=False, right=False)
    counts = np.bincount(stratum, minlength=len(edges) - 1)
    quota = allocate(counts, n)
    rng = np.random.default_rng(seed)
    picked = [rng.choice(np.flatnonzero(stratum == s), size=q, replace=False) for s, q in enumerate(quota) if q]
    out = d.loc[np.sort(np.concatenate(picked))].copy()
    out["stratum"] = stratum[out.index].astype(int)
    return out.reset_index(drop=True)
