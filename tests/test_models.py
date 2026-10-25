import numpy as np
import pandas as pd
import pytest

from vdxtess.config import load
from vdxtess.models import design_matrix, overlap, percentile_rank, rank

P = load()["models"]
AMPLITUDES = ["std", "mad_std", "p2p_std", "amp_90", "amp_98", "ls_amp", "bls_depth", "dip_depth", "flare_amp"]


def population(n=400, seed=0):
    """Tabella di caratteristiche sintetica: n stelle che sono solo rumore, con un po' di dispersione."""
    rng = np.random.default_rng(seed)
    s = 1e-3 * np.exp(rng.normal(0, 0.3, n))
    return pd.DataFrame({
        "tic": np.arange(1, n + 1), "tmag_hdr": rng.uniform(8, 18, n),
        "std": s * rng.normal(1, 0.03, n), "mad_std": s, "noise_ratio": rng.normal(0.95, 0.03, n),
        "p2p_std": s * rng.normal(1, 0.03, n), "amp_90": 3.29 * s * rng.normal(1, 0.03, n),
        "amp_98": 4.65 * s * rng.normal(1, 0.03, n), "skew": rng.normal(0, 0.03, n),
        "kurt": rng.normal(0, 0.05, n), "eta": rng.normal(2, 0.03, n),
        "ls_period": 10 ** rng.uniform(-1.3, 1.1, n), "ls_power": rng.uniform(0, 0.01, n),
        "ls_amp": 0.05 * s * rng.uniform(0.5, 1.5, n),
        "bls_period": 10 ** rng.uniform(-0.3, 1.1, n), "bls_depth": 0.3 * s * rng.uniform(0.5, 1.5, n),
        "bls_duration_h": rng.choice([1.0, 2, 4, 8], n), "bls_snr": rng.uniform(4, 7, n),
        "n_dips": np.zeros(n), "dip_depth": np.zeros(n), "dip_snr": np.zeros(n), "dip_duration_h": np.zeros(n),
        "n_flares": np.zeros(n), "flare_amp": np.zeros(n), "flare_snr": np.zeros(n),
        "flare_duration_h": np.zeros(n),
    })


@pytest.fixture(scope="module")
def eclipsing():
    """Popolazione più una binaria a eclisse: code pesanti, asimmetria negativa, dip forte."""
    f = population()
    i = 123
    s = f.at[i, "p2p_std"]
    f.loc[i, ["std", "amp_90", "amp_98", "skew", "kurt", "eta", "ls_power", "ls_amp"]] = \
        [80 * s, 30 * s, 400 * s, -4.0, 15.0, 0.02, 0.4, 60 * s]
    f.loc[i, ["bls_depth", "bls_snr", "n_dips", "dip_depth", "dip_snr", "dip_duration_h"]] = \
        [300 * s, 400, 3, 400 * s, 200, 4]
    return f, f.at[i, "tic"]


def test_injected_outlier_tops_both_methods(eclipsing):
    f, tic = eclipsing
    r, _ = rank(f, P)
    top = r.iloc[0]
    assert top.tic == tic
    assert top.prank_if == 1 and top.prank_lof == 1
    # i motivi indicati sono caratteristiche che l'iniezione ha davvero cambiato
    changed = {"log_std_p2p", "log_amp90_p2p", "log_tail", "asinh_skew", "asinh_kurt", "log_eta", "ls_power",
               "log_ls_amp_p2p", "log_bls_snr", "log1p_n_dips", "log1p_dip_snr", "log1p_dip_duration_h"}
    assert {d.split("=")[0] for d in top.drivers.split(", ")} <= changed


def test_deterministic(eclipsing):
    f, _ = eclipsing
    a, ca = rank(f, P)
    a2, ca2 = rank(f, P)
    pd.testing.assert_frame_equal(a, a2)
    assert ca == ca2
    # con le righe in altro ordine Isolation Forest estrae sottocampioni diversi: il primo resta
    b, _ = rank(f.sample(frac=1, random_state=1).reset_index(drop=True), P)
    assert b.tic.iat[0] == a.tic.iat[0]


def test_design_matrix_noise_invariant():
    """Stessa curva vista su una stella brillante e su una debole: gli ingressi coincidono."""
    f = population(50)
    faint = f.copy()
    faint[AMPLITUDES] *= 300
    pd.testing.assert_frame_equal(design_matrix(f), design_matrix(faint), rtol=1e-9)


def test_design_matrix_finite():
    z = design_matrix(population(50))
    assert np.isfinite(z.to_numpy()).all()


def test_percentile_rank():
    r = percentile_rank(np.array([0.3, 5.0, -1.0, 2.0]))
    assert list(r) == [0.5, 1.0, 0.25, 0.75]


def test_overlap():
    a = np.array([5, 4, 3, 2, 1.0])
    assert overlap(a, a, 2) == 2
    assert overlap(a, -a, 2) == 0
    assert overlap(a, np.array([5, 1, 4, 2, 3.0]), 3) == 2
