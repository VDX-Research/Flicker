"""Grafici di un candidato: curva, curva appiattita con eventi, periodogramma, ripiegamento BLS.

Una figura PNG per TIC, quattro pannelli, pensata per un astronomo e riusabile come allegato
dei Risultati in Core (FASE 5). Colori: dati in grigio, curva binnata in blu, marcatori degli
eventi in rosso (dip) e arancio (brillamenti), più etichette: il colore non è mai l'unica
informazione.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

from vdxtess.features import bin_curve, flatten

DATA, BINNED, DIP, FLARE, BLS = "#9aa0a6", "#1f5fae", "#c62828", "#e08a00", "#6a3d9a"


def _style(ax, xlabel, ylabel):
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(alpha=0.25, lw=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def candidate(d: pd.DataFrame, row: pd.Series, p: dict, path, title: str) -> None:
    """Scrive la figura del candidato `row` (riga del ranking) dalla curva pulita `d`."""
    t, f, seg = d.time.to_numpy(), d.flux.to_numpy(), d.segment.to_numpy()
    fig, ax = plt.subplots(4, 1, figsize=(9, 10), constrained_layout=True,
                           gridspec_kw={"height_ratios": [1.2, 1.2, 0.9, 0.9]})
    fig.suptitle(title, fontsize=10, ha="left", x=0.01)

    tb, fb = bin_curve(t, f, seg, p["ls_bin_minutes"])
    ax[0].plot(t, f, ".", ms=1, color=DATA, rasterized=True, label="2 min")
    ax[0].plot(tb, fb, ".", ms=2, color=BINNED, label=f"bin {p['ls_bin_minutes']:g} min")
    ax[0].legend(fontsize=7, loc="upper right", frameon=False)
    _style(ax[0], "BTJD", "flusso relativo (PDCSAP)")
    lo, hi = np.percentile(f, [0.5, 99.5])
    pad = 0.15 * (hi - lo)
    ax[0].set_ylim(lo - pad, hi + pad)

    flat = flatten(f, seg, p["flatten_window_d"])
    tb, fb = bin_curve(t, flat, seg, p["bls_bin_minutes"])
    ax[1].plot(t, flat, ".", ms=1, color=DATA, rasterized=True)
    ax[1].plot(tb, fb, ".", ms=2, color=BINNED)
    for name, c in (("dip", DIP), ("flare", FLARE)):
        t0 = row.get(f"t_{name}")
        if pd.notna(t0):
            ax[1].axvline(t0, color=c, lw=1, ls="--")
            ax[1].annotate(name, (t0, 1), xycoords=("data", "axes fraction"), color=c,
                           fontsize=7, ha="left", va="top", xytext=(2, -2), textcoords="offset points")
    _style(ax[1], "BTJD", f"appiattita ({p['flatten_window_d']:g} d)")
    lo, hi = np.percentile(flat, [0.1, 99.9])
    pad = 0.15 * (hi - lo)
    ax[1].set_ylim(lo - pad, hi + pad)

    tb, fb = bin_curve(t, f, seg, p["ls_bin_minutes"])
    ls = LombScargle(tb, fb)
    freq, power = ls.autopower(minimum_frequency=1 / p["ls_max_period_d"],
                               maximum_frequency=1 / p["ls_min_period_d"],
                               samples_per_peak=p["ls_samples_per_peak"])
    ax[2].plot(1 / freq, power, lw=0.8, color=BINNED)
    ax[2].axvline(row.ls_period, color=DIP, lw=0.8, ls=":")
    ax[2].annotate(f"P = {row.ls_period:.4g} d", (row.ls_period, 0.95), xycoords=("data", "axes fraction"),
                   fontsize=7, color="#333", xytext=(3, 0), textcoords="offset points", va="top")
    ax[2].set_xscale("log")
    _style(ax[2], "periodo [d]", "potenza Lomb-Scargle")

    tb, fb = bin_curve(t, flat, seg, p["bls_bin_minutes"])
    ph = ((tb - row.t_bls + row.bls_period / 2) % row.bls_period) / row.bls_period - 0.5
    ax[3].plot(ph * row.bls_period * 24, fb, ".", ms=2, color=DATA, rasterized=True)
    w = 3 * row.bls_duration_h
    ax[3].axvspan(-row.bls_duration_h / 2, row.bls_duration_h / 2, color=BLS, alpha=0.12, lw=0)
    ax[3].set_xlim(-max(w, 6), max(w, 6))
    _style(ax[3], "ore dal centro del transito BLS", "appiattita, ripiegata")
    ax[3].set_title(f"BLS: P = {row.bls_period:.4g} d, durata {row.bls_duration_h:.3g} h, "
                    f"profondità {row.bls_depth:.3g}, SNR {row.bls_snr:.3g}", fontsize=8, loc="left")

    fig.savefig(path, dpi=110)
    plt.close(fig)
