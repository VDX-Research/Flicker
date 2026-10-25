"""Caratteristiche per TIC calcolate sulla curva pulita (flusso relativo, ~1).

Quattro gruppi, tutti interpretabili da un astronomo:
- variabilità e forma della distribuzione, sulla curva non detrendizzata;
- periodogramma di Lomb-Scargle, su bin di `bin_minutes`;
- ricerca di transiti (BLS), sulla curva appiattita da un filtro mediano mobile;
- eventi isolati (dip e brillamenti), sulla stessa curva appiattita.

L'appiattimento serve solo a BLS e agli eventi: toglie la variabilità lenta (> flatten_window_d)
e con essa anche gli oscuramenti più lunghi di qualche ora, che restano visibili nel primo gruppo
(asimmetria, ampiezza).

In più, diagnostiche per la fase di scarto degli artefatti (colonne `diag_*` e `t_*`): non
entrano nei modelli, servono ai criteri espliciti di scarto.
"""
import numpy as np
import pandas as pd
from astropy.timeseries import BoxLeastSquares, LombScargle
from scipy.ndimage import median_filter
from scipy.stats import kurtosis, skew

# caratteristiche che entrano nei modelli della FASE 3 (le altre colonne sono metadati)
MODEL_FEATURES = [
    "std", "mad_std", "noise_ratio", "p2p_std", "amp_90", "amp_98", "skew", "kurt", "eta",
    "ls_period", "ls_power", "ls_amp",
    "bls_period", "bls_depth", "bls_duration_h", "bls_snr",
    "n_dips", "dip_depth", "dip_snr", "dip_duration_h",
    "n_flares", "flare_amp", "flare_snr", "flare_duration_h",
]

CADENCE_D = 2 / 1440
IMPULSIVE_OUTLIER = 512


def mad_std(x: np.ndarray) -> float:
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def bin_curve(time: np.ndarray, flux: np.ndarray, segment: np.ndarray, minutes: float) -> tuple[np.ndarray, np.ndarray]:
    """Media del flusso in bin di `minutes` minuti, senza bin a cavallo di due segmenti."""
    w = minutes / 1440
    key = pd.DataFrame({"s": segment, "b": np.floor((time - time.min()) / w).astype(np.int64),
                        "t": time, "f": flux})
    g = key.groupby(["s", "b"], sort=True)[["t", "f"]].mean()
    return g.t.to_numpy(), g.f.to_numpy()


def flatten(flux: np.ndarray, segment: np.ndarray, window_d: float) -> np.ndarray:
    """Flusso diviso per la mediana mobile di window_d giorni, segmento per segmento."""
    size = max(3, int(round(window_d / CADENCE_D)) | 1)
    trend = np.empty_like(flux)
    for s in np.unique(segment):
        m = segment == s
        trend[m] = median_filter(flux[m], size=min(size, int(m.sum()) | 1), mode="nearest")
    return flux / trend


def distribution(flux: np.ndarray, flux_err: np.ndarray, segment: np.ndarray) -> dict:
    d = np.diff(flux)[np.diff(segment) == 0]  # differenze solo dentro un segmento
    var = np.var(flux)
    p = np.percentile(flux, [1, 5, 95, 99])
    m = mad_std(flux)
    return {
        "std": float(np.std(flux)),
        "mad_std": m,
        # variabilità rispetto al rumore atteso: ~1 per una stella costante
        "noise_ratio": m / float(np.median(flux_err)),
        # rumore punto-punto: insensibile alla variabilità lenta
        "p2p_std": mad_std(d) / np.sqrt(2),
        "amp_90": float(p[2] - p[1]),
        "amp_98": float(p[3] - p[0]),
        "skew": float(skew(flux)),
        "kurt": float(kurtosis(flux)),
        # rapporto di von Neumann: ~2 per rumore bianco, << 2 per variabilità coerente
        "eta": float(np.mean(d ** 2) / var) if var > 0 else np.nan,
    }


def periodogram(t: np.ndarray, f: np.ndarray, min_period: float, max_period: float, samples_per_peak: int) -> dict:
    ls = LombScargle(t, f)
    freq, power = ls.autopower(minimum_frequency=1 / max_period, maximum_frequency=1 / min_period,
                               samples_per_peak=samples_per_peak)
    i = int(np.argmax(power))
    model = ls.model(t, freq[i])
    return {"ls_period": float(1 / freq[i]), "ls_power": float(power[i]),
            "ls_amp": float((model.max() - model.min()) / 2)}


def bls(t: np.ndarray, f: np.ndarray, min_period: float, max_period: float, durations_h: list[float],
        frequency_factor: float) -> dict:
    durations = np.asarray(durations_h) / 24
    model = BoxLeastSquares(t, f)
    periods = model.autoperiod(durations, minimum_period=min_period, maximum_period=max_period,
                               frequency_factor=frequency_factor)
    r = model.power(periods, durations, objective="snr")
    i = int(np.argmax(r.power))
    stats = model.compute_stats(r.period[i], r.duration[i], r.transit_time[i])
    return {"bls_period": float(r.period[i]), "bls_depth": float(r.depth[i]),
            "bls_duration_h": float(r.duration[i] * 24), "bls_snr": float(r.depth_snr[i]),
            "bls_n_transits": int(np.sum(np.asarray(stats["per_transit_count"]) > 0)),
            "t_bls": float(r.transit_time[i])}


def runs(mask: np.ndarray, time: np.ndarray, max_gap_d: float) -> list[np.ndarray]:
    """Gruppi di indici consecutivi con mask vera; un buco > max_gap_d spezza il gruppo."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    cut = np.flatnonzero((np.diff(idx) > 1) | (np.diff(time[idx]) > max_gap_d)) + 1
    return np.split(idx, cut)


def events(time: np.ndarray, r: np.ndarray, sigma: float, min_points: int, sign: int) -> tuple[list, float]:
    """Eventi isolati sulla curva appiattita r (~0): almeno min_points cadenze consecutive oltre
    `sigma` deviazioni robuste, sotto lo zero (sign=-1, dip) o sopra (sign=+1, brillamento).
    Un punto singolo, come un raggio cosmico, non basta. Restituisce i gruppi di indici e il
    rumore robusto usato."""
    s = mad_std(r)
    if s == 0:
        return [], s
    found = [g for g in runs(sign * r > sigma * s, time, 3 * CADENCE_D) if g.size >= min_points]
    return found, s


def strongest(time: np.ndarray, r: np.ndarray, found: list, s: float, sign: int, name: str) -> tuple[dict, np.ndarray]:
    """Riassunto dell'evento più significativo (SNR = somma dei residui / (σ √n))."""
    size = "depth" if sign < 0 else "amp"
    out = {f"n_{name}s": len(found), f"{name}_{size}": 0.0, f"{name}_snr": 0.0,
           f"{name}_duration_h": 0.0, f"t_{name}": np.nan}
    if not found:
        return out, np.array([], dtype=int)
    snr = np.array([sign * r[g].sum() / (s * np.sqrt(g.size)) for g in found])
    g = found[int(np.argmax(snr))]
    peak = g[int(np.argmax(sign * r[g]))]
    out |= {f"{name}_{size}": float(sign * r[peak]), f"{name}_snr": float(snr.max()),
            f"{name}_duration_h": float((time[g[-1]] - time[g[0]] + CADENCE_D) * 24),
            f"t_{name}": float(time[peak])}
    return out, g


def edge_distance(t0: float, time: np.ndarray, segment: np.ndarray) -> float:
    """Distanza in giorni dal bordo di segmento più vicino (inizio o fine settore, buchi)."""
    if not np.isfinite(t0):
        return np.nan
    edges = np.concatenate([[time[segment == s].min(), time[segment == s].max()] for s in np.unique(segment)])
    return float(np.min(np.abs(edges - t0)))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3 or np.std(a[m]) == 0 or np.std(b[m]) == 0:
        return np.nan
    return float(np.corrcoef(a[m], b[m])[0, 1])


def diagnostics(d: pd.DataFrame, flat: np.ndarray, groups: dict, out: dict) -> dict:
    """Diagnostiche per lo scarto: correlazione del flusso appiattito con centroidi e fondo
    (|r| alto = sistematica o contaminazione), distanza degli eventi dai bordi, quante cadenze
    dell'evento hanno il flag "Impulsive outlier"."""
    t, seg = d.time.to_numpy(), d.segment.to_numpy()
    f = flat - 1
    res = {
        "diag_corr_centr": np.nanmax(np.abs([corr(f, d[c].to_numpy()) for c in ("mom_centr1", "mom_centr2")])),
        "diag_corr_bkg": corr(f, d.sap_bkg.to_numpy()),
    }
    q = d.quality.to_numpy().astype(np.int64)
    for name, g in groups.items():
        res[f"diag_{name}_edge_d"] = edge_distance(out[f"t_{name}"], t, seg)
        res[f"diag_{name}_q512"] = int(np.sum((q[g] & IMPULSIVE_OUTLIER) > 0))
        # spostamento del centroide durante l'evento rispetto alla dispersione fuori evento
        shift = []
        for c in ("mom_centr1", "mom_centr2"):
            x = d[c].to_numpy()
            if g.size == 0 or not np.isfinite(x).any():
                continue
            outside = np.delete(x, g)
            sd = mad_std(outside[np.isfinite(outside)])
            if sd > 0:
                shift.append(abs(np.nanmean(x[g]) - np.nanmedian(outside)) / (sd / np.sqrt(g.size)))
        res[f"diag_{name}_centr_shift"] = float(max(shift)) if shift else np.nan
    res["diag_bls_edge_d"] = edge_distance(out["t_bls"], t, seg)
    return res


def features(d: pd.DataFrame, p: dict) -> dict:
    """Tutte le caratteristiche di una curva pulita (colonne di clean.py)."""
    t, f, fe, seg = (d[c].to_numpy() for c in ("time", "flux", "flux_err", "segment"))
    out = {"n_points": len(t), "baseline_d": float(t.max() - t.min())}
    out |= distribution(f, fe, seg)
    tb, fb = bin_curve(t, f, seg, p["ls_bin_minutes"])
    out |= periodogram(tb, fb, p["ls_min_period_d"], p["ls_max_period_d"], p["ls_samples_per_peak"])
    flat = flatten(f, seg, p["flatten_window_d"])
    tb, fb = bin_curve(t, flat, seg, p["bls_bin_minutes"])
    out |= bls(tb, fb, p["bls_min_period_d"], p["bls_max_period_d"], p["bls_durations_h"], p["bls_frequency_factor"])
    r = flat - 1
    groups = {}
    for sign, name in ((-1, "dip"), (1, "flare")):
        found, s = events(t, r, p["event_sigma"], p["event_min_points"], sign)
        o, groups[name] = strongest(t, r, found, s, sign, name)
        out |= o
    out |= diagnostics(d, flat, groups, out)
    return out
