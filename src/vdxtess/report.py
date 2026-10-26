"""Report per l'astronomo (FASE 6): funzioni pure che trasformano riepiloghi e tabelle delle fasi
in Markdown. Nessun numero è scritto a mano: tutto viene da data/summary_*, data/*.csv e
data/products_*.json, così il report del campione e quello della corsa finale si confrontano riga per riga."""
import math

import pandas as pd

LABELS = ("noto", "noto con classe diversa", "assente")
PERSISTENCE = ("persistente", "non persistente", "persistenza non verificabile")


def cell(v) -> str:
    """Valore di una cella Markdown: vuoti e NaN come trattino, `|` protetto."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == "":
        return "—"
    if isinstance(v, float):
        v = f"{v:.4g}"
    return str(v).replace("|", "\\|")


def table(rows: list[list], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def fmt_int(n) -> str:
    return f"{int(n):,}"


def pct(a, b) -> str:
    return f"{100 * a / b:.1f}%" if b else "—"


def gb(n_bytes) -> str:
    return f"{n_bytes / 1e9:.2f} GB"


def label_by_event(cand: pd.DataFrame) -> list[list]:
    """Etichetta di catalogo per tipo di evento guida, con riga dei totali."""
    ct = pd.crosstab(cand.event.fillna("nessuno"), cand.catalog_label).reindex(columns=LABELS, fill_value=0)
    rows = [[ev] + [int(x) for x in ct.loc[ev]] + [int(ct.loc[ev].sum())] for ev in ct.index]
    return rows + [["total"] + [int(ct[c].sum()) for c in LABELS] + [int(ct.values.sum())]]


def other_sectors(detail, min_snr: float) -> str:
    """Settori con l'evento sopra soglia da `persistence_detail` ("S39: SNR 1376, S13: SNR 0")."""
    if not isinstance(detail, str) or "SNR" not in detail:
        return "no other sector" if detail == "nessun altro settore" else cell(detail)
    hits = []
    for part in detail.split(","):
        s, _, snr = part.strip().partition(": SNR ")
        if snr and float(snr) >= min_snr:
            hits.append(s)
    n = detail.count("SNR")
    return f"{len(hits)}/{n} sectors ({', '.join(hits)})" if hits else f"0/{n} sectors"


def candidate_rows(cand: pd.DataFrame, min_snr: float, figures: dict[int, str] | None = None) -> list[list]:
    figures = figures or {}
    rows = []
    for r in cand.itertuples():
        tic = int(r.tic)
        fig = f"[plot]({figures[tic]})" if tic in figures else ""
        rows.append([int(r.rank), tic, r.event, r.simbad_id, r.simbad_otype, r.vsx_type,
                     f"{r.tmag_hdr:.2f}", r.persistence, other_sectors(r.persistence_detail, min_snr),
                     r.variabile_vicina, r.warnings, fig])
    return rows


def cand_headers(neighbor_arcsec: float) -> list[str]:
    return ["rank", "TIC", "event", "SIMBAD", "otype", "VSX", "Tmag", "persistence",
            "other sectors with event", f"known variable within {neighbor_arcsec:g}\"", "warnings", "figure"]


# descrizioni in inglese dei criteri; il CSV delle fasi le ha in italiano
CRITERIA = {
    "flusso_indefinito": "robust relative scatter > `max_mad_std`: PDCSAP median close to zero",
    "contaminazione": "`CROWDSAP` < `min_crowdsap`: less than half the aperture flux is from the target",
    "sistematica_centroide": "|r| between flux and a centroid > `max_corr_centr`",
    "sistematica_fondo": "|r| between flux and background > `max_abs_corr_bkg`",
    "evento_al_bordo": "the driving event is within `min_edge_d` of a segment edge",
    "evento_impulsive_outlier": "fraction of 'Impulsive outlier' cadences in the event >= `max_q512_frac`",
    "sopravvissute": "no criterion failed (survivors)",
}


def artifact_rows(counts: pd.DataFrame) -> list[list]:
    rows = []
    for r in counts.itertuples():
        ind = "" if pd.isna(r.all_independent) else int(r.all_independent)
        t50 = "" if pd.isna(r.top50_independent) else int(r.top50_independent)
        rows.append([f"`{r.criterion}`", CRITERIA.get(r.criterion, r.description), int(r.all_sequential), ind,
                     int(r.top50_sequential), t50])
    return rows


def version_key(v: str) -> tuple:
    """Ordine numerico delle versioni SPOC: spoc-5.0.9 prima di spoc-5.0.10."""
    head = v.removeprefix("spoc-").split("-")[0]
    return tuple(int(x) for x in head.split(".") if x.isdigit()), v


def build(s: dict, products: dict, cand: pd.DataFrame, counts: pd.DataFrame, queries: dict,
          meta: dict, figures: dict[int, str] | None = None) -> str:
    """Report completo. `s` = riepiloghi per fase (fase1..fase5, artefatti), `queries` = date min/max
    delle interrogazioni per catalogo, `meta` = sector, label, frozen, fingerprint, commit, generated_at e le soglie min_snr, match_arcsec,
    neighbor_arcsec, sectors_max (da [crossmatch] e [dataset] della configurazione)."""
    f1, f2, f3, art, f4 = s["fase1"], s["fase2"], s["fase3"], s["artefatti"], s["fase4"]
    f5 = s.get("fase5")
    sector, label = meta["sector"], meta["label"]
    n_cand = len(cand)
    lab = cand.catalog_label.value_counts()
    absent = cand[cand.catalog_label == "assente"]
    other = cand[cand.catalog_label == "noto con classe diversa"]
    unverifiable = cand[cand.persistence == "persistenza non verificabile"]
    nonpers = cand[cand.persistence == "non persistente"]
    absent_pers = absent.persistence.value_counts()
    surv = counts.loc[counts.criterion == "sopravvissute"].iloc[0]
    sample = label == "sample"
    snr, r_match, r_nb, smax = meta["min_snr"], meta["match_arcsec"], meta["neighbor_arcsec"], meta["sectors_max"]
    heads = cand_headers(r_nb)

    L = [f"# TESS Sector {sector}: anomalous light-curve candidates ({'development sample' if sample else 'all targets'})", ""]
    L += [f"Generated {meta['generated_at']} by `scripts/fase6.py` at commit `{meta['commit']}`, "
          f"parameters fingerprint `{meta['fingerprint']}`.", ""]
    L += ["> Everything in this report is a **candidate for verification**, not a discovery. "
          "A label `assente` only means that no variability class was found in the four catalogues queried.", ""]

    L += ["## 1. Summary", ""]
    L += [f"- {fmt_int(f1['curves_in'])} light curves of sector {sector} were analysed; "
          f"{fmt_int(f2['ok'])} had cleaned data and features.",
          f"- After artifact rejection {fmt_int(surv.all_sequential)} stars survived; the first "
          f"{n_cand} in the anomaly ranking are the candidates.",
          f"- Catalogue labels: **{lab.get('noto', 0)} known** (a catalogue class explains the event), "
          f"**{lab.get('noto con classe diversa', 0)} known with a different class**, "
          f"**{lab.get('assente', 0)} absent** from SIMBAD, VSX, TOI and the TESS EB catalogue as variables.",
          f"- Of the {len(absent)} absent candidates, {absent_pers.get('persistente', 0)} show the same event type "
          f"in another sector, {absent_pers.get('non persistente', 0)} do not, and "
          f"{absent_pers.get('persistenza non verificabile', 0)} cannot be checked.",
          f"- {f4['sospetto_sistematica']} candidates are flagged as a likely systematic (coincident events on the same CCD); "
          f"{f4['variabile_vicina']} have a known variable star within {r_nb:g}\"."]
    if sample:
        L += ["- This is the **development sample**: parameters were tuned on it, so its numbers are not an "
              "unbiased estimate. The final run on all targets uses the same parameters, frozen."]
    L += [""]

    L += ["## 2. Data and versions", ""]
    L += [table([
        ["Sector", sector],
        ["Product", f"SPOC light curves, {products['cadence_s']} s cadence, PDCSAP flux"],
        ["Data release", ", ".join(f"DR{x}" for x in products["data_release"])],
        ["SPOC version", ", ".join(f"`{x}`" for x in sorted(products["spoc_version"], key=version_key))],
        ["File date (header DATE)", ", ".join(products["file_date"])],
        ["Downloaded", f"{products['downloaded_from']} – {products['downloaded_to']}"],
        ["Files", f"{fmt_int(products['n_files'])} ({gb(products['bytes'])})"],
        ["QUALITY bitmask rejected", products["quality_bitmask"]],
    ] + [[f"{k.upper() if k != 'tess_eb' else 'TESS EB (Prša et al. 2022)'} queried", f"{a} – {b}"]
         for k, (a, b) in sorted(queries.items())]
      + [["TOI table (ExoFOP) downloaded", f4["toi_table_downloaded"]],
         ["Other-sector curves (persistence)", f"{f4['other_sector_curves']} curves, {f4['other_sector_errors']} errors, "
          f"data releases {min(f4['other_sector_data_rel'])}–{max(f4['other_sector_data_rel'])}"],
         ["Other-sector SPOC versions", ", ".join(f"`{x}`" for x in sorted(f4["other_sector_spoc"], key=version_key))]],
      ["", ""]), ""]
    L += [f"Persistence uses only SPOC light curves (2 min and 20 s) of sectors up to {smax}, the last with "
          f"published release notes. Later sectors are not used (see section 12).", ""]

    L += ["## 3. Protocol", ""]
    if sample:
        L += [f"Development sample of {fmt_int(f1['curves_in'])} targets (seed {sector}, stratified by Tmag). "
              f"All thresholds were tuned on it. `frozen = {str(meta['frozen']).lower()}`."]
    else:
        L += [f"**Tuned then frozen.** All thresholds were tuned on the development sample of 3,000 targets "
              f"(seed {sector}, stratified by Tmag); then `frozen = true` was set and this single run on all "
              f"{fmt_int(f1['curves_in'])} targets was made without changing anything."]
    L += [f"Every phase records the parameters fingerprint; all phases of this report share `{meta['fingerprint']}`.", ""]

    L += ["## 4. Cleaning, features, models", ""]
    L += [table([
        ["Light curves in / kept", f"{fmt_int(f1['curves_in'])} / {fmt_int(f1['curves_kept'])}"],
        ["Excluded", ", ".join(f"{k}: {v}" for k, v in f1["excluded"].items()) or "—"],
        ["Cadences raw / clean", f"{fmt_int(f1['n_raw'])} / {fmt_int(f1['n_clean'])} ({pct(f1['n_clean'], f1['n_raw'])})"],
        ["Dropped by QUALITY flags", fmt_int(f1["drop_quality"])],
        ["Dropped as non-finite flux", fmt_int(f1["drop_nonfinite"])],
        ["Dropped in short segments", fmt_int(f1["drop_short_segment"])],
        ["Features ok / errors", f"{fmt_int(f2['ok'])} / {f2['errors']}"],
        ["Spearman ρ, Isolation Forest vs LOF", f"{f3['spearman_if_lof']:.2f}"],
        ["IF/LOF overlap in top 50 / 100 / 300", f"{f3['overlap_top50']} / {f3['overlap_top100']} / {f3['overlap_top300']}"],
        ["Driving event within 0.1 d of an edge, top vs all",
         f"{f3['event_within_0.1d_of_edge_top']:.2f} vs {f3['event_within_0.1d_of_edge_all']:.3f}"],
    ], ["", ""]), ""]
    L += ["The two models disagree substantially, so the ranking uses the mean of their percentile ranks.", ""]

    L += ["## 5. Artifact rejection", ""]
    L += ["Criteria are applied in order and a star is removed by the first it fails (*sequential*); "
          "*independent* counts how many stars would fail each criterion alone.", ""]
    L += [table(artifact_rows(counts), ["criterion", "rejects when", "all, sequential", "all, independent",
                                        "top 50, sequential", "top 50, independent"]), ""]
    L += [f"{art['rerank_on_star_survivors_shared']} of the {n_cand} candidates are also in the top {n_cand} "
          "when the models are refit on the survivors of the star criteria only.", ""]

    L += ["## 6. Catalogue labels", ""]
    L += ["Labels are the pipeline codes: `noto` = known, a catalogue class explains the driving event; "
          "`noto con classe diversa` = known with a class that does not explain it; `assente` = no variability "
          "class in any catalogue queried. Persistence: `persistente` = the same event type in another sector, "
          "`non persistente` = other sectors exist but show nothing, `persistenza non verificabile` = no usable "
          "other sector.", ""]
    L += [table(label_by_event(cand), ["driving event", *LABELS, "total"]), ""]
    L += [table([[p, int((cand.persistence == p).sum())] for p in PERSISTENCE], ["persistence", "candidates"]), ""]

    L += [f"## 7. Candidates absent from the catalogues ({len(absent)})", ""]
    L += ["Not in SIMBAD, VSX, TOI or the TESS EB catalogue as variables. The SIMBAD column is the identifier "
          "of a plain star at the position, if any.", ""]
    L += [f"`rank` is the position in the anomaly ranking before artifact rejection; `other sectors with event` "
          f"counts sectors where the same event type reaches SNR ≥ {snr:g}.", ""]
    L += [table(candidate_rows(absent, snr, figures), heads), ""]

    L += [f"## 8. Candidates known with a different class ({len(other)})", ""]
    L += ["The target has a catalogued variability class that does not explain the driving event "
          "(for example a rotator with a dip).", ""]
    L += [table(candidate_rows(other, snr), heads), ""]

    L += [f"## 9. Persistence not verifiable ({len(unverifiable)})", ""]
    L += [f"No other SPOC sector up to {smax}, or none readable. These candidates are **kept**; "
          "they need another sector or other photometry.", ""]
    L += [table(candidate_rows(unverifiable, snr, figures), heads) if len(unverifiable) else "None.", ""]
    if len(nonpers):
        L += [f"Not persistent ({len(nonpers)}): other sectors exist but none shows the same event type with SNR ≥ {snr:g}: "
              + ", ".join(f"TIC {int(t)} ({c})" for t, c in zip(nonpers.tic, nonpers.catalog_label)) + ".", ""]

    L += ["## 10. Flags", ""]
    warn = cand.warnings.dropna().str.split(";").explode().str.strip().value_counts()
    L += [table([[f"`sospetto_sistematica`", f4["sospetto_sistematica"]],
                 [f"known variable within {r_nb:g}\" (`variabile_vicina`)", f4["variabile_vicina"]]]
                + [[f"warning `{k}`", int(v)] for k, v in warn.items()], ["flag", "candidates"]), ""]
    L += ["Warnings do not reject; they say what to check by hand (pixel-level data, centroids, neighbours).", ""]

    L += ["## 11. Limits", ""]
    L += ["- One sector, 2-min SPOC targets only: stars without a 2-min target are not searched.",
          "- The anomaly ranking is unsupervised: it finds what is rare in this population, not what is new. "
          "Most top-ranked stars are known variables.",
          f"- Catalogue matching is by position ({r_match:g}\") for SIMBAD and VSX and by TIC for TOI and the TESS EB catalogue "
          "(sectors 1–26 only). Catalogues not queried (Gaia DR3 variability, ASAS-SN, ZTF, KELT) may already "
          "list some `assente` candidates. Answers are cached at the query dates above.",
          "- TESS pixels are 21\": a nearby star can be the true source. Crowding is only filtered by `CROWDSAP`; "
          "no pixel-level centroid analysis was done.",
          f"- Persistence checks only the same event type with SNR ≥ {snr:g}, and only in sectors up to {smax}.",
          "- Thresholds were tuned on the development sample."
          + (" The sample numbers are therefore optimistic." if sample else ""), ""]

    L += ["## 12. VDX Core and next version", ""]
    if f5:
        L += [f"- Registered in VDX Core: run id {f5['run_id']} ({f5['run_status']}), "
              f"{f5['results']['accepted']}/{f5['results']['sent']} results accepted, "
              f"plots attached {f5['plots']['attached']} + {f5['plots']['duplicate']} already present, "
              f"dataset linked: {'yes' if f5['dataset_linked'] else 'no'}."]
        if f5["warnings"]:
            L += ["- Pipeline log messages from the send (Italian, verbatim):"]
            L += [f"  - `{w}`" for w in f5["warnings"]]
    else:
        L += ["- Not yet registered in VDX Core (`scripts/fase5.py`)."]
    L += [f"- v2: add sectors after {smax} (105–107 have data on MAST) to the persistence check once their release notes are published; "
          "query Gaia DR3 variability and ASAS-SN; pixel-level centroid tests for the absent candidates.", ""]
    return "\n".join(L)
