---
title: Arquitetura do Sistema
type: system
status: validated
confidence: 0.90
owner: arquitetura de dados
related:
  - ../processes/pipeline-batch.md
  - ../processes/operacao-webapp.md
  - artefatos-dados.md
  - ../decisions/ADR-0001-ols-com-smearing.md
  - ../decisions/ADR-0002-front-static-api-opcional.md
tags: [arquitetura, batch, runtime, flask, frontend]
last_updated: 2026-06-19
---

<!-- ai-summary
System: descreve os componentes batch, runtime e frontend para previsao de trafego.
Flow: dados brutos -> regressao -> artefatos -> visualizacao estatico/dinamico.
Owner: arquitetura de dados.
Systems: pipeline.py, webapp.py, src/*, docs/js/app.js.
Status: validated.
-->

# Arquitetura Geral

## Componentes

1. Batch Offline (`pipeline.py`)
- Carrega dados, executa OLS por target, avalia SLO.
- Exporta JSON/GeoJSON para mapa e XLSX para analise.

2. Runtime Parametrico (`webapp.py` + `src/runtime_pipeline.py`)
- Exponibiliza API Flask para alterar parametros de treino e rodar pipeline dinamicamente.

3. Frontend (`docs/index.html` + `docs/js/app.js`)
- Renderiza mapa e metricas a partir de `docs/data/`.
- Pode operar sem API em modo estatico.

## Fluxo principal

1. `data/raw/*` alimenta modelagem.
2. `src/regression.py` gera previsoes com base em configuracoes de `config.py` ou payload runtime.
3. `src/export.py` e `src/excel_report.py` persistem saidas.
4. Frontend consome `docs/data/*` e apresenta resultados.

## Mapa de responsabilidade por modulo

- `src/data_prep.py`: normalizacao e feature engineering.
- `src/regression.py`: treino OLS, backward elimination e predicao.
- `src/formulas.py`: representacao textual/LaTeX/Excel de equacoes.
- `src/geometry.py`: georreferenciamento SRE.
- `src/export.py`: contratos JSON/GeoJSON e relatorios.
- `src/excel_report.py`: workbook final.
- `src/runtime_pipeline.py`: orquestracao configuravel para UI.

## Riscos arquiteturais

- Dependencia de caminho externo para pipeline legado em runtime (`../vdm-regressao-previsto/pipeline.py`).
- Acoplamento entre schema de exportacao e parsing no frontend.
- Metricas em amostra exigem comunicacao clara em relatorios.
