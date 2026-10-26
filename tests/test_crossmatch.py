import numpy as np
import pandas as pd
import pytest

from vdxtess import crossmatch
from vdxtess.config import load

P = load()["crossmatch"]
NONE = pd.DataFrame()


def simbad(*rows):
    return pd.DataFrame([dict(zip(("main_id", "otype", "sep_arcsec"), r)) for r in rows])


def vsx(*rows):
    return pd.DataFrame([dict(zip(("Name", "Type", "Period", "sep_arcsec"), r)) for r in rows])


def toi(*rows):
    return pd.DataFrame([dict(zip(("TOI", "TFOPWG Disposition"), r)) for r in rows])


@pytest.mark.parametrize("otype, norm", [("EB?", "EB*"), ("Fl?", "Fl*"), ("Y*?", "Y*O"), ("V*?", "V*"), ("PM*", "PM*"), ("", ""), (np.nan, "")])
def test_simbad_candidate_type(otype, norm):
    assert crossmatch.simbad_type(otype) == norm


@pytest.mark.parametrize("vtype, event, ok", [
    ("EA/DM", "dip", True), ("EW", "bls", True), ("ELL", "dip", False), ("ROT:", "dip", False),
    ("BY+UV", "flare", True), ("UV:", "flare", True), ("EA", "flare", False), ("INST", "dip", True),
    (np.nan, "dip", False),  # tipo vuoto letto dalla cache come NaN
])
def test_vsx_explains(vtype, event, ok):
    assert crossmatch.vsx_explains(vtype, event) is ok


def test_label_noto():
    r = crossmatch.label("dip", simbad(("V* X", "EB?", 1.0)), NONE, NONE, P)
    assert r["catalog_label"] == "noto" and r["catalog_explains"] == "SIMBAD EB*"


def test_label_other_class():
    r = crossmatch.label("dip", simbad(("V* X", "RR*", 1.0)), vsx(("X", "ROT", 2.3, 1.0)), NONE, P)
    assert r["catalog_label"] == "noto con classe diversa"


def test_supergiant_is_not_a_variability_class():
    assert crossmatch.label("dip", simbad(("HD 1", "s*b", 1.0)), NONE, NONE, P)["catalog_label"] == "assente"


def test_label_plain_star_is_absent():
    r = crossmatch.label("dip", simbad(("TYC 1", "*", 0.5), ("TYC 2", "PM*", 3.0)), NONE, NONE, P)
    assert r["catalog_label"] == "assente" and r["simbad_id"] == "TYC 1" and r["variabile_vicina"] == ""


def test_label_outside_match_radius_is_neighbor():
    r = crossmatch.label("dip", simbad(("TYC 1", "*", 0.5), ("V* Y", "EB*", 30.0)),
                         vsx(("Y", "EA", 1.1, 30.0)), NONE, P)
    assert r["catalog_label"] == "assente"
    assert "V* Y (EB*, 30\")" in r["variabile_vicina"] and "Y (EA, 30\")" in r["variabile_vicina"]


def test_toi_explains_dip_not_flare():
    t = toi((1234.01, "PC"))
    assert crossmatch.label("dip", NONE, NONE, t, P)["catalog_label"] == "noto"
    r = crossmatch.label("flare", NONE, NONE, t, P)
    assert r["catalog_label"] == "noto con classe diversa" and r["toi"] == "1234.01"


def test_tess_eb_explains_dip_not_flare():
    eb = pd.DataFrame({"TIC": ["0133701671"], "Per": [4.6955]})
    r = crossmatch.label("dip", simbad(("HD 1", "*", 0.5)), NONE, NONE, P, eb)
    assert r["catalog_label"] == "noto" and r["catalog_explains"] == "TESS EB" and r["tess_eb_period_d"] == 4.6955
    assert crossmatch.label("flare", NONE, NONE, NONE, P, eb)["catalog_label"] == "noto con classe diversa"
    assert np.isnan(crossmatch.label("dip", NONE, NONE, NONE, P)["tess_eb_period_d"])


def test_any_catalog_explaining_wins():
    r = crossmatch.label("flare", simbad(("V* X", "EB*", 1.0)), vsx(("X", "EA+UV", 1.0, 1.0)), NONE, P)
    assert r["catalog_label"] == "noto" and r["catalog_explains"] == "VSX EA+UV"


def pop_ccd(times, camera=1, ccd=1):
    return pd.DataFrame({"tic": range(100, 100 + len(times)), "camera": camera, "ccd": ccd,
                         "n_dips": 1, "t_dip": times, "n_flares": 0, "t_flare": np.nan})


def test_coincidences_flags_clustered_epoch():
    rng = np.random.default_rng(0)
    spread = rng.uniform(4150, 4177, 200)
    pop = pd.concat([pop_ccd(np.r_[spread, [4160.0] * 10, 4150, 4177])])
    cand = pd.DataFrame({"tic": [1, 2], "event": ["dip", "dip"], "camera": 1, "ccd": 1,
                         "t_dip": [4160.01, 4163.3], "t_flare": np.nan})
    c = crossmatch.coincidences(cand, pop, P).set_index("tic")
    assert c.at[1, "coinc_n"] >= 10 and c.at[1, "sospetto_sistematica"]
    assert not c.at[2, "sospetto_sistematica"]


def test_coincidences_other_ccd_and_events_ignored():
    pop = pd.concat([pop_ccd([4160.0] * 10, ccd=2), pop_ccd([4150.0, 4177.0])])
    cand = pd.DataFrame({"tic": [1, 2], "event": ["dip", "bls"], "camera": 1, "ccd": 1,
                         "t_dip": [4160.0, 4160.0], "t_flare": np.nan})
    c = crossmatch.coincidences(cand, pop, P).set_index("tic")
    assert c.at[1, "coinc_n"] == 0 and not c.at[1, "sospetto_sistematica"]
    assert np.isnan(c.at[2, "coinc_n"])


@pytest.mark.parametrize("s, out", [("103 76 105 104", [76, 104]), (np.nan, []), ("103", [])])
def test_other_sectors(s, out):
    assert crossmatch.other_sectors(s, 103, 104) == out


def per(*rows):
    return pd.DataFrame([dict(zip(("sector", "n_dips", "dip_snr", "n_flares", "flare_snr", "bls_snr", "error"), r))
                         for r in rows])


def test_persistence_labels():
    assert crossmatch.persistence("dip", [], NONE, P)["persistence"] == "persistenza non verificabile"
    rows = per((76, 1, 25.0, 0, 0.0, 5.0, np.nan), (104, 0, 0.0, 2, 30.0, 4.0, np.nan))
    assert crossmatch.persistence("dip", [76, 104], rows, P)["persistence"] == "persistente"
    assert crossmatch.persistence("flare", [76, 104], rows, P)["persistence"] == "persistente"
    assert crossmatch.persistence("bls", [76, 104], rows, P)["persistence"] == "non persistente"
    assert crossmatch.persistence("", [76, 104], rows, P)["persistence"] == "persistenza non verificabile"


def test_persistence_weak_or_unreadable():
    weak = per((76, 1, 6.0, 0, 0.0, 0.0, np.nan))
    assert crossmatch.persistence("dip", [76], weak, P)["persistence"] == "non persistente"
    bad = per((76, np.nan, np.nan, np.nan, np.nan, np.nan, "HTTPError"))
    r = crossmatch.persistence("dip", [76], bad, P)
    assert r["persistence"] == "persistenza non verificabile" and r["persistence_detail"] == "altri settori illeggibili"
