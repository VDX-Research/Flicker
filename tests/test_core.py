import json
import math

import pytest

from vdxtess import core


def row(**kw):
    r = {"rank": 3, "tic": 292292315, "prank_combined": 0.99871234, "event": "dip", "drivers": "dip_snr, bls_snr",
         "catalog_label": "assente", "catalog_explains": math.nan, "simbad_id": "TYC 1", "simbad_otype": "*",
         "vsx_name": math.nan, "vsx_type": math.nan, "toi": math.nan, "toi_disposition": math.nan,
         "variabile_vicina": math.nan, "sospetto_sistematica": False,
         "persistence": "persistenza non verificabile", "persistence_detail": "nessun altro settore",
         "warnings": math.nan}
    return r | kw


def test_ids_and_keys():
    assert core.dataset_id(103, 141) == "tess-s103-spoc-2min-dr141"
    assert core.result_id(103, 292292315.0) == "s103-tic-292292315"
    assert core.run_key("abc1234", "b8cb320b43cbd27f", 103, "sample") == "abc1234:b8cb320b43cbd27f:S103:sample"


@pytest.mark.parametrize("lab, ref", [("noto", "known"), ("noto con classe diversa", "known_other"), ("assente", "absent")])
def test_reference(lab, ref):
    assert core.result_message(row(catalog_label=lab), 103, 7)["properties"]["reference"] == ref


def test_result_message():
    m = core.result_message(row(), 103, 7)
    p = m["properties"]
    assert m["externalId"] == "s103-tic-292292315" and m["name"] == "TIC 292292315"
    assert p["score"] == 0.998712 and p["run"] == 7 and p["extra"] == {"tic_id": 292292315}
    assert m["defaults"] == {"review": "to_review"} and "review" not in p
    assert "extra" not in core.result_message(row(), 103, 7, with_extra=False)["properties"]
    json.dumps(m, allow_nan=False)  # nessun NaN nel messaggio


def test_note_skips_missing_and_never_says_discovery():
    n = core.result_note(row(sector=103))
    assert n.startswith("Candidato, rank 3 in S103") and "nan" not in n.lower()
    assert "VSX" not in n and "TOI" not in n and "SIMBAD: TYC 1 [*]" in n
    assert "persistenza: persistenza non verificabile (nessun altro settore)" in n
    assert "scoperta" not in n.lower()
    n = core.result_note(row(sector=103, vsx_name="X", vsx_type="EA", toi="1234.01", toi_disposition="PC",
                             sospetto_sistematica=True, catalog_explains="VSX EA"))
    assert "VSX: X [EA]" in n and "TOI 1234.01 PC" in n and "sospetto sistematica" in n and "(VSX EA)" in n


def test_run_message():
    m = core.run_message("abc1234", "fp", 103, "sample", {"a": 1}, 2980.0, 123.456, "ok", "proj", "tess-s103-spoc-2min-dr141")
    assert m["key"] == "abc1234:fp:S103:sample"
    assert m["payload"] == {"commit": "abc1234", "params": {"a": 1}, "items": 2980, "duration_s": 123.5, "outcome": "ok"}
    assert len(m["objects"]) == 2
    assert len(core.run_message("abc1234", "fp", 103, "sample", {}, 1, 1, "ok", "proj")["objects"]) == 1


def test_load_env(tmp_path, monkeypatch):
    monkeypatch.delenv("VDX_CORE_URL", raising=False)
    monkeypatch.setenv("VDX_TOKEN", "già impostato")
    f = tmp_path / ".env"
    f.write_text("# commento\nVDX_CORE_URL=example.org\nVDX_TOKEN='dal file'\n")
    core.load_env(f)
    import os
    assert os.environ["VDX_CORE_URL"] == "https://example.org"
    assert os.environ["VDX_TOKEN"] == "già impostato"
