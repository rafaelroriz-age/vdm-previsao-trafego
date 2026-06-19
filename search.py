"""
search.py
---------
Busca honesta de features explicáveis (≤ max_size) por target.

Reproduz a matemática do pipeline (log-transform + backward elimination +
Duan smearing + MAPE no espaço original) de forma rápida, para encontrar o
conjunto de features que maximiza R² e minimiza MAPE sob a restrição de
explicabilidade (poucas features, todas interpretáveis em fórmula).

Uso:
  python search.py            # busca para todos os targets
  python search.py vmd        # busca só para um target
"""
from __future__ import annotations

import sys
from itertools import combinations

import numpy as np
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

import config as cfg
from src import data_prep, regression

# Pool de features explicáveis (todas usáveis em fórmula/Excel; sem PCA/localização)
POOL = [
    "go",
    "log_extensao",
    "situacao_is_dup",
    "perim_urb",
    "log_media_empresas_ativas",
    "log_media_pib",
    "log_media_populacao_residente",
    "log_media_frotas_ativas",
    "log_distancia_cid_1",
    "excesso_frotas_km",
    "log_excesso_frotas_km",
    "frotas_per_km",
    "empresas_per_km",
]


def _prep():
    df = data_prep.load_dataset(cfg.DATASET_FILE)
    df = data_prep.apply_boolean_merge(df, cfg.BOOLEAN_MERGES)
    df = data_prep.apply_group_merge(df, cfg.GROUP_COL, cfg.GROUP_MERGES)
    df = data_prep.feature_engineering(df, cfg.TARGETS, cfg.GROUP_COL)
    return df


def eval_features(df, target, feats, p=0.15, log=True, max_features=6):
    """Avalia um conjunto de features: retorna (r2_log, mape_orig, n_feat, kept)."""
    enc, _ = regression.encode_features(df.reset_index(drop=False), feats, cfg.ENCODING_CHOICES)
    enc.index = df.index
    has = enc.notna().all(axis=1)
    mask = df[target].notna() & has
    if int(mask.sum()) < 10:
        return None
    X = enc.loc[mask].values.astype(float)
    y = df.loc[mask, target].values.astype(float)
    ym = np.log(np.maximum(y, 1e-9)) if log else y
    Xs = StandardScaler().fit_transform(X)
    kept_idx, kept_names, res = regression.backward_elimination_ols(Xs, ym, list(enc.columns), p)
    if not kept_idx or res is None:
        return None
    if max_features and len(kept_idx) > max_features:
        tv = [(i, n, abs(float(res.tvalues[j + 1]))) for j, (i, n) in enumerate(zip(kept_idx, kept_names))]
        tv.sort(key=lambda z: z[2], reverse=True)
        kept_idx = [z[0] for z in tv[:max_features]]
        kept_names = [z[1] for z in tv[:max_features]]
        res = sm.OLS(ym, sm.add_constant(Xs[:, kept_idx], has_constant="add")).fit()
    Xf = Xs[:, kept_idx]
    yhat_log = res.predict(sm.add_constant(Xf, has_constant="add"))
    smear = float(np.mean(np.exp(ym - yhat_log))) if log else 1.0
    yhat = np.exp(yhat_log) * smear if log else yhat_log
    yhat = np.maximum(yhat, 0)
    err = y - yhat
    nz = y != 0
    mape = float(np.mean(np.abs(err[nz] / y[nz])) * 100) if nz.any() else None
    return round(float(res.rsquared), 4), round(mape, 2) if mape else None, len(kept_names), kept_names


def score(r2, mape):
    if r2 is None or mape is None:
        return -1e9
    return r2 * 100 - mape / 5.0


def target_pool(df, target, use_location=False):
    pool = list(POOL)
    if use_location:
        for suf in ("go", "regional"):
            for stat in ("media", "mediana"):
                col = f"{target}_{stat}_{suf}"
                if col in df.columns:
                    pool.append(col)
    return pool


def search_target(df, target, sizes=(3, 4, 5), top=8, use_location=False):
    results = []
    seen = set()
    pool = target_pool(df, target, use_location)
    for k in sizes:
        for combo in combinations(pool, k):
            ev = eval_features(df, target, list(combo))
            if ev is None:
                continue
            r2, mape, nfeat, kept = ev
            key = tuple(sorted(kept))
            if key in seen:
                continue
            seen.add(key)
            results.append((score(r2, mape), r2, mape, nfeat, kept))
    results.sort(key=lambda z: z[0], reverse=True)
    return results[:top]


def main():
    df = _prep()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_location = "--loc" in sys.argv
    targets = args if args else cfg.TARGETS
    for t in targets:
        slo = cfg.SLO[t]
        tag = " +location" if use_location else ""
        print(f"\n{'='*70}\nTARGET: {t}{tag}  (SLO: R²≥{slo['r2_min']}, MAPE≤{slo['mape_max']}%)\n{'='*70}")
        best = search_target(df, t, use_location=use_location)
        for s, r2, mape, nfeat, kept in best:
            ok = "OK " if (r2 >= slo["r2_min"] and mape <= slo["mape_max"]) else "   "
            print(f"  {ok} R²={r2:.3f}  MAPE={mape:>6.1f}%  n={nfeat}  {kept}")


if __name__ == "__main__":
    main()
