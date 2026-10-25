"""Scarto esplicito degli artefatti: criteri documentati, in ordine fisso, contati uno per uno.

Ogni criterio è una funzione della riga del ranking (caratteristiche e diagnostiche della FASE 2)
e delle soglie in `[artifacts]` di `config/pipeline.toml`. Una stella è scartata dal primo
criterio che fallisce (`artifact_reason`); i conteggi si riportano sia in sequenza (quante ne
elimina ciascun criterio dopo i precedenti) sia indipendenti (quante ne fallirebbero ciascuno da
solo), così due corse con soglie diverse si confrontano criterio per criterio.

Due famiglie:
- sulla stella: flusso non definito, contaminazione, sistematiche di centroide e fondo;
- sull'evento che guida il punteggio: si applicano solo se il primo motivo del punteggio
  (`drivers`) è quell'evento, perché un brillamento al bordo non rende artefatto una binaria
  a eclisse scelta per i suoi dip.

Gli avvisi (`warnings`) non scartano: segnalano cosa controllare a mano.
"""
import numpy as np
import pandas as pd

CADENCES_PER_HOUR = 30  # cadenza a 2 minuti

# primo motivo del punteggio che descrive la forma della distribuzione: l'evento è quello
# indicato dal segno dell'asimmetria (negativa: dip; positiva: brillamento)
SHAPE_DRIVERS = {"asinh_skew", "log_tail", "asinh_kurt", "log_amp90_p2p", "log_std_p2p", "log_noise_ratio"}


def driving_event(r: pd.DataFrame) -> pd.Series:
    """'dip', 'flare', 'bls' o '' (variabilità periodica o nessun evento) per ogni stella."""
    d1 = r.drivers.fillna("").str.split("=").str[0]
    out = np.select(
        [d1.str.contains("dip"), d1.str.contains("flare"), d1.str.contains("bls"),
         d1.isin(SHAPE_DRIVERS) & (r["skew"] < 0), d1.isin(SHAPE_DRIVERS) & (r["skew"] > 0)],
        ["dip", "flare", "bls", "dip", "flare"], default="")
    return pd.Series(out, index=r.index)


def event_table(r: pd.DataFrame) -> pd.DataFrame:
    """Diagnostiche dell'evento che guida il punteggio: distanza dal bordo, frazione di cadenze
    "Impulsive outlier", spostamento del centroide. NaN se l'evento non c'è."""
    kind = driving_event(r)
    e = pd.DataFrame({"event": kind, "edge_d": np.nan, "q512_frac": np.nan, "centr_shift": np.nan},
                     index=r.index)
    for k in ("dip", "flare"):
        m = kind == k
        n_cad = (r.loc[m, f"{k}_duration_h"] * CADENCES_PER_HOUR).round().clip(lower=1)
        has = r.loc[m, "n_dips" if k == "dip" else "n_flares"] > 0
        e.loc[m, "edge_d"] = r.loc[m, f"diag_{k}_edge_d"].where(has)
        e.loc[m, "q512_frac"] = (r.loc[m, f"diag_{k}_q512"] / n_cad).where(has)
        e.loc[m, "centr_shift"] = r.loc[m, f"diag_{k}_centr_shift"].where(has)
    m = kind == "bls"
    e.loc[m, "edge_d"] = r.loc[m, "diag_bls_edge_d"]
    return e


# (codice, descrizione, test): il test restituisce True dove la stella FALLISCE il criterio.
# Le comparazioni con NaN danno False: una diagnostica mancante non scarta.
CRITERIA = [
    ("flusso_indefinito", "dispersione relativa mad_std > max_mad_std: mediana PDCSAP vicina a zero",
     lambda r, e, p: r.mad_std > p["max_mad_std"]),
    ("contaminazione", "CROWDSAP < min_crowdsap: meno di metà del flusso in apertura è del target",
     lambda r, e, p: r.crowdsap < p["min_crowdsap"]),
    ("sistematica_centroide", "|r| flusso-centroide > max_corr_centr",
     lambda r, e, p: r.diag_corr_centr > p["max_corr_centr"]),
    ("sistematica_fondo", "|r| flusso-fondo > max_abs_corr_bkg",
     lambda r, e, p: r.diag_corr_bkg.abs() > p["max_abs_corr_bkg"]),
    ("evento_al_bordo", "l'evento che guida il punteggio è entro min_edge_d dal bordo di un segmento",
     lambda r, e, p: e.edge_d < p["min_edge_d"]),
    ("evento_impulsive_outlier", "frazione di cadenze 'Impulsive outlier' nell'evento >= max_q512_frac",
     lambda r, e, p: e.q512_frac >= p["max_q512_frac"]),
]

WARNINGS = [
    ("spostamento_centroide", lambda r, e, p: e.centr_shift > p["warn_centr_shift"]),
    ("impulsive_outlier_nell_evento", lambda r, e, p: e.q512_frac > 0),
    ("contaminazione_parziale", lambda r, e, p: r.crowdsap < p["warn_crowdsap"]),
]


def failures(r: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Una colonna booleana per criterio: True = la stella fallisce quel criterio."""
    e = event_table(r)
    return pd.DataFrame({c: test(r, e, p).fillna(False).astype(bool) for c, _, test in CRITERIA},
                        index=r.index)


def apply(r: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Ranking con evento guida, motivo di scarto (primo criterio fallito, '' se passa) e avvisi."""
    e = event_table(r)
    fail = failures(r, p)
    reason = pd.Series("", index=r.index)
    for c in reversed(fail.columns):  # all'indietro: vince il primo criterio fallito
        reason = reason.mask(fail[c], c)
    warn = pd.DataFrame({c: test(r, e, p).fillna(False).astype(bool) for c, test in WARNINGS}, index=r.index)
    warnings = warn.apply(lambda row: "; ".join(c for c in warn.columns if row[c]), axis=1)
    return r.assign(event=e.event, event_edge_d=e.edge_d, event_q512_frac=e.q512_frac,
                    event_centr_shift=e.centr_shift, artifact_reason=reason, warnings=warnings)


def counts(a: pd.DataFrame, p: dict, tops: list[int]) -> pd.DataFrame:
    """Per ogni criterio e popolazione (tutte, primi k del ranking): scartate in sequenza e
    fallimenti indipendenti. `a` è l'uscita di `apply`, in ordine di rango."""
    fail = failures(a, p)
    rows = []
    for c, desc, _ in CRITERIA:
        row = {"criterion": c, "description": desc}
        for name, n in [("all", len(a))] + [(f"top{k}", k) for k in tops]:
            row[f"{name}_sequential"] = int((a.artifact_reason.iloc[:n] == c).sum())
            row[f"{name}_independent"] = int(fail[c].iloc[:n].sum())
        rows.append(row)
    total = {"criterion": "sopravvissute", "description": "nessun criterio fallito"}
    for name, n in [("all", len(a))] + [(f"top{k}", k) for k in tops]:
        total[f"{name}_sequential"] = int((a.artifact_reason.iloc[:n] == "").sum())
    rows.append(total)
    return pd.DataFrame(rows)
