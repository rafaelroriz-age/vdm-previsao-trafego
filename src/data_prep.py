"""
data_prep.py
------------
Carregamento do dataset e transformações de pré-modelagem:
boolean-merge, group-merge e feature engineering.

Portado de `vdm-regressao-previsto/pipeline.py` (somente as partes de dados).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def load_dataset(path) -> pd.DataFrame:
    """Carrega o dataset oficial (1 linha por SRE) e normaliza a chave `sre`."""
    df = pd.read_excel(path)
    if "sre" in df.columns:
        df["sre"] = df["sre"].astype(str).str.strip()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Boolean-merge
# ─────────────────────────────────────────────────────────────────────────────
def apply_boolean_merge(
    df: pd.DataFrame,
    merges: dict[str, tuple[list, str]],  # {col: ([true_values], new_col_name)}
) -> pd.DataFrame:
    """Cria colunas booleanas a partir de colunas categóricas.
    Ex.: {'situacao': (['DUP'], 'situacao_is_dup')}.
    A coluna original é mantida."""
    df = df.copy()
    for col, (true_vals, new_name) in merges.items():
        if col in df.columns:
            df[new_name] = df[col].isin(true_vals).astype(bool)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Group-merge
# ─────────────────────────────────────────────────────────────────────────────
def normalize_group_label(v) -> str:
    """Normaliza o valor de uma coluna de grupo para string limpa.
    Converte floats inteiros: 1.0 → '1'."""
    s = str(v)
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return s


def apply_group_merge(
    df: pd.DataFrame,
    group_col: str,
    merges: list[tuple[list, str]],  # [([val1, val2], merged_label), ...]
) -> pd.DataFrame:
    """Substitui valores em group_col combinando regiões (ex.: 2 e 3 → '2+3')."""
    df = df.copy()
    if not merges:
        df[group_col] = df[group_col].map(normalize_group_label)
        return df
    df[group_col] = df[group_col].map(normalize_group_label)
    for values, label in merges:
        str_vals = [normalize_group_label(v) for v in values]
        mask = df[group_col].isin(str_vals)
        df.loc[mask, group_col] = label
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Feature engineering
# ─────────────────────────────────────────────────────────────────────────────
def feature_engineering(
    df: pd.DataFrame,
    targets: list[str],
    group_col: str = "regional_macro",
) -> pd.DataFrame:
    """Anexa features derivadas (colunas originais inalteradas):

    1. Log-transforms de numéricas assimétricas        → ``log_<col>``
    2. Razões socioeconômicas (per-capita / per-km)    → ``frotas_per_km`` etc.
    3. Log das razões                                  → ``log_<ratio>``
    4. Excesso relativo à média regional               → ``excesso_frotas_km`` etc.
    5. Features de localização por target (média/mediana/CV + PCA composto)
    """
    df = df.copy()

    # 1. Log-transforms de numéricas base
    _log_base = [
        "distancia_cid_1", "distancia_cid_1_2_3",
        "media_pib", "media_populacao_residente",
        "media_frotas_ativas", "media_empresas_ativas",
        "extensao",
    ]
    for col in _log_base:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            df[f"log_{col}"] = np.log1p(df[col].clip(lower=0))

    # 2. Razões socioeconômicas
    _pop = df["media_populacao_residente"] if "media_populacao_residente" in df.columns else None
    _ext = df["extensao"]                  if "extensao"                  in df.columns else None
    _pib = df["media_pib"]                 if "media_pib"                 in df.columns else None
    _fro = df["media_frotas_ativas"]       if "media_frotas_ativas"       in df.columns else None
    _emp = df["media_empresas_ativas"]     if "media_empresas_ativas"     in df.columns else None

    if _fro is not None and _pop is not None:
        df["frotas_per_capita"]   = _fro / _pop.replace(0, np.nan)
    if _pib is not None and _pop is not None:
        df["pib_per_capita"]      = _pib / _pop.replace(0, np.nan)
    if _emp is not None and _pop is not None:
        df["empresas_per_capita"] = _emp / _pop.replace(0, np.nan)
    if _fro is not None and _ext is not None:
        df["frotas_per_km"]       = _fro / _ext.replace(0, np.nan)
    if _emp is not None and _ext is not None:
        df["empresas_per_km"]     = _emp / _ext.replace(0, np.nan)
    if _pib is not None and _ext is not None:
        df["pib_per_km"]          = _pib / _ext.replace(0, np.nan)

    # 3. Log das razões
    _ratio_cols = [
        "frotas_per_capita", "pib_per_capita", "empresas_per_capita",
        "frotas_per_km", "empresas_per_km", "pib_per_km",
    ]
    for col in _ratio_cols:
        if col in df.columns:
            df[f"log_{col}"] = np.log1p(df[col].clip(lower=0))

    # 3b. Excesso relativo à média regional
    if _fro is not None and _ext is not None and group_col in df.columns:
        reg_avg_frotas_km = df.groupby(group_col)["frotas_per_km"].transform("mean")
        df["excesso_frotas_km"] = df["frotas_per_km"] / reg_avg_frotas_km.clip(lower=1)
        df["log_excesso_frotas_km"] = np.log1p(df["excesso_frotas_km"].clip(lower=0))
    if _pib is not None and _ext is not None and group_col in df.columns:
        reg_avg_pib_km = df.groupby(group_col)["pib_per_km"].transform("mean")
        df["excesso_pib_km"] = df["pib_per_km"] / reg_avg_pib_km.clip(lower=1)
        df["log_excesso_pib_km"] = np.log1p(df["excesso_pib_km"].clip(lower=0))

    # 4. Features de localização por target (média/mediana/CV por grupo + PCA)
    _loc_groups: dict[str, str] = {}
    if "go" in df.columns:
        _loc_groups["go"] = "go"
    if group_col in df.columns and group_col not in _loc_groups:
        suffix = "regional" if "regional" in group_col.lower() else group_col
        _loc_groups[group_col] = suffix

    for target in targets:
        if target not in df.columns:
            continue
        obs_mask = df[target].notna()
        if obs_mask.sum() == 0:
            continue

        loc_cols = []
        for gcol, suffix in _loc_groups.items():
            stats = df.loc[obs_mask].groupby(gcol)[target].agg(["mean", "median", "std"])
            mean_col = f"{target}_media_{suffix}"
            med_col  = f"{target}_mediana_{suffix}"
            cv_col   = f"{target}_cv_{suffix}"

            df[mean_col] = df[gcol].map(stats["mean"])
            df[med_col]  = df[gcol].map(stats["median"])
            cv_series = stats["std"] / stats["mean"].clip(lower=1)
            df[cv_col] = df[gcol].map(cv_series)

            loc_cols.extend([mean_col, med_col, cv_col])

        if len(loc_cols) >= 2:
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler as LocScaler

            X_loc = df[loc_cols].fillna(df[loc_cols].median()).values.astype(float)
            X_loc_scaled = LocScaler().fit_transform(X_loc)
            pca = PCA(n_components=1)
            df[f"localizacao_{target}"] = pca.fit_transform(X_loc_scaled)[:, 0]

    return df
