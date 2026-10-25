import numpy as np
import pandas as pd
import pytest

from vdxtess import artifacts
from vdxtess.config import load

P = load()["artifacts"]


def star(**kw):
    """Una riga di ranking che passa tutti i criteri: dip lontano dal bordo, nessuna sistematica."""
    r = {"drivers": "log1p_dip_snr=+5.0, asinh_skew=-3.0, log_tail=+2.0", "skew": -1.0,
         "mad_std": 0.001, "crowdsap": 0.99, "diag_corr_centr": 0.05, "diag_corr_bkg": 0.02,
         "n_dips": 1, "dip_duration_h": 2.0, "diag_dip_edge_d": 3.0, "diag_dip_q512": 0, "diag_dip_centr_shift": 1.0,
         "n_flares": 0, "flare_duration_h": 0.0, "diag_flare_edge_d": np.nan, "diag_flare_q512": np.nan,
         "diag_flare_centr_shift": np.nan, "diag_bls_edge_d": 2.0}
    r.update(kw)
    return r


def table(*rows):
    return pd.DataFrame(list(rows))


@pytest.mark.parametrize("code, kw", [
    ("flusso_indefinito", {"mad_std": 0.5}),
    ("contaminazione", {"crowdsap": 0.3}),
    ("sistematica_centroide", {"diag_corr_centr": 0.8}),
    ("sistematica_fondo", {"diag_corr_bkg": -0.6}),
    ("evento_al_bordo", {"diag_dip_edge_d": 0.02}),
    ("evento_impulsive_outlier", {"diag_dip_q512": 40}),  # 40 cadenze su 60
])
def test_each_criterion_fires_alone(code, kw):
    a = artifacts.apply(table(star(), star(**kw)), P)
    assert list(a.artifact_reason) == ["", code]


def test_first_failing_criterion_wins():
    a = artifacts.apply(table(star(mad_std=0.5, crowdsap=0.3, diag_dip_edge_d=0.0),
                              star(crowdsap=0.3, diag_dip_edge_d=0.0)), P)
    assert list(a.artifact_reason) == ["flusso_indefinito", "contaminazione"]


def test_event_criteria_follow_the_driving_event():
    # brillamento al bordo, ma il punteggio è guidato dal dip: non è un artefatto
    flare_at_edge = {"n_flares": 1, "flare_duration_h": 0.5, "diag_flare_edge_d": 0.0, "diag_flare_q512": 15}
    a = artifacts.apply(table(star(**flare_at_edge),
                              star(**flare_at_edge, drivers="log1p_flare_snr=+6.0", skew=2.0)), P)
    assert list(a.event) == ["dip", "flare"]
    assert list(a.artifact_reason) == ["", "evento_al_bordo"]


def test_shape_driver_uses_skew_sign():
    a = artifacts.apply(table(star(drivers="asinh_skew=-20.0", skew=-3.0),
                              star(drivers="asinh_skew=+20.0", skew=3.0),
                              star(drivers="log_eta=-8.0")), P)
    assert list(a.event) == ["dip", "flare", ""]


def test_missing_diagnostics_do_not_discard():
    a = artifacts.apply(table(star(diag_corr_centr=np.nan, diag_corr_bkg=np.nan, crowdsap=np.nan),
                              star(n_dips=0, diag_dip_edge_d=0.0)), P)  # nessun dip rilevato: bordo ignorato
    assert list(a.artifact_reason) == ["", ""]


def test_warnings_do_not_discard():
    a = artifacts.apply(table(star(diag_dip_centr_shift=50.0, diag_dip_q512=3, crowdsap=0.7)), P)
    assert a.artifact_reason.iat[0] == ""
    assert a.warnings.iat[0] == "spostamento_centroide; impulsive_outlier_nell_evento; contaminazione_parziale"


def test_counts_consistent():
    rows = [star(), star(mad_std=0.5, crowdsap=0.3), star(crowdsap=0.3), star(diag_dip_edge_d=0.0), star()]
    a = artifacts.apply(table(*rows), P)
    c = artifacts.counts(a, P, [3]).set_index("criterion")
    # in sequenza ogni stella è contata una volta sola: la somma (con le sopravvissute) è il totale
    assert c.all_sequential.sum() == len(a) and c.top3_sequential.sum() == 3
    assert c.at["contaminazione", "all_sequential"] == 1 and c.at["contaminazione", "all_independent"] == 2
    assert c.at["sopravvissute", "all_sequential"] == 2
