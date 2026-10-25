import numpy as np
import pandas as pd
import pytest

from vdxtess.config import load
from vdxtess.features import MODEL_FEATURES, edge_distance, events, features, flatten

P = load()["features"]
SIGMA = 1e-3


def curve(days=20.0, seed=0, gap=(9.5, 10.5)):
    """Curva pulita sintetica: rumore bianco gaussiano, due segmenti, centroidi e fondo costanti."""
    rng = np.random.default_rng(seed)
    t = 4000 + np.arange(0, days, 2 / 1440)
    t = t[(t - 4000 < gap[0]) | (t - 4000 > gap[1])]
    n = len(t)
    return pd.DataFrame({
        "time": t, "flux": 1 + rng.normal(0, SIGMA, n), "flux_err": np.full(n, SIGMA),
        "segment": (t - 4000 > gap[1]).astype(int), "quality": np.zeros(n, dtype=np.int32),
        "sap_flux": np.full(n, 1e4), "sap_bkg": rng.normal(100, 1, n),
        "mom_centr1": rng.normal(500, 0.01, n), "mom_centr2": rng.normal(600, 0.01, n),
        "pos_corr1": np.zeros(n), "pos_corr2": np.zeros(n),
    })


@pytest.fixture(scope="module")
def null():
    return features(curve(), P)


def test_null_curve(null):
    assert null["noise_ratio"] == pytest.approx(1, abs=0.05)
    assert null["eta"] == pytest.approx(2, abs=0.1)
    assert abs(null["skew"]) < 0.1
    assert null["n_dips"] == 0 and null["n_flares"] == 0
    assert null["bls_snr"] < 7
    assert all(np.isfinite(null[k]) for k in MODEL_FEATURES)


def test_sine_period_and_amplitude():
    d = curve()
    d["flux"] += 0.01 * np.sin(2 * np.pi * d.time / 3.7)
    f = features(d, P)
    assert f["ls_period"] == pytest.approx(3.7, rel=0.02)
    assert f["ls_amp"] == pytest.approx(0.01, rel=0.05)
    assert f["ls_power"] > 0.9 and f["eta"] < 0.1


def test_box_transit_found_by_bls(null):
    d = curve()
    period, t0, dur = 2.3, 4000.7, 2 / 24
    phase = ((d.time - t0 + period / 2) % period) - period / 2
    d.loc[np.abs(phase) < dur / 2, "flux"] -= 0.003
    f = features(d, P)
    assert f["bls_period"] == pytest.approx(period, rel=0.01)
    assert f["bls_depth"] == pytest.approx(0.003, rel=0.2)
    assert f["bls_snr"] > 5 * max(null["bls_snr"], 1)
    assert f["bls_n_transits"] >= 6


def test_flare_is_isolated_event_with_time():
    d = curve()
    i = np.searchsorted(d.time, 4005.0)
    d.loc[i:i + 9, "flux"] += 0.02 * np.exp(-np.arange(10) / 3)  # salita istantanea, decadimento
    f = features(d, P)
    assert f["n_flares"] == 1 and f["n_dips"] == 0
    assert f["t_flare"] == pytest.approx(d.time[i])
    assert f["flare_amp"] == pytest.approx(0.02, rel=0.1)
    assert f["skew"] > 0.5
    assert f["diag_flare_edge_d"] == pytest.approx(4.5, abs=0.01)  # dal buco a 4009.5


def test_single_point_is_not_an_event():
    d = curve()
    d.loc[1000, "flux"] -= 0.05  # raggio cosmico o outlier singolo
    r = flatten(d.flux.to_numpy(), d.segment.to_numpy(), 1.0) - 1
    found, _ = events(d.time.to_numpy(), r, 4.0, 3, -1)
    assert found == []


def test_event_flags_and_centroid_shift():
    d = curve()
    i = np.searchsorted(d.time, 4012.0)
    d.loc[i:i + 14, "flux"] -= 0.01
    d.loc[i:i + 14, "mom_centr1"] += 0.05  # la "stella" si sposta durante il dip: contaminazione
    d.loc[i:i + 2, "quality"] = 512
    f = features(d, P)
    assert f["n_dips"] == 1
    assert f["diag_dip_q512"] == 3
    assert f["diag_dip_centr_shift"] > 10


def test_flux_background_correlation():
    d = curve()
    ramp = np.sin(2 * np.pi * d.time / 0.3)  # sistematica veloce, sopravvive all'appiattimento
    d["flux"] += 0.005 * ramp
    d["sap_bkg"] = 100 + 10 * ramp
    assert features(d, P)["diag_corr_bkg"] > 0.9


def test_edge_distance():
    t = np.array([0.0, 1.0, 2.0, 5.0, 6.0])
    seg = np.array([0, 0, 0, 1, 1])
    assert edge_distance(1.0, t, seg) == 1.0
    assert edge_distance(5.5, t, seg) == 0.5
    assert np.isnan(edge_distance(np.nan, t, seg))
