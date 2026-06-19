---
title: Execucao do Pipeline Batch
type: process
status: validated
confidence: 0.90
owner: engenharia de dados
related:
  - ../systems/arquitetura-sistema.md
  - ../systems/artefatos-dados.md
  - ../knowledge/baseline-metricas.md
  - ../plans/divergencias.md
tags: [pipeline, ols, exportacao, validacao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define o fluxo offline para gerar previsoes, metricas e artefatos de mapa/excel.
Flow: preparar ambiente -> rodar pipeline.py -> validar pytest/SLO -> publicar artefatos.
Owner: engenharia de dados.
Systems: config.py, src/regression.py, src/export.py, src/excel_report.py.
Status: validated.
-->

# Processo de Execucao Batch

> Migrado de `README.md` (secoes "Como rodar", "Metodologia" e "Deploy").

## Objetivo

Gerar previsoes para `vmd`, `vmdc`, `n_aashto`, `n_usace`, exportando:
- `segments.geojson`
- `count_points.geojson`
- `model_metrics.json`
- `calibration_report.json`
- `sre_previsao_trafego.xlsx`

## Pre-condicoes

1. Dependencias instaladas via `requirements.txt`.
2. Dataset e geometrias presentes em `data/raw/` conforme `config.py`.
3. Permissao de escrita em `data/export/` e `docs/data/`.

## Passo a passo

1. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

2. Executar pipeline:

```powershell
python pipeline.py
```

3. Validar testes e SLO:

```powershell
python -m pytest -q
```

4. Validar visualizacao local estaticamente:

```powershell
python -m http.server 8778 --directory docs
```

## Saidas esperadas

- JSON/GeoJSON atualizados em `data/export/` e `docs/data/`.
- Excel atualizado em `data/export/sre_previsao_trafego.xlsx`.
- Logs indicando status APROVADO ou REPROVADO baseado em SLO.

## Falhas comuns

- Arquivo de dataset nao encontrado: revisar `config.py` (`DATASET_FILE`).
- Erro de geometria: revisar `GEOREF_FILE` e `GEOMETRY_JSON`.
- Falha de SLO: registrar analise em `docs/plans/divergencias.md` antes de alterar thresholds.
