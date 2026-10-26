import math

import pandas as pd
import pytest

from vdxtess import report


def test_cell():
    assert report.cell(None) == "—"
    assert report.cell(math.nan) == "—"
    assert report.cell("") == "—"
    assert report.cell(0.123456) == "0.1235"
    assert report.cell("a|b") == "a\\|b"
    assert report.cell(7) == "7"


def test_table():
    t = report.table([[1, None]], ["a", "b"]).splitlines()
    assert t == ["| a | b |", "|---|---|", "| 1 | — |"]


def test_pct_gb():
    assert report.pct(1, 4) == "25.0%"
    assert report.pct(1, 0) == "—"
    assert report.gb(5_780_177_280) == "5.78 GB"


@pytest.mark.parametrize("detail, expected", [
    ("S39: SNR 1376, S13: SNR 0", "1/2 sectors (S39)"),
    ("S39: SNR 9.9, S13: SNR 0", "0/2 sectors"),
    ("S39: SNR 10, S13: SNR 12", "2/2 sectors (S39, S13)"),
    ("nessun altro settore", "no other sector"),
    (math.nan, "—"),
])
def test_other_sectors(detail, expected):
    assert report.other_sectors(detail, 10.0) == expected


def test_version_key():
    v = ["spoc-5.0.10-20200904", "spoc-5.0.9-20200827", "spoc-5.0.124-20250919-1-g4fdf1a46a8"]
    assert sorted(v, key=report.version_key) == [v[1], v[0], v[2]]


def cands():
    return pd.DataFrame([
        {"rank": 1, "tic": 11, "event": "dip", "catalog_label": "assente", "persistence": "persistente",
         "persistence_detail": "S39: SNR 20", "simbad_id": "Gaia DR3 1", "simbad_otype": "*", "vsx_type": None,
         "tmag_hdr": 10.0, "variabile_vicina": None, "warnings": "contaminazione_parziale"},
        {"rank": 4, "tic": 22, "event": "flare", "catalog_label": "noto", "persistence": "persistenza non verificabile",
         "persistence_detail": "nessun altro settore", "simbad_id": "V* X", "simbad_otype": "Er*", "vsx_type": "UV",
         "tmag_hdr": 11.5, "variabile_vicina": None, "warnings": None},
        {"rank": 9, "tic": 33, "event": None, "catalog_label": "noto con classe diversa",
         "persistence": "non persistente", "persistence_detail": "S12: SNR 0", "simbad_id": "V* Y",
         "simbad_otype": "Ro*", "vsx_type": "ROT", "tmag_hdr": 9.0, "variabile_vicina": None, "warnings": None},
    ])


def test_label_by_event():
    rows = report.label_by_event(cands())
    assert rows[-1] == ["total", 1, 1, 1, 3]
    assert ["nessuno", 0, 1, 0, 1] in rows


def test_build_smoke():
    s = {
        "fase1": {"curves_in": 3, "curves_kept": 3, "excluded": {}, "n_raw": 100, "n_clean": 90,
                  "drop_quality": 5, "drop_nonfinite": 5, "drop_short_segment": 0},
        "fase2": {"ok": 3, "errors": 0},
        "fase3": {"spearman_if_lof": 0.4, "overlap_top50": 20, "overlap_top100": 50, "overlap_top300": 200,
                  "event_within_0.1d_of_edge_top": 0.3, "event_within_0.1d_of_edge_all": 0.05},
        "artefatti": {"rerank_on_star_survivors_shared": 2},
        "fase4": {"sospetto_sistematica": 0, "variabile_vicina": 0, "toi_table_downloaded": "2026-10-01",
                  "other_sector_curves": 2, "other_sector_errors": 0, "other_sector_data_rel": [30, 60],
                  "other_sector_spoc": ["spoc-5.0.10-1", "spoc-5.0.9-1"]},
    }
    products = {"cadence_s": 120, "data_release": [141], "spoc_version": ["spoc-5.0.126-20251212"],
                "file_date": ["2025-12-12"], "downloaded_from": "a", "downloaded_to": "b", "n_files": 3,
                "bytes": 1e9, "quality_bitmask": 175}
    counts = pd.DataFrame([
        {"criterion": "contaminazione", "description": "x", "all_sequential": 1, "all_independent": 1,
         "top50_sequential": 0, "top50_independent": 0},
        {"criterion": "sopravvissute", "description": "x", "all_sequential": 3, "all_independent": None,
         "top50_sequential": 3, "top50_independent": None},
    ])
    meta = {"sector": 103, "label": "sample", "frozen": False, "fingerprint": "f", "commit": "c",
            "generated_at": "now", "min_snr": 10.0, "match_arcsec": 5.0, "neighbor_arcsec": 42.0,
            "sectors_max": 104}
    md = report.build(s, products, cands(), counts, {"simbad": ("t0", "t1")}, meta, {11: "figures/x.png"})
    assert "## 12." in md
    assert "**1 absent**" in md
    assert "[plot](figures/x.png)" in md
    assert "`spoc-5.0.9-1`, `spoc-5.0.10-1`" in md
    assert "CROWDSAP" in md and "| x |" not in md  # descrizione inglese, non quella del CSV
    assert "nessun altro settore" not in md
    assert "scoperta" not in md.lower() and "discovery." not in md.replace("not a discovery.", "")
