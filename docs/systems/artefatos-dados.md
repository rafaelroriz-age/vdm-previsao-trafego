---
title: Contratos de Artefatos de Dados
type: system
status: review
confidence: 0.80
owner: engenharia de dados
related:
  - ../processes/pipeline-batch.md
  - ../processes/operacao-webapp.md
  - arquitetura-sistema.md
  - ../plans/duvidas-abertas.md
tags: [geojson, json, excel, contrato, schema]
last_updated: 2026-06-19
---

<!-- ai-summary
System: documenta arquivos de entrada/saida usados por pipeline, webapp e frontend.
Flow: data/raw -> processamento -> data/export e docs/data -> consumo no mapa/UI.
Owner: engenharia de dados.
Systems: src/export.py, src/excel_report.py, docs/js/app.js.
Status: review.
-->

# Contratos de Artefatos

## Entradas principais

- `data/raw/sre_abr_2026_georef_vdm_v4.xlsx`: dataset oficial configurado em `config.py`.
- `data/raw/sre_abr_2026_georef.xlsx`: base com WKT de geometria.
- `data/raw/SRE-GO_2026_ABR.json`: geometria complementar.

## Saidas de processamento

Arquivos gerados em dois destinos (`data/export/` e `docs/data/`):

1. `segments.geojson`
- FeatureCollection com segmentos georreferenciados.
- Usado para renderizacao de trechos e valores por target.

2. `count_points.geojson`
- FeatureCollection de pontos observados.
- Usado em visualizacoes de calibracao e referencia.

3. `model_metrics.json`
- Metricas agregadas por target (R2, MAPE e status SLO).

4. `calibration_report.json`
- Dados para graficos de observado x estimado e distribuicoes de erro.

5. `sre_previsao_trafego.xlsx`
- Planilha com resultados, calibracao e equacoes para uso tecnico.

## Uploads

- `data/uploads/*`: datasets enviados via `POST /api/upload`.

## Notas de governanca

- Arquivos em `docs/data/local/` podem sobrescrever dados padrao no frontend e devem ficar fora do git.
- Alteracoes de schema exigem atualizacao coordenada entre exportador, frontend e testes.
