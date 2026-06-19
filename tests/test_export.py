"""
Testes de schema dos artefatos de exportação (JSON/GeoJSON) consumidos pelo frontend.

Executa o pipeline real e valida a estrutura dos arquivos gerados.
Executar:  pytest tests/test_export.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as cfg

DOCS = cfg.DOCS_DATA_DIR


def _load(name):
    path = DOCS / name
    assert path.exists(), f"{name} não foi gerado — rode `python pipeline.py` primeiro"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_segments_schema():
    fc = _load("segments.geojson")
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 1000
    p = fc["features"][0]["properties"]
    for base in ("sre", "classe", "regional", "fonte"):
        assert base in p
    for t in cfg.TARGETS:
        for suf in ("_obs", "_pred", "_final", "_source"):
            assert f"{t}{suf}" in p, f"falta {t}{suf}"
    # geometria em [lon, lat]
    geom = fc["features"][0]["geometry"]
    assert geom["type"] in ("LineString", "MultiLineString")


def test_all_segments_have_geometry():
    fc = _load("segments.geojson")
    assert all(f.get("geometry") for f in fc["features"])


def test_model_metrics_schema():
    m = _load("model_metrics.json")
    assert "targets" in m and "slo" in m
    for t in cfg.TARGETS:
        tinfo = m["targets"][t]
        assert "r2_global" in tinfo and "mape" in tinfo
        assert "equations" in tinfo and tinfo["equations"]["excel"]
        assert isinstance(tinfo["features"], list) and len(tinfo["features"]) <= 6


def test_calibration_schema():
    c = _load("calibration_report.json")
    for t in cfg.TARGETS:
        tinfo = c["targets"][t]
        assert "metrics" in tinfo and "scatter_data" in tinfo
        if tinfo["scatter_data"]:
            row = tinfo["scatter_data"][0]
            for k in ("sre", "observed", "estimated", "residual"):
                assert k in row


def test_slo_all_approved():
    """Garante que o modelo publicado atende todos os critérios de aceite."""
    m = _load("model_metrics.json")
    assert m["slo"]["_todos_aprovados"] is True, "Algum target não atende o SLO"
