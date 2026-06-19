"""
pipeline.py
-----------
Orquestrador do pipeline de previsão de tráfego por regressão OLS.

Fluxo:
  dados (v4) → merges → feature engineering → OLS por target →
  exportação (GeoJSON + JSON + Excel) → avaliação de SLO.

Uso:
  python pipeline.py
"""
from __future__ import annotations

import json

import config as cfg
from src import data_prep, export, excel_report, geometry, regression


def run() -> dict:
    print("=" * 60)
    print("Pipeline de Previsão de Tráfego — Regressão OLS")
    print("=" * 60)

    # 1. Dados
    print("[1/6] Carregando dataset...")
    df = data_prep.load_dataset(cfg.DATASET_FILE)
    df = data_prep.apply_boolean_merge(df, cfg.BOOLEAN_MERGES)
    df = data_prep.apply_group_merge(df, cfg.GROUP_COL, cfg.GROUP_MERGES)
    df = data_prep.feature_engineering(df, cfg.TARGETS, cfg.GROUP_COL)
    print(f"   {len(df)} segmentos, group_col='{cfg.GROUP_COL}'")

    # 2. Regressão
    print("[2/6] Rodando regressão OLS por target...")
    result = regression.run_regression_pipeline(
        df=df,
        group_col=cfg.GROUP_COL,
        targets=cfg.TARGETS,
        features_per_target=cfg.FEATURES_PER_TARGET,
        encoding_choices=cfg.ENCODING_CHOICES,
        pvalue_threshold=cfg.PVALUE_THRESHOLD,
        log_transform=cfg.LOG_TRANSFORM,
        mandatory_per_target=cfg.MANDATORY_PER_TARGET,
        max_features=cfg.MAX_FEATURES,
        clip_predictions=cfg.CLIP_PREDICTIONS,
    )

    # 3. Resumos + SLO
    print("[3/6] Calculando métricas e avaliando SLO...")
    summaries = {t: export.compute_target_summary(result, t) for t in cfg.TARGETS}
    slo_report = export.evaluate_slo(summaries, cfg.SLO)
    _print_slo(summaries, slo_report)

    # 4. Geometria
    print("[4/6] Construindo geometria georreferenciada...")
    sre2geom = geometry.build_sre_geometry(cfg.GEOREF_FILE, cfg.GEOMETRY_JSON)

    # 5. Exportação JSON/GeoJSON
    print("[5/6] Exportando GeoJSON e relatórios JSON...")
    segments = export.build_segments_geojson(result, sre2geom, cfg.TARGETS)
    points = export.build_count_points_geojson(result, sre2geom, cfg.TARGETS)
    model_metrics = export.build_model_metrics(summaries, slo_report, cfg.TARGETS)
    calibration = export.build_calibration_report(result, summaries, cfg.TARGETS)

    for target_dir in (cfg.EXPORT_DIR, cfg.DOCS_DATA_DIR):
        export.write_json(segments, target_dir / "segments.geojson")
        export.write_json(points, target_dir / "count_points.geojson")
        export.write_json(model_metrics, target_dir / "model_metrics.json")
        export.write_json(calibration, target_dir / "calibration_report.json")
    print(f"   segments.geojson: {len(segments['features'])} | "
          f"count_points.geojson: {len(points['features'])}")

    # 6. Excel
    print("[6/6] Exportando planilha Excel...")
    xlsx = excel_report.export_to_excel(result)
    cfg.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = cfg.EXPORT_DIR / "sre_previsao_trafego.xlsx"
    xlsx_path.write_bytes(xlsx)
    print(f"   {xlsx_path.name} ({len(xlsx) / 1024:.0f} KB)")

    print("\n" + ("APROVADO" if slo_report["_todos_aprovados"] else "REPROVADO") +
          " — ver SLO acima.")
    return {"result": result, "summaries": summaries, "slo": slo_report}


def _print_slo(summaries, slo_report):
    print("\n   Target     R²global  (min)   MAPE%   (max)   Status")
    print("   " + "-" * 56)
    for t, r in slo_report.items():
        if t.startswith("_"):
            continue
        r2 = r["r2_global"]
        mape = r["mape"]
        status = "OK " if r["aprovado"] else "FALHA"
        print(f"   {t:<10} {r2 if r2 is not None else '   -':>7}  "
              f"({r['r2_min']:.2f})  {mape if mape is not None else '  -':>6}  "
              f"({r['mape_max']:.0f})   {status}")
    print()


if __name__ == "__main__":
    run()
