import numpy as np
import pandas as pd
import pytest

from vdxtess.sample import allocate, stratified_sample

EDGES = [-99.0, 8.0, 10.0, 12.0, 99.0]


def population(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"tic": rng.permutation(np.arange(1, n + 1) * 7), "tmag": rng.uniform(5, 15, n)})


def test_allocate_sums_and_is_proportional():
    k = allocate(np.array([500, 300, 200]), 100)
    assert k.tolist() == [50, 30, 20]
    k = allocate(np.array([1, 1, 1]), 2)
    assert k.sum() == 2 and k.tolist() == [1, 1, 0]


def test_allocate_rejects_oversize():
    with pytest.raises(ValueError):
        allocate(np.array([3, 2]), 6)


def test_sample_reproducible_and_order_independent():
    df = population()
    a = stratified_sample(df, 300, 103, EDGES)
    b = stratified_sample(df.sample(frac=1, random_state=1), 300, 103, EDGES)
    assert len(a) == 300
    assert a.tic.tolist() == b.tic.tolist()
    assert stratified_sample(df, 300, 104, EDGES).tic.tolist() != a.tic.tolist()


def test_sample_strata_match_population():
    df = population()
    s = stratified_sample(df, 400, 1, EDGES)
    pop = pd.cut(df.tmag, EDGES, labels=False, right=False).value_counts(normalize=True).sort_index()
    got = s.stratum.value_counts(normalize=True).sort_index()
    assert np.allclose(pop.values, got.values, atol=0.01)
    assert s.tic.is_unique


def test_sample_skips_missing_tmag():
    df = population(100)
    df.loc[:9, "tmag"] = np.nan
    s = stratified_sample(df, 90, 0, EDGES)
    assert s.tmag.notna().all() and len(s) == 90
