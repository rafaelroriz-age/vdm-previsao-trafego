"""
Testes unitários e de integração do pipeline de regressão.

Executar:  pytest -q   (a partir da raiz do projeto)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_prep import (
    apply_boolean_merge,
    apply_group_merge,
    feature_engineering,
    normalize_group_label,
)
from src.regression import (
    backward_elimination_ols,
    detect_column_types,
    encode_features,
    run_regression_pipeline,
)
from src.formulas import equation_to_excel, equation_to_latex_inline


# ── detect_column_types ──────────────────────────────────────────────────────
def test_detect_numeric():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10, 20, 30]})
    r = detect_column_types(df)
    assert r["a"] == "numeric" and r["b"] == "numeric"


def test_detect_boolean():
    assert detect_column_types(pd.DataFrame({"f": [True, False, True]}))["f"] == "boolean"
    assert detect_column_types(pd.DataFrame({"f": [0, 1, 0]}))["f"] == "boolean"


def test_detect_categorical():
    assert detect_column_types(pd.DataFrame({"c": ["A", "B", "A"]}))["c"] == "categorical"


# ── normalize_group_label ─────────────────────────────────────────────────────
def test_normalize_group_label():
    assert normalize_group_label(1.0) == "1"
    assert normalize_group_label(2) == "2"
    assert normalize_group_label("2+3") == "2+3"
    assert normalize_group_label(3.5) == "3.5"


# ── apply_boolean_merge ───────────────────────────────────────────────────────
def test_apply_boolean_merge():
    df = pd.DataFrame({"situacao": ["DUP", "PAV", "DUP", "EOD"]})
    out = apply_boolean_merge(df, {"situacao": (["DUP"], "situacao_is_dup")})
    assert out["situacao_is_dup"].tolist() == [True, False, True, False]
    assert "situacao" in out.columns  # original mantida


# ── apply_group_merge ─────────────────────────────────────────────────────────
def test_apply_group_merge():
    df = pd.DataFrame({"regional_macro": [1.0, 2.0, 3.0, 5.0]})
    out = apply_group_merge(df, "regional_macro", [(["2", "3"], "2+3")])
    assert out["regional_macro"].tolist() == ["1", "2+3", "2+3", "5"]


def test_apply_group_merge_empty():
    df = pd.DataFrame({"regional_macro": [1.0, 2.0]})
    out = apply_group_merge(df, "regional_macro", [])
    assert out["regional_macro"].tolist() == ["1", "2"]


# ── encode_features ───────────────────────────────────────────────────────────
def test_encode_onehot():
    df = pd.DataFrame({"perim_urb": ["s", "n", "s"]})
    enc, encoders = encode_features(df, ["perim_urb"], {"perim_urb": "onehot"})
    assert "perim_urb_s" in enc.columns
    assert enc["perim_urb_s"].tolist() == [1.0, 0.0, 1.0]


def test_encode_numeric_passthrough():
    df = pd.DataFrame({"go": [10, 20, 30]})
    enc, _ = encode_features(df, ["go"], {})
    assert enc["go"].tolist() == [10.0, 20.0, 30.0]


# ── backward_elimination_ols ──────────────────────────────────────────────────
def test_backward_elimination_keeps_signal():
    rng = np.random.default_rng(0)
    n = 200
    x1 = rng.normal(size=n)
    noise = rng.normal(size=n)
    y = 3.0 * x1 + 0.5 * rng.normal(size=n)
    X = np.column_stack([x1, noise])
    kept_idx, kept_names, res = backward_elimination_ols(X, y, ["signal", "noise"], 0.05)
    assert "signal" in kept_names
    assert res is not None


def test_backward_elimination_mandatory():
    rng = np.random.default_rng(1)
    n = 100
    X = rng.normal(size=(n, 2))
    y = rng.normal(size=n)  # ruído puro
    kept_idx, kept_names, res = backward_elimination_ols(
        X, y, ["a", "b"], 0.05, mandatory_features=["a"]
    )
    assert "a" in kept_names  # mandatória nunca removida


# ── formulas ──────────────────────────────────────────────────────────────────
def test_equation_to_excel():
    eq = "log(ŷ(vmd)) = +1.5000\n        + 0.3000 × go\n        - 0.2000 × situacao_is_dup"
    out = equation_to_excel(eq)
    assert out.startswith("=1,5000")
    assert "go" in out and "situacao_is_dup" in out


def test_equation_to_latex_inline():
    eq = "log(ŷ(vmd)) = +1.5000\n        + 0.3000 × go"
    out = equation_to_latex_inline(eq)
    assert "\\hat{y}" in out and "\\times" in out


# ── integração: run_regression_pipeline ───────────────────────────────────────
def _synthetic_df(n=120, seed=42):
    rng = np.random.default_rng(seed)
    go = rng.integers(1, 50, size=n).astype(float)
    pib = rng.uniform(1e5, 1e7, size=n)
    region = rng.choice(["1", "2+3", "4", "5"], size=n)
    base = 2.0 + 0.01 * go + 0.3 * np.log1p(pib)
    y = np.exp(base + rng.normal(0, 0.3, size=n))
    df = pd.DataFrame({
        "sre": [f"S{i:04d}" for i in range(n)],
        "go": go, "media_pib": pib, "regional_macro": region, "vmd": y,
    })
    # esconde 30% dos alvos (a prever)
    miss = rng.choice(n, size=int(n * 0.3), replace=False)
    df.loc[miss, "vmd"] = np.nan
    return df


def test_pipeline_runs_and_fills():
    df = _synthetic_df()
    df = feature_engineering(df, ["vmd"], "regional_macro")
    res = run_regression_pipeline(
        df=df, group_col="regional_macro", targets=["vmd"],
        features_per_target={"vmd": ["go", "log_media_pib"]},
        encoding_choices={}, pvalue_threshold=0.2, log_transform=True, max_features=4,
    )
    out = res["df_result"]
    assert out["vmd"].notna().all()           # todos preenchidos
    assert (out["vmd"] >= 0).all()            # sem negativos
    assert not res["equations_df"].empty


def test_pipeline_no_negative_predictions():
    df = _synthetic_df(seed=7)
    df = feature_engineering(df, ["vmd"], "regional_macro")
    res = run_regression_pipeline(
        df=df, group_col="regional_macro", targets=["vmd"],
        features_per_target={"vmd": ["go", "log_media_pib"]},
        encoding_choices={}, pvalue_threshold=0.2, log_transform=True,
    )
    assert (res["df_result"]["vmd"] >= 0).all()
