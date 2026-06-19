"""
export.py
---------
Gera os artefatos consumidos pelo frontend (mapa estático):

  - segments.geojson        : geometria + obs/prev/final/source por target
  - count_points.geojson    : pontos observados (ponto médio do segmento)
  - model_metrics.json      : por target → features, coefs, métricas, equações
  - calibration_report.json : por target → métricas + scatter observado×ajustado

Também avalia os critérios de aceite (SLO) por target.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.formulas import equation_to_excel, equation_to_latex_inline
from src.geometry import geometry_midpoint


# ─────────────────────────────────────────────────────────────────────────────
# Métricas / resumo por target
# ─────────────────────────────────────────────────────────────────────────────
def compute_target_summary(result: dict, target: str) -> dict:
    """Resumo global por target: R², MAE, RMSE, MAPE (espaço original) +
    features, coeficientes e equações (texto/latex/excel)."""
    group_col = result["group_col"]
    metrics_df = result["metrics_df"]
    resid_df = result["residuals_df"]
    coefs_df = result["coefs_df"]
    pvalues_df = result["pvalues_df"]
    equations_df = result["equations_df"]

    mt = metrics_df[(metrics_df["target"] == target) &
                    (metrics_df["metodo"].isin(["regressao_linear", "regressao_linear_strat"]))] if not metrics_df.empty else pd.DataFrame()

    r2_global = float(mt["r2_global"].dropna().iloc[0]) if (not mt.empty and "r2_global" in mt and not mt["r2_global"].dropna().empty) else None
    r2_mean = float(mt["r2"].dropna().mean()) if (not mt.empty and not mt["r2"].dropna().empty) else None
    r2_min = float(mt["r2"].dropna().min()) if (not mt.empty and not mt["r2"].dropna().empty) else None

    # Métricas globais no espaço original, a partir dos resíduos de treino
    rt = resid_df[resid_df["target"] == target] if not resid_df.empty else pd.DataFrame()
    if not rt.empty:
        obs = rt["y_obs"].values.astype(float)
        pred = rt["y_pred"].values.astype(float)
        err = obs - pred
        mae = float(np.mean(np.abs(err)))
        rmse = float(np.sqrt(np.mean(err ** 2)))
        nz = obs != 0
        mape = float(np.mean(np.abs(err[nz] / obs[nz])) * 100) if nz.any() else None
        n_obs = int(len(obs))
    else:
        mae = rmse = mape = None
        n_obs = 0

    # Features + coeficientes + p-values
    features = []
    if not coefs_df.empty:
        ct = coefs_df[coefs_df["target"] == target]
        pt = pvalues_df[pvalues_df["target"] == target] if not pvalues_df.empty else pd.DataFrame()
        pmap = dict(zip(pt["feature"], pt["pvalue"])) if not pt.empty else {}
        for _, row in ct.iterrows():
            features.append({
                "feature": row["feature"],
                "coef": float(row["coef"]),
                "pvalue": float(pmap.get(row["feature"], np.nan)) if row["feature"] in pmap else None,
            })

    # Equações
    eq_text = intercept = smearing = None
    eq_source = equations_df
    if eq_source.empty and "equations_global" in result:
        eq_source = result.get("equations_global", pd.DataFrame())
    if not eq_source.empty:
        et = eq_source[eq_source["target"] == target]
        if not et.empty:
            eq_text = et.iloc[0]["equation"]
            intercept = float(et.iloc[0]["intercept"])
            smearing = et.iloc[0].get("smearing")

    equations = None
    if eq_text:
        equations = {
            "texto": eq_text,
            "latex": equation_to_latex_inline(eq_text),
            "excel": equation_to_excel(eq_text),
        }

    return {
        "target": target,
        "r2_global": round(r2_global, 4) if r2_global is not None else None,
        "r2_mean_regioes": round(r2_mean, 4) if r2_mean is not None else None,
        "r2_min_regioes": round(r2_min, 4) if r2_min is not None else None,
        "mae": round(mae, 2) if mae is not None else None,
        "rmse": round(rmse, 2) if rmse is not None else None,
        "mape": round(mape, 2) if mape is not None else None,
        "n_observacoes": n_obs,
        "intercept": intercept,
        "smearing": float(smearing) if smearing is not None else None,
        "features": features,
        "n_features": len(features),
        "equations": equations,
        "log_transform": result["log_transform"],
    }


def evaluate_slo(summaries: dict, slo: dict) -> dict:
    """Compara R² global e MAPE de cada target com o SLO. Retorna dict de avaliação."""
    report = {}
    for t, crit in slo.items():
        s = summaries.get(t, {})
        r2 = s.get("r2_global")
        mape = s.get("mape")
        r2_ok = (r2 is not None) and (r2 >= crit["r2_min"])
        mape_ok = (mape is not None) and (mape <= crit["mape_max"])
        report[t] = {
            "r2_global": r2, "r2_min": crit["r2_min"], "r2_ok": r2_ok,
            "mape": mape, "mape_max": crit["mape_max"], "mape_ok": mape_ok,
            "aprovado": bool(r2_ok and mape_ok),
        }
    report["_todos_aprovados"] = all(v["aprovado"] for v in report.values())
    return report


# ─────────────────────────────────────────────────────────────────────────────
# GeoJSON de segmentos
# ─────────────────────────────────────────────────────────────────────────────
_SOURCE_MAP = {
    "observado": "observado",
    "previsto": "previsto",
    "previsto_media_global": "media_global",
}


def build_segments_geojson(result: dict, sre2geom: dict, targets: list[str]) -> dict:
    df = result["df_result"]
    group_col = result["group_col"]
    features = []
    missing_geom = 0

    for _, row in df.iterrows():
        sre = str(row.get("sre", "")).strip()
        geom = sre2geom.get(sre)
        if geom is None:
            missing_geom += 1
            continue

        props = {
            "sre": sre,
            "go": _safe(row.get("go"), int),
            "classe": _safe(row.get("classe")),
            "situacao": _safe(row.get("situacao")),
            "perim_urb": _safe(row.get("perim_urb")),
            "regional": _safe(row.get(group_col)),
            "extensao": _safe(row.get("extensao"), float),
            "fonte": _safe(row.get("fonte")),
        }

        for t in targets:
            source = _SOURCE_MAP.get(str(row.get(f"fonte_{t}")), "media_global")
            final = _num(row.get(t))
            adj = _num(row.get(f"{t}_ajustado"))
            if source == "observado":
                obs = final
                pred = adj if adj is not None else final
            else:
                obs = None
                pred = final
            props[f"{t}_obs"] = obs
            props[f"{t}_pred"] = pred
            props[f"{t}_final"] = final
            props[f"{t}_source"] = source

        features.append({"type": "Feature", "geometry": geom, "properties": props})

    if missing_geom:
        print(f"   [aviso] {missing_geom} segmentos sem geometria (ignorados no mapa)")
    return {"type": "FeatureCollection", "features": features}


def build_count_points_geojson(result: dict, sre2geom: dict, targets: list[str]) -> dict:
    """Ponto observado por SRE que tem pelo menos um target observado."""
    df = result["df_result"]
    group_col = result["group_col"]
    pts = []
    for _, row in df.iterrows():
        sre = str(row.get("sre", "")).strip()
        geom = sre2geom.get(sre)
        if geom is None:
            continue
        observed = {t: row.get(f"fonte_{t}") == "observado" for t in targets}
        if not any(observed.values()):
            continue
        mid = geometry_midpoint(geom)
        if mid is None:
            continue
        lon, lat = mid
        props = {
            "sre": sre,
            "go": _safe(row.get("go"), int),
            "regional": _safe(row.get(group_col)),
        }
        for t in targets:
            props[f"{t}"] = _num(row.get(t)) if observed[t] else None
        pts.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": pts}


# ─────────────────────────────────────────────────────────────────────────────
# Relatórios JSON
# ─────────────────────────────────────────────────────────────────────────────
def build_model_metrics(summaries: dict, slo_report: dict, targets: list[str]) -> dict:
    return {
        "targets": {t: summaries[t] for t in targets if t in summaries},
        "slo": slo_report,
    }


def build_calibration_report(result: dict, summaries: dict, targets: list[str]) -> dict:
    resid_df = result["residuals_df"]
    df = result["df_result"]
    out = {"targets": {}}
    for t in targets:
        s = summaries.get(t, {})
        scatter = []
        # Liga resíduos (y_obs/y_pred) de volta às SREs observadas via valores
        obs_rows = df[df[f"fonte_{t}"] == "observado"]
        for _, row in obs_rows.iterrows():
            obs = _num(row.get(t))
            est = _num(row.get(f"{t}_ajustado"))
            if obs is None or est is None:
                continue
            resid = round(obs - est, 4)
            erro_pct = round((obs - est) / obs * 100, 2) if obs not in (0, None) else None
            scatter.append({
                "sre": str(row.get("sre", "")).strip(),
                "observed": obs, "estimated": est,
                "residual": resid, "erro_pct": erro_pct,
            })
        out["targets"][t] = {
            "metrics": {
                "r2_global": s.get("r2_global"),
                "r2_mean_regioes": s.get("r2_mean_regioes"),
                "mae": s.get("mae"), "rmse": s.get("rmse"), "mape": s.get("mape"),
                "n_observacoes": s.get("n_observacoes"),
            },
            "scatter_data": scatter,
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Escrita
# ─────────────────────────────────────────────────────────────────────────────
def write_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _safe(val, cast=str, default=None):
    if val is None:
        return default
    try:
        s = str(val).strip()
        if s in ("", "nan", "None"):
            return default
        return cast(float(s)) if cast in (int, float) else (cast(s) if cast is not str else s)
    except (ValueError, TypeError):
        return default


def _num(val):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        f = float(val)
        if np.isnan(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None
