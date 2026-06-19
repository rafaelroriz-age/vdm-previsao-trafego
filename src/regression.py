"""
regression.py
-------------
Motor de regressão OLS: detecção de tipos, codificação, backward elimination
via statsmodels e o loop principal de previsão (um modelo global por target,
log-transform + Duan smearing, limite de features explicáveis).

Portado de `vdm-regressao-previsto/pipeline.py` (somente o núcleo OLS).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ─────────────────────────────────────────────────────────────────────────────
# Detecção de tipos
# ─────────────────────────────────────────────────────────────────────────────
def detect_column_types(df: pd.DataFrame) -> dict[str, str]:
    """Retorna {col: 'numeric' | 'boolean' | 'categorical'} para cada coluna."""
    result: dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        unique_vals = s.dropna().unique()
        if s.dtype == bool or set(unique_vals).issubset({0, 1, True, False, "0", "1"}):
            result[col] = "boolean"
        elif pd.api.types.is_numeric_dtype(s):
            result[col] = "numeric"
        else:
            result[col] = "categorical"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Codificação de features
# ─────────────────────────────────────────────────────────────────────────────
def encode_features(
    df: pd.DataFrame,
    selected_features: list[str],
    encoding_choices: dict[str, str],   # col -> 'onehot' | 'label'
    fit_encoders: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Codifica as features selecionadas. Numéricas/booleanas viram float;
    categóricas usam one-hot (drop_first) ou label encoding."""
    parts: list[pd.DataFrame] = []
    encoders: dict = fit_encoders.copy() if fit_encoders else {}
    type_map = detect_column_types(df)

    for col in selected_features:
        if col not in df.columns:
            continue
        col_type = type_map.get(col, "numeric")

        if encoding_choices.get(col) in ("onehot", "label") and col_type != "categorical":
            col_type = "categorical"

        if col_type in ("numeric", "boolean"):
            parts.append(df[[col]].astype(float).reset_index(drop=True))

        elif col_type == "categorical":
            choice = encoding_choices.get(col, "onehot")
            if choice == "label":
                if fit_encoders and col in fit_encoders:
                    le: LabelEncoder = fit_encoders[col]
                    known = set(le.classes_)
                    safe = df[col].apply(lambda v: v if v in known else le.classes_[0])
                    encoded = le.transform(safe.astype(str))
                else:
                    le = LabelEncoder()
                    encoded = le.fit_transform(df[col].fillna("__missing__").astype(str))
                    encoders[col] = le
                parts.append(pd.DataFrame({col: encoded.astype(float)}).reset_index(drop=True))
            else:  # onehot
                dummies = pd.get_dummies(
                    df[col].fillna("__missing__").astype(str), prefix=col, drop_first=True
                ).astype(float)
                if fit_encoders and col in fit_encoders:
                    expected_cols = fit_encoders[col]
                    dummies = dummies.reindex(columns=expected_cols, fill_value=0.0)
                else:
                    encoders[col] = list(dummies.columns)
                parts.append(dummies.reset_index(drop=True))

    if not parts:
        return pd.DataFrame(index=range(len(df))), encoders
    return pd.concat(parts, axis=1), encoders


# ─────────────────────────────────────────────────────────────────────────────
# Backward elimination (statsmodels OLS)
# ─────────────────────────────────────────────────────────────────────────────
def backward_elimination_ols(
    X_sc: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    threshold: float,
    mandatory_features: list[str] | None = None,
) -> tuple[list[int], list[str], object | None]:
    """Remove iterativamente a feature com maior p-value acima de `threshold`.
    Features em `mandatory_features` nunca são removidas."""
    if not mandatory_features:
        mandatory_features = []

    mandatory_set: set[str] = set()
    for col in feature_names:
        for mf in mandatory_features:
            if col == mf or col.startswith(mf + "_"):
                mandatory_set.add(col)

    kept = list(range(X_sc.shape[1]))
    res = None
    while True:
        if not kept:
            return [], [], None
        X_iter = sm.add_constant(X_sc[:, kept], has_constant="add")
        try:
            res = sm.OLS(y, X_iter).fit()
        except Exception:
            return kept, [feature_names[i] for i in kept], None

        pvals = res.pvalues[1:]
        removable = [i for i, idx in enumerate(kept) if feature_names[idx] not in mandatory_set]
        if not removable:
            break
        pvals_removable = pvals[removable]
        max_pval_removable = float(pvals_removable.max())
        if max_pval_removable <= threshold:
            break
        worst_in_removable = int(pvals_removable.argmax())
        worst_local = removable[worst_in_removable]
        kept.pop(worst_local)

    return kept, [feature_names[i] for i in kept], res


# ─────────────────────────────────────────────────────────────────────────────
# Helper de log de métricas
# ─────────────────────────────────────────────────────────────────────────────
def _log_row(target, regiao, n_train, n_pred, metodo, r2, group_col="regiao"):
    return {
        "target": target,
        group_col: regiao,
        "n_train": n_train,
        "n_pred": n_pred,
        "metodo": metodo,
        "r2": r2,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline principal de regressão (um modelo global por target)
# ─────────────────────────────────────────────────────────────────────────────
def run_regression_pipeline(
    df: pd.DataFrame,
    group_col: str,
    targets: list[str],
    features_per_target: dict[str, list[str]],
    encoding_choices: dict[str, str],
    pvalue_threshold: float,
    log_transform: bool = False,
    mandatory_per_target: dict[str, list[str]] | None = None,
    max_features: int | None = None,
    clip_predictions: bool = False,
) -> dict:
    """Pipeline completo. Um OLS global por target usando todas as SREs juntas;
    group_col entra como one-hot para capturar efeitos regionais. Métricas por
    região são derivadas post-hoc dos resíduos do modelo global (visualização)."""
    df_result = df.copy()
    fonte_cols: dict[str, pd.Series] = {
        t: pd.Series(
            ["observado" if pd.notna(df[t].iloc[i]) else np.nan for i in range(len(df))],
            index=df.index,
        )
        for t in targets
    }

    model_log: list[dict] = []
    pvalues_rows: list[dict] = []
    coefs_rows: list[dict] = []
    equations_rows: list[dict] = []
    residuals_rows: list[dict] = []
    clip_log: list[dict] = []

    regions = sorted(df[group_col].dropna().unique().tolist(), key=str)

    for target in targets:
        target_features   = [f for f in features_per_target.get(target, []) if f != target]
        mandatory_features = [f for f in (mandatory_per_target or {}).get(target, []) if f != target]

        encoded_all, _encoders = encode_features(
            df_result.reset_index(drop=False), target_features, encoding_choices,
        )
        encoded_all.index = df_result.index

        feat_cols = list(encoded_all.columns)
        has_all_features = encoded_all.notna().all(axis=1)
        mask_train = df_result[target].notna() & has_all_features
        mask_pred  = df_result[target].isna()  & has_all_features
        mask_missing_no_feat = df_result[target].isna() & ~has_all_features

        n_train_global = int(mask_train.sum())
        n_pred_global  = int(mask_pred.sum())
        n_any_missing  = int(df_result[target].isna().sum())

        def _per_region_log(metodo, r2=None, extra=None):
            for _reg in regions:
                _mr = df_result[group_col] == _reg
                _nt = int((mask_train & _mr).sum())
                _np = int(((mask_pred | mask_missing_no_feat) & _mr).sum())
                row = _log_row(target, _reg, _nt, _np, metodo, r2, group_col)
                if extra:
                    row.update(extra)
                model_log.append(row)

        if n_any_missing == 0:
            _per_region_log("sem_vazios")
            continue

        if n_train_global < 2:
            global_mean = df_result.loc[df_result[target].notna(), target].mean()
            mask_all_missing = mask_pred | mask_missing_no_feat
            df_result.loc[mask_all_missing, target] = global_mean
            fonte_cols[target].loc[mask_all_missing] = "previsto_media_global"
            _per_region_log("media_global")
            continue

        if n_pred_global == 0:
            global_mean = df_result.loc[df_result[target].notna(), target].mean()
            df_result.loc[mask_missing_no_feat, target] = global_mean
            fonte_cols[target].loc[mask_missing_no_feat] = "previsto_media_global"
            _per_region_log("media_global")
            continue

        X_train_raw = encoded_all.loc[mask_train].values.astype(float)
        y_train     = df_result.loc[mask_train, target].values.astype(float)
        X_pred_raw  = encoded_all.loc[mask_pred].values.astype(float)
        idx_pred    = df_result[mask_pred].index

        y_train_model = np.log(np.maximum(y_train, 1e-9)) if log_transform else y_train

        scaler = StandardScaler()
        X_train_sc = scaler.fit_transform(X_train_raw)
        X_pred_sc  = scaler.transform(X_pred_raw)

        try:
            _res_full = sm.OLS(y_train_model, sm.add_constant(X_train_sc, has_constant="add")).fit()
            r2_full = round(float(_res_full.rsquared), 4)
        except Exception:
            r2_full = None

        kept_idx, kept_names, ols_res = backward_elimination_ols(
            X_train_sc, y_train_model, feat_cols, pvalue_threshold, mandatory_features
        )

        # Limita a max_features (mantém maior |t-stat|; preserva mandatórias)
        if max_features and kept_idx and ols_res is not None and len(kept_idx) > max_features:
            mandatory_set_enc: set[str] = set()
            for mc in mandatory_features:
                for kn in kept_names:
                    if kn == mc or kn.startswith(mc + "_"):
                        mandatory_set_enc.add(kn)
            mandatory_kept = [i for i, n in zip(kept_idx, kept_names) if n in mandatory_set_enc]
            non_mandatory = [(i, n, abs(float(ols_res.tvalues[j + 1])))
                             for j, (i, n) in enumerate(zip(kept_idx, kept_names))
                             if n not in mandatory_set_enc]
            non_mandatory.sort(key=lambda x: x[2], reverse=True)
            slots = max(0, max_features - len(mandatory_kept))
            kept_idx   = mandatory_kept + [x[0] for x in non_mandatory[:slots]]
            kept_names = [kept_names[kept_idx.index(i)] for i in kept_idx] if kept_idx else []
            _X_red = sm.add_constant(X_train_sc[:, kept_idx], has_constant="add")
            try:
                ols_res = sm.OLS(y_train_model, _X_red).fit()
            except Exception:
                pass

        if not kept_idx or ols_res is None:
            global_mean = df_result.loc[df_result[target].notna(), target].mean()
            mask_all_missing = mask_pred | mask_missing_no_feat
            df_result.loc[mask_all_missing, target] = global_mean
            fonte_cols[target].loc[mask_all_missing] = "previsto_media_global"
            _per_region_log(
                "media_global_sem_features",
                extra={
                    "r2_modelo_completo": r2_full,
                    "aviso": f"Todas as features eliminadas (p>{pvalue_threshold}). Aumente o threshold.",
                },
            )
            continue

        X_train_final = X_train_sc[:, kept_idx]
        X_pred_final  = X_pred_sc[:, kept_idx]

        # Duan smearing — corrige o viés de retransformação quando log_transform=True
        if log_transform:
            _y_train_hat_log = ols_res.predict(sm.add_constant(X_train_final, has_constant="add"))
            _smearing = float(np.mean(np.exp(y_train_model - _y_train_hat_log)))
        else:
            _smearing = 1.0

        y_hat = ols_res.predict(sm.add_constant(X_pred_final, has_constant="add"))
        if log_transform:
            y_hat = np.exp(y_hat) * _smearing

        n_neg = int((y_hat < 0).sum())
        if n_neg > 0:
            clip_log.append({
                "target": target, group_col: "global",
                "n_negativos_clampados": n_neg,
                "min_previsto_bruto": round(float(y_hat.min()), 4),
                "media_y_treino": round(float(y_train.mean()), 4),
            })
        y_hat = np.maximum(y_hat, 0)

        df_result.loc[idx_pred, target] = np.round(y_hat, 4)
        fonte_cols[target].loc[idx_pred] = "previsto"

        if mask_missing_no_feat.sum() > 0:
            fallback_mean = round(float(y_train.mean()), 4)
            df_result.loc[mask_missing_no_feat, target] = fallback_mean
            fonte_cols[target].loc[mask_missing_no_feat] = "previsto_media_global"

        r2_global = float(ols_res.rsquared)
        X_train_ols        = sm.add_constant(X_train_final, has_constant="add")
        y_pred_train_model = ols_res.predict(X_train_ols)
        y_pred_train = np.exp(y_pred_train_model) * _smearing if log_transform else y_pred_train_model
        p_global = X_train_final.shape[1]

        df_result.loc[mask_train, f"{target}_ajustado"] = np.round(y_pred_train, 4)

        train_regions_arr = df_result.loc[mask_train, group_col].values
        pred_regions_arr  = df_result.loc[mask_pred,  group_col].values

        for regiao in regions:
            r_mask_tr = train_regions_arr == regiao
            r_mask_pr = pred_regions_arr  == regiao
            n_tr_reg = int(r_mask_tr.sum())
            n_pr_reg = int(r_mask_pr.sum())
            if n_tr_reg == 0:
                model_log.append(_log_row(target, regiao, 0, n_pr_reg, "regressao_linear", None, group_col))
                continue

            y_tr_reg  = y_train[r_mask_tr]
            y_pr_reg  = y_pred_train[r_mask_tr]
            resid_reg = y_tr_reg - y_pr_reg

            ss_res_reg = float(np.sum(resid_reg ** 2))
            ss_tot_reg = float(np.sum((y_tr_reg - y_tr_reg.mean()) ** 2))
            r2_reg = (1.0 - ss_res_reg / ss_tot_reg) if ss_tot_reg > 0 else float("nan")
            mse_reg  = float(np.mean(resid_reg ** 2))
            mae_reg  = float(np.mean(np.abs(resid_reg)))
            rmse_reg = math.sqrt(mse_reg)
            nonzero_reg = y_tr_reg != 0
            mape_reg = float(np.mean(np.abs(resid_reg[nonzero_reg] / y_tr_reg[nonzero_reg])) * 100) if nonzero_reg.any() else None
            denom_reg = n_tr_reg - p_global - 1
            rse_reg = math.sqrt(ss_res_reg / denom_reg) if denom_reg > 0 else None

            model_log.append({
                **_log_row(target, regiao, n_tr_reg, n_pr_reg, "regressao_linear", round(r2_reg, 4), group_col),
                "r2_global": round(r2_global, 4),
                "r2_modelo_completo": r2_full,
                "mse": round(mse_reg, 4),
                "mae": round(mae_reg, 4),
                "rmse": round(rmse_reg, 4),
                "mape": round(mape_reg, 4) if mape_reg is not None else None,
                "rse": round(rse_reg, 4) if rse_reg is not None else None,
                "features_usadas": ", ".join(kept_names),
                "n_features_usadas": len(kept_names),
                "aviso": None,
            })

            for _obs, _pred, _resid in zip(y_tr_reg, y_pr_reg, resid_reg):
                residuals_rows.append({
                    "target": target, group_col: regiao,
                    "y_obs": round(float(_obs), 4),
                    "y_pred": round(float(_pred), 4),
                    "residuo": round(float(_resid), 4),
                })

        for j, fname in enumerate(kept_names):
            pvalues_rows.append({
                "target": target, group_col: "global", "feature": fname,
                "coef": round(float(ols_res.params[j + 1]), 6),
                "pvalue": round(float(ols_res.pvalues[j + 1]), 6),
                "significativo": ols_res.pvalues[j + 1] <= pvalue_threshold,
            })
            coefs_rows.append({
                "target": target, group_col: "global", "feature": fname,
                "coef": round(float(ols_res.params[j + 1]), 6),
            })

        intercept = float(ols_res.params[0])
        padding   = " " * (len(target) + 5)
        lhs = f"log(ŷ({target}))" if log_transform else f"ŷ({target})"
        eq_parts = [f"{lhs} = {intercept:+.4f}"]
        for _j, _fname in enumerate(kept_names):
            _coef = float(ols_res.params[_j + 1])
            _sign = "+" if _coef >= 0 else "-"
            eq_parts.append(f"{padding}  {_sign} {abs(_coef):.4f} × {_fname}")
        if log_transform:
            eq_parts.append(
                f"\nŷ({target}) = exp(log(ŷ)) × {_smearing:.6f}"
                f"  [Duan smearing: mean(exp(ε_i)) sobre {int(mask_train.sum())} obs.]"
            )
        equations_rows.append({
            "target": target, group_col: "global",
            "intercept": round(intercept, 4),
            "equation": "\n".join(eq_parts),
            "n_features": len(kept_names),
            "smearing": round(_smearing, 6) if log_transform else None,
        })

    # Clip para [0.3×mediana_regional, 3.0×mediana_regional]
    if clip_predictions:
        _regions_unique = sorted(df[group_col].dropna().unique().tolist(), key=str)
        for t in targets:
            obs_mask_orig = df[t].notna()
            for reg in _regions_unique:
                reg_mask = df_result[group_col].astype(str) == str(reg)
                obs_reg = df.loc[obs_mask_orig & reg_mask, t]
                if len(obs_reg) == 0:
                    continue
                med = obs_reg.median()
                lo, hi = 0.3 * med, 3.0 * med
                pred_mask = reg_mask & ~obs_mask_orig
                df_result.loc[pred_mask, t] = df_result.loc[pred_mask, t].clip(lo, hi)
                adj_col = f"{t}_ajustado"
                if adj_col in df_result.columns:
                    df_result.loc[obs_mask_orig & reg_mask, adj_col] = (
                        df_result.loc[obs_mask_orig & reg_mask, adj_col].clip(lo, hi)
                    )

    for t in targets:
        df_result[f"fonte_{t}"] = fonte_cols[t]

    def _define_fonte(row):
        valores = [row.get(f"fonte_{t}") for t in targets]
        unicos = {v for v in valores if pd.notna(v)}
        if unicos == {"observado"}:
            return "observado"
        if unicos == {"previsto"}:
            return "previsto"
        if "previsto_media_global" in unicos and "observado" not in unicos:
            return "previsto_media_global"
        return "misto"

    df_result["fonte"] = df_result.apply(_define_fonte, axis=1)

    return {
        "df_result":     df_result,
        "metrics_df":    pd.DataFrame(model_log),
        "pvalues_df":    pd.DataFrame(pvalues_rows)   if pvalues_rows   else pd.DataFrame(),
        "coefs_df":      pd.DataFrame(coefs_rows)     if coefs_rows     else pd.DataFrame(),
        "equations_df":  pd.DataFrame(equations_rows) if equations_rows else pd.DataFrame(),
        "residuals_df":  pd.DataFrame(residuals_rows) if residuals_rows else pd.DataFrame(),
        "clip_log":      clip_log,
        "fonte_cols":    fonte_cols,
        "group_col":     group_col,
        "log_transform": log_transform,
    }
