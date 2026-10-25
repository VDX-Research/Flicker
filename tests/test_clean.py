import numpy as np
import pandas as pd

from vdxtess.clean import clean, segments

P = dict(bitmask=16575, gap_days=0.5, min_segment_days=0.5, min_points=100)


def curve(n=2000, dt=2 / 1440, level=1000.0):
    t = 3000 + np.arange(n) * dt
    return pd.DataFrame({"time": t, "pdcsap_flux": np.full(n, level), "pdcsap_flux_err": np.ones(n),
                         "quality": np.zeros(n, dtype=np.int32)})


def test_segments_split_on_gaps():
    t = np.array([0, 0.1, 0.2, 1.0, 1.1, 3.0])
    assert segments(t, 0.5).tolist() == [0, 0, 0, 1, 1, 2]


def test_quality_mask_keeps_impulsive_outlier():
    df = curve()
    df.loc[10, "quality"] = 32      # desaturazione: tolta
    df.loc[20, "quality"] = 512     # impulsive outlier: resta
    d, n = clean(df, **P)
    assert n["drop_quality"] == 1
    assert 512 in d.quality.values


def test_nonfinite_dropped_and_counted():
    df = curve()
    df.loc[5:9, "pdcsap_flux"] = np.nan
    d, n = clean(df, **P)
    assert n["drop_nonfinite"] == 5 and n["n_clean"] == 1995
    assert np.isfinite(d.flux).all()


def test_each_segment_normalized_to_one():
    a, b = curve(1000, level=1000.0), curve(1000, level=2000.0)
    b["time"] += 5  # buco di ~3.6 giorni
    d, n = clean(pd.concat([a, b], ignore_index=True), **P)
    assert n["n_segments"] == 2
    assert np.allclose(d.groupby("segment").flux.median(), 1.0)


def test_short_segment_dropped():
    a, b = curve(1000), curve(100)  # 100 cadenze = 0.14 d
    b["time"] += 5
    d, n = clean(pd.concat([a, b], ignore_index=True), **P)
    assert n["drop_short_segment"] == 100 and n["n_segments"] == 1


def test_dip_preserved():
    df = curve()
    df.loc[1000:1010, "pdcsap_flux"] = 900.0  # transito del 10%: nessun clipping
    d, _ = clean(df, **P)
    assert d.flux.min() == 0.9


def test_too_few_points_excluded():
    d, n = clean(curve(50), **P)
    assert d is None and n["excluded"] in ("too_few_points",)


def test_nonpositive_median_excluded():
    df = curve(level=-5.0)  # fondo sovrasottratto: mediana negativa, non normalizzabile
    d, n = clean(df, **P)
    assert d is None and n["excluded"] == "nonpositive_median"
