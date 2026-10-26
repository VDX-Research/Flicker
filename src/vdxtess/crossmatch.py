"""FASE 4: confronto con i cataloghi (SIMBAD, VSX, TOI, binarie a eclisse TESS), controllo dei falsi segnali e persistenza.

Funzioni pure sulle tabelle: le interrogazioni in rete e la loro cache stanno in scripts/fase4.py,
così le regole di etichettatura si provano senza rete (tests/test_crossmatch.py).

Etichetta di catalogo (`catalog_label`), per l'evento che guida il punteggio:
- "noto": un catalogo dà al target una classe che spiega l'evento (tabella EXPLAINS);
- "noto con classe diversa": il target ha una classe di variabilità che non spiega l'evento;
- "assente": nessuna classe di variabilità per il target (può comparire come stella qualunque).
Il target è l'oggetto più vicino entro `match_radius_arcsec`; una variabile nota più lontana ma
entro `neighbor_radius_arcsec` (~2 pixel TESS) è un possibile contaminante (`variabile_vicina`).
"""
import re

import numpy as np
import pandas as pd
from scipy.stats import poisson

# Tipi SIMBAD di variabilità (codici brevi di SIMBAD 4). Le classi candidate ("EB?", "Fl?",
# "Y*?", "V*?") contano come la classe stessa. Tutti gli altri tipi (*, PM*, **, SB*, HS*, s*b,
# Em*, ...) non sono classi di variabilità.
SIMBAD_VARIABLE = {
    "V*", "Ir*", "Er*", "Ro*", "El*", "EB*", "Fl*", "BY*", "RS*", "Pu*", "RR*", "Ce*", "cC*", "dS*",
    "RV*", "WV*", "bC*", "gD*", "SX*", "LP*", "Mi*", "sr*", "a2*", "Or*", "TT*", "Y*O", "Ae*",
    "CV*", "No*", "XB*", "LXB", "HXB", "BS*", "Psr", "WD*", "ZZ*", "BD*", "Pl", "Be*",
}
# classi che spiegano l'evento: dip (e transito BLS) o brillamento
SIMBAD_EXPLAINS = {
    "dip": {"EB*", "Or*", "TT*", "Y*O", "Ae*", "Pl"},
    "flare": {"Fl*", "Er*", "BY*", "RS*", "TT*", "Or*", "Y*O", "CV*", "No*"},
}
SIMBAD_EXPLAINS["bls"] = SIMBAD_EXPLAINS["dip"]

# Tipi VSX (GCVS esteso): si confrontano i prefissi dei singoli tipi di una designazione composta
# come "EA/DM", "BY+UV" o "ROT:" (i ":" di incertezza si ignorano). Ogni riga VSX è una variabile.
VSX_EXPLAINS = {
    "dip": ("E", "UXOR", "INS", "IN", "TTS", "CTTS",
            "WTTS", "YSO", "DIP"),
    "flare": ("UV", "UVN", "FLARE", "BY", "RS", "INS", "IN", "TTS", "CTTS", "WTTS", "YSO",
              "UG", "NL", "N", "ZAND", "CV"),
}
VSX_EXPLAINS["bls"] = VSX_EXPLAINS["dip"]
VSX_NOT_ECLIPSING = ("ELL",)  # tutti i tipi "E*" sono a eclisse (EA, EB, EW, EP...) tranne ELL

LABELS = ("noto", "noto con classe diversa", "assente")


def simbad_type(otype: str) -> str:
    """Tipo SIMBAD normalizzato: la classe candidata vale come la classe ("EB?" -> "EB*",
    "Y*?" -> "Y*O", "V*?" -> "V*")."""
    t = otype.strip() if isinstance(otype, str) else ""
    if t.endswith("?"):
        for full in (t[:-1] + "*", t[:-1] + "O", t[:-1]):
            if full in SIMBAD_VARIABLE:
                return full
    return t


def vsx_tokens(vtype: str) -> list[str]:
    return [t for t in re.split(r"[/+|,() ]+", (vtype if isinstance(vtype, str) else "").replace(":", "").upper()) if t]


def vsx_explains(vtype: str, event: str) -> bool:
    for tok in vsx_tokens(vtype):
        if tok.startswith(VSX_NOT_ECLIPSING):
            continue
        if tok.startswith(VSX_EXPLAINS.get(event, ())):
            return True
    return False


def nearest(rows: pd.DataFrame, radius: float) -> pd.Series | None:
    """Riga più vicina entro `radius` arcosecondi (colonna `sep_arcsec`), None se non c'è."""
    if rows is None or rows.empty:
        return None
    r = rows.sort_values("sep_arcsec")
    return r.iloc[0] if r.sep_arcsec.iat[0] <= radius else None


def label(event: str, simbad: pd.DataFrame, vsx: pd.DataFrame, toi: pd.DataFrame, p: dict,
          tess_eb: pd.DataFrame | None = None) -> dict:
    """Etichetta di catalogo di un candidato. `simbad` (main_id, otype, sep_arcsec), `vsx`
    (Name, Type, Period, sep_arcsec) e `toi` (TOI, TFOPWG Disposition) sono le righe trovate
    intorno al candidato; TOI e `tess_eb` (Prša et al. 2022, colonne TIC, Per) sono legati per
    TIC, quindi sono sempre il target. Una binaria a eclisse TESS spiega dip e transito BLS."""
    s = nearest(simbad, p["match_radius_arcsec"])
    v = nearest(vsx, p["match_radius_arcsec"])
    s_type = simbad_type(s.otype) if s is not None else ""
    s_var = s_type in SIMBAD_VARIABLE
    has_toi = toi is not None and not toi.empty
    has_eb = tess_eb is not None and not tess_eb.empty
    explains = []
    if s_var and s_type in SIMBAD_EXPLAINS.get(event, set()):
        explains.append(f"SIMBAD {s_type}")
    if v is not None and vsx_explains(v.Type, event):
        explains.append(f"VSX {v.Type}")
    if has_toi and event in ("dip", "bls"):
        explains.append("TOI")
    if has_eb and event in ("dip", "bls"):
        explains.append("TESS EB")
    if explains:
        lab = "noto"
    elif s_var or v is not None or has_toi or has_eb:
        lab = "noto con classe diversa"
    else:
        lab = "assente"

    # variabili note entro il raggio di contaminazione che non sono il target
    neigh = []
    if simbad is not None and not simbad.empty:
        for _, r in simbad.iterrows():
            if (s is None or r.main_id != s.main_id) and simbad_type(r.otype) in SIMBAD_VARIABLE \
                    and r.sep_arcsec <= p["neighbor_radius_arcsec"]:
                neigh.append(f"{r.main_id} ({simbad_type(r.otype)}, {r.sep_arcsec:.0f}\")")
    if vsx is not None and not vsx.empty:
        for _, r in vsx.iterrows():
            if (v is None or r.Name != v.Name) and r.sep_arcsec <= p["neighbor_radius_arcsec"]:
                neigh.append(f"{r.Name} ({r.Type}, {r.sep_arcsec:.0f}\")")
    return {
        "catalog_label": lab,
        "catalog_explains": "; ".join(explains),
        "simbad_id": s.main_id if s is not None else "",
        "simbad_otype": s.otype if s is not None else "",
        "simbad_sep_arcsec": s.sep_arcsec if s is not None else np.nan,
        "vsx_name": v.Name if v is not None else "",
        "vsx_type": v.Type if v is not None else "",
        "vsx_period_d": v.Period if v is not None else np.nan,
        "toi": "; ".join(str(t) for t in toi["TOI"]) if has_toi else "",
        "toi_disposition": "; ".join(str(t) for t in toi["TFOPWG Disposition"].fillna("")) if has_toi else "",
        "tess_eb_period_d": float(tess_eb.Per.iat[0]) if has_eb else np.nan,
        "variabile_vicina": "; ".join(neigh),
    }


def coincidences(cand: pd.DataFrame, pop: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Eventi coincidenti: per ogni candidato con evento dip o brillamento, quante ALTRE stelle
    dello stesso camera/CCD hanno l'evento più forte dello stesso tipo entro ±window giorni.

    Il numero si confronta con l'atteso se gli eventi del CCD fossero sparsi a caso nel settore
    (Poisson, λ = eventi del CCD × 2·window / durata): con p < coincidence_max_p l'evento è
    `sospetto_sistematica`. La probabilità non dipende dalla dimensione della popolazione, quindi
    la stessa soglia vale sul campione e su tutti i target."""
    w = p["coincidence_window_d"]
    out = []
    for _, r in cand.iterrows():
        k = r.event
        if k not in ("dip", "flare"):
            out.append({"tic": r.tic, "coinc_n": np.nan, "coinc_expected": np.nan, "coinc_p": np.nan,
                        "sospetto_sistematica": False})
            continue
        t_col, n_col = f"t_{k}", f"n_{k}s"
        ccd = pop[(pop.camera == r.camera) & (pop.ccd == r.ccd) & (pop.tic != r.tic) & (pop[n_col] > 0)]
        t_all = pop.loc[pop[n_col] > 0, t_col]
        span = float(t_all.max() - t_all.min()) if len(t_all) > 1 else np.nan
        n = int(((ccd[t_col] - r[t_col]).abs() <= w).sum())
        lam = len(ccd) * 2 * w / span if span and span > 0 else np.nan
        pv = float(poisson.sf(n - 1, lam)) if n > 0 and np.isfinite(lam) else 1.0
        out.append({"tic": r.tic, "coinc_n": n, "coinc_expected": lam, "coinc_p": pv,
                    "sospetto_sistematica": pv < p["coincidence_max_p"]})
    return pd.DataFrame(out)


def other_sectors(overlap: str, sector: int, max_sector: int) -> list[int]:
    """Settori SPOC del target diversi da `sector` e non oltre `max_sector`, dalla colonna
    `other_sectors` di data/overlap_s103.csv (stringa separata da spazi, NaN se nessuno)."""
    if not isinstance(overlap, str):
        return []
    return sorted({int(s) for s in overlap.split() if int(s) != sector and int(s) <= max_sector})


def persistence(event: str, sectors: list[int], per_sector: pd.DataFrame, p: dict) -> dict:
    """Etichetta di persistenza dall'evento guida e dalle caratteristiche degli altri settori.

    `per_sector`: una riga per settore scaricato (sector, n_dips, dip_snr, n_flares, flare_snr,
    bls_snr, error). "persistente" se in almeno un altro settore lo stesso tipo di evento è
    rilevato con SNR >= persistence_min_snr; "persistenza non verificabile" se il target non ha
    altri settori o nessuno è leggibile, o se l'evento guida non è un evento isolato."""
    if not sectors:
        return {"persistence": "persistenza non verificabile", "persistence_detail": "nessun altro settore"}
    ok = per_sector[per_sector.get("error", pd.Series(index=per_sector.index, dtype=object)).isna()] \
        if not per_sector.empty else per_sector
    if ok.empty:
        return {"persistence": "persistenza non verificabile", "persistence_detail": "altri settori illeggibili"}
    col = {"dip": ("n_dips", "dip_snr"), "flare": ("n_flares", "flare_snr")}.get(event)
    if col is None:
        if event == "bls":
            col = (None, "bls_snr")
        else:
            return {"persistence": "persistenza non verificabile", "persistence_detail": "evento guida non isolato"}
    n_col, snr_col = col
    snr = ok[snr_col].fillna(0)
    det = snr >= p["persistence_min_snr"]
    if n_col is not None:
        det &= ok[n_col].fillna(0) > 0
    detail = ", ".join(f"S{int(s)}: SNR {v:.0f}" for s, v in zip(ok.sector, snr))
    return {"persistence": "persistente" if det.any() else "non persistente", "persistence_detail": detail}
