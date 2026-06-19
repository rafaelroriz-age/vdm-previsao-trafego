---
title: Inventario de Conhecimento Consolidado
type: plan
status: validated
confidence: 0.90
owner: engenharia
related:
  - ../README.md
  - divergencias.md
  - duvidas-abertas.md
  - segundo-cerebro-roadmap.md
tags: [inventario, consolidacao, rastreabilidade]
last_updated: 2026-06-19
---

<!-- ai-summary
System: registra o que foi mapeado no repositorio e qual acao foi tomada para cada item.
Flow: identificar fonte -> classificar migrar/atualizar/criar -> apontar documento destino.
Owner: engenharia.
Systems: README.md, config.py, src/*, docs/knowledge/*, webapp.py.
Status: validated.
-->

# Inventario

| Item de conhecimento | Evidencia (origem) | Acao | Destino consolidado |
|---|---|---|---|
| Objetivo do produto e targets | `README.md` | migrar | `docs/README.md`, `docs/processes/pipeline-batch.md` |
| Metodologia OLS + smearing | `README.md`, `config.py`, `src/regression.py` | migrar | `docs/decisions/ADR-0001-ols-com-smearing.md` |
| Processo de execucao batch | `README.md`, `pipeline.py` | atualizar | `docs/processes/pipeline-batch.md` |
| Processo de operacao runtime/web | `webapp.py`, `src/runtime_pipeline.py`, `README.md` | criar | `docs/processes/operacao-webapp.md` |
| Arquitetura de componentes | `README.md`, `pipeline.py`, `webapp.py` | criar | `docs/systems/arquitetura-sistema.md` |
| Contratos de artefatos | `src/export.py`, `src/excel_report.py`, `README.md` | criar | `docs/systems/artefatos-dados.md` |
| Baseline de metricas | `docs/knowledge/baseline-metricas.md` | atualizar | `docs/knowledge/baseline-metricas.md` |
| Glossario de features | `docs/knowledge/glossario.md`, `config.py` | atualizar | `docs/knowledge/glossario.md` |
| Fallback frontend estatico | `README.md`, `webapp.py`, `/memories/repo/run-notes.md` | criar | `docs/decisions/ADR-0002-front-static-api-opcional.md` |
| Regras operacionais do agente | solicitacao do usuario + estrutura do repositorio | criar | `AGENTS.md`, `MEMORY.md`, `skills/*.md` |
