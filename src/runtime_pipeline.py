"""
runtime_pipeline.py
-------------------
Execução dinâmica do pipeline via configuração recebida da UI web.

Objetivo: trazer para o novo layout as opções-chave do Streamlit:
- dataset
- group_col
- group merges
- boolean merges
- targets
- features/mandatory por target
- encoding categórico
- p-value, log-transform, max_features
- estratificado por região (opcional)
- clip de predições
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import pandas as pd

import config as cfg
from src import excel_report, export, geometry, regression


def _normalize_group_label(v) -> str:
    s = str(v)
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return s


def _split_candidates(df: pd.DataFrame, targets: list[str]) -> dict[str, list[str]]:
    """Versão local do split de candidatos (sem colunas quase-id categóricas)."""
    exclude = set(targets)
    type_map = regression.detect_column_types(df)
    n_rows = len(df)
    out: dict[str, list[str]] = {"numeric": [], "boolean": [], "categorical": []}
    for col, t in type_map.items():
        if col in exclude:
            continue
        n_unique = df[col].nunique()
        if n_unique <= 1:
            continue
        if t == "categorical" and n_unique / max(1, n_rows) > 0.95:
            continue
        out[t].append(col)
    for k in out:
        out[k] = sorted(out[k])
    return out


def _load_legacy_pipeline():
    """Carrega dinamicamente o pipeline legado (vdm-regressao-previsto)."""
    legacy_path = cfg.BASE_DIR.parent / "vdm-regressao-previsto" / "pipeline.py"
    if not legacy_path.exists():
        raise FileNotFoundError(f"Pipeline legado não encontrado: {legacy_path}")
    spec = importlib.util.spec_from_file_location("legacy_pipeline", str(legacy_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Falha ao carregar pipeline legado")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_runtime_config() -> dict[str, Any]:
    return {
        "dataset_path": str(cfg.DATASET_FILE),
        "group_col": cfg.GROUP_COL,
        "targets": list(cfg.TARGETS),
        "group_merges": [{"values": ["2", "3"], "label": "2+3"}],
        "boolean_merges": [{"column": "situacao", "true_values": ["DUP"], "new_name": "situacao_is_dup"}],
        "features_per_target": cfg.FEATURES_PER_TARGET,
        "mandatory_per_target": {t: [] for t in cfg.TARGETS},
        "encoding_choices": dict(cfg.ENCODING_CHOICES),
        "pvalue_threshold": cfg.PVALUE_THRESHOLD,
        "log_transform": False,
        "use_max_features": False,
        "max_features": cfg.MAX_FEATURES,
        "clip_predictions": True,
        "use_stratified": True,
        "min_train_region": 10,
    }


def build_candidates(config_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Monta candidatos de features com base na configuração parcial atual."""
    payload = default_runtime_config()
    if config_payload:
        payload.update(config_payload)

    dataset_path = Path(payload.get("dataset_path") or cfg.DATASET_FILE)
    if not dataset_path.is_absolute():
        dataset_path = (cfg.BASE_DIR / dataset_path).resolve()

    legacy = _load_legacy_pipeline()
    if dataset_path.suffix.lower() == ".csv":
        df = pd.read_csv(dataset_path)
    else:
        df = pd.read_excel(dataset_path)

    group_col = payload.get("group_col", cfg.GROUP_COL)
    targets = [t for t in payload.get("targets", cfg.TARGETS) if t in df.columns]
    if "sre" in df.columns:
        df["sre"] = df["sre"].astype(str).str.strip()

    merges = []
    for m in payload.get("group_merges", []):
        values = [_normalize_group_label(v) for v in m.get("values", [])]
        label = str(m.get("label", "+".join(values)))
        if len(values) >= 2:
            merges.append((values, label))
    if merges:
        df = legacy.apply_group_merge(df, group_col, merges)

    low_card_categories = {}
    type_map = legacy.detect_column_types(df)
    for col, t in type_map.items():
        if t != "categorical" or col in targets:
            continue
        n_unique = df[col].nunique(dropna=True)
        if n_unique <= 6:
            low_card_categories[col] = sorted(df[col].dropna().astype(str).unique().tolist())

    bool_map = {}
    for b in payload.get("boolean_merges", []):
        col = b.get("column")
        tv = b.get("true_values", [])
        nn = b.get("new_name") or f"{col}_is_{'_'.join(str(x).lower() for x in tv)}"
        if col and tv:
            bool_map[col] = (tv, nn)
    if bool_map:
        df = legacy.apply_boolean_merge(df, bool_map)

    df = legacy.feature_engineering(df, targets, group_col)

    candidates = _split_candidates(df, targets)
    columns = list(df.columns)
    per_target = {}
    for t in targets:
        others = [x for x in targets if x != t]
        c_t = _split_candidates(df, others)
        per_target[t] = {
            "numeric": c_t["numeric"],
            "boolean": c_t["boolean"],
            "categorical": c_t["categorical"],
            "all": c_t["numeric"] + c_t["boolean"] + c_t["categorical"],
        }

    return {
        "columns": columns,
        "targets_available": [c for c in columns if pd.api.types.is_numeric_dtype(df[c])],
        "candidates": candidates,
        "per_target": per_target,
        "low_card_categories": low_card_categories,
        "group_values": sorted(df[group_col].dropna().map(_normalize_group_label).unique().tolist(), key=str)
        if group_col in df.columns else [],
    }


def run_pipeline_runtime(config_payload: dict[str, Any]) -> dict[str, Any]:
    payload = default_runtime_config()
    payload.update(config_payload or {})

    dataset_path = Path(payload.get("dataset_path") or cfg.DATASET_FILE)
    if not dataset_path.is_absolute():
        dataset_path = (cfg.BASE_DIR / dataset_path).resolve()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {dataset_path}")

    group_col = payload.get("group_col", cfg.GROUP_COL)
    use_stratified = bool(payload.get("use_stratified", False))
    min_train_region = int(payload.get("min_train_region", 10))

    if dataset_path.suffix.lower() == ".csv":
        df = pd.read_csv(dataset_path)
    else:
        df = pd.read_excel(dataset_path)

    if "sre" in df.columns:
        df["sre"] = df["sre"].astype(str).str.strip()

    targets = [t for t in payload.get("targets", cfg.TARGETS) if t in df.columns]
    if not targets:
        raise ValueError("Nenhum target válido selecionado")

    # Merges de grupo
    legacy = _load_legacy_pipeline()
    merges = []
    for m in payload.get("group_merges", []):
        values = [_normalize_group_label(v) for v in m.get("values", [])]
        label = str(m.get("label", "+".join(values)))
        if len(values) >= 2:
            merges.append((values, label))
    if merges:
        df = legacy.apply_group_merge(df, group_col, merges)

    # Boolean merges
    bool_map = {}
    for b in payload.get("boolean_merges", []):
        col = b.get("column")
        tv = b.get("true_values", [])
        nn = b.get("new_name") or f"{col}_is_{'_'.join(str(x).lower() for x in tv)}"
        if col and tv:
            bool_map[col] = (tv, nn)
    if bool_map:
        df = legacy.apply_boolean_merge(df, bool_map)

    # Feature engineering
    df = legacy.feature_engineering(df, targets, group_col)

    # Features / mandatory / encoding
    features_per_target = {}
    for t in targets:
        feats = payload.get("features_per_target", {}).get(t, [])
        feats = [f for f in feats if f in df.columns and f != t]
        if not feats:
            # fallback: usa seleção atual do config quando disponível
            feats = [f for f in cfg.FEATURES_PER_TARGET.get(t, []) if f in df.columns and f != t]
        features_per_target[t] = feats

    mandatory_per_target = {}
    for t in targets:
        m = payload.get("mandatory_per_target", {}).get(t, [])
        mandatory_per_target[t] = [f for f in m if f in features_per_target[t]]

    encoding_choices = dict(payload.get("encoding_choices", cfg.ENCODING_CHOICES))
    pvalue_threshold = float(payload.get("pvalue_threshold", cfg.PVALUE_THRESHOLD))
    log_transform = bool(payload.get("log_transform", cfg.LOG_TRANSFORM))
    use_max_features = bool(payload.get("use_max_features", True))
    max_features = int(payload.get("max_features", cfg.MAX_FEATURES)) if use_max_features else None
    clip_predictions = bool(payload.get("clip_predictions", cfg.CLIP_PREDICTIONS))

    if use_stratified:
        result = legacy.run_regression_pipeline_stratified(
            df=df,
            group_col=group_col,
            targets=targets,
            features_per_target=features_per_target,
            encoding_choices=encoding_choices,
            pvalue_threshold=pvalue_threshold,
            log_transform=log_transform,
            mandatory_per_target=mandatory_per_target,
            max_features=max_features,
            min_train_region=min_train_region,
            clip_predictions=clip_predictions,
        )
        # Equações globais para exibir fórmula mais estável na UI
        try:
            result_global = legacy.run_regression_pipeline(
                df=df,
                group_col=group_col,
                targets=targets,
                features_per_target=features_per_target,
                encoding_choices=encoding_choices,
                pvalue_threshold=pvalue_threshold,
                log_transform=log_transform,
                mandatory_per_target=mandatory_per_target,
                max_features=max_features,
                clip_predictions=clip_predictions,
            )
            result["equations_global"] = result_global.get("equations_df", pd.DataFrame())
        except Exception:
            pass
    else:
        result = legacy.run_regression_pipeline(
            df=df,
            group_col=group_col,
            targets=targets,
            features_per_target=features_per_target,
            encoding_choices=encoding_choices,
            pvalue_threshold=pvalue_threshold,
            log_transform=log_transform,
            mandatory_per_target=mandatory_per_target,
            max_features=max_features,
            clip_predictions=clip_predictions,
        )

    summaries = {t: export.compute_target_summary(result, t) for t in targets}
    # aplica SLO apenas dos targets presentes
    slo_subset = {t: cfg.SLO[t] for t in targets if t in cfg.SLO}
    slo_report = export.evaluate_slo(summaries, slo_subset)

    sre2geom = geometry.build_sre_geometry(cfg.GEOREF_FILE, cfg.GEOMETRY_JSON)
    segments = export.build_segments_geojson(result, sre2geom, targets)
    points = export.build_count_points_geojson(result, sre2geom, targets)
    model_metrics = export.build_model_metrics(summaries, slo_report, targets)
    calibration = export.build_calibration_report(result, summaries, targets)

    # Persistência para frontend estático
    for target_dir in (cfg.EXPORT_DIR, cfg.DOCS_DATA_DIR):
        export.write_json(segments, target_dir / "segments.geojson")
        export.write_json(points, target_dir / "count_points.geojson")
        export.write_json(model_metrics, target_dir / "model_metrics.json")
        export.write_json(calibration, target_dir / "calibration_report.json")

    xlsx = excel_report.export_to_excel(result)
    cfg.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = cfg.EXPORT_DIR / "sre_previsao_trafego.xlsx"
    xlsx_path.write_bytes(xlsx)

    return {
        "ok": True,
        "message": "Pipeline executado com sucesso",
        "targets": targets,
        "slo": slo_report,
        "summary": {t: {"r2": summaries[t].get("r2_global"), "mape": summaries[t].get("mape")} for t in targets},
        "files": {
            "segments": str(cfg.DOCS_DATA_DIR / "segments.geojson"),
            "count_points": str(cfg.DOCS_DATA_DIR / "count_points.geojson"),
            "model_metrics": str(cfg.DOCS_DATA_DIR / "model_metrics.json"),
            "calibration_report": str(cfg.DOCS_DATA_DIR / "calibration_report.json"),
            "excel": str(xlsx_path),
        },
    }
