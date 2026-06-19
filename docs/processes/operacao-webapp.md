---
title: Operacao da Webapp Runtime
type: process
status: validated
confidence: 0.90
owner: engenharia de aplicacao
related:
  - ../systems/arquitetura-sistema.md
  - ../systems/artefatos-dados.md
  - ../plans/divergencias.md
tags: [flask, runtime, frontend, upload]
last_updated: 2026-06-19
---

<!-- ai-summary
System: descreve o fluxo da webapp Flask para executar pipeline configuravel e download de excel.
Flow: subir webapp.py -> health check -> upload/opcoes -> run -> download.
Owner: engenharia de aplicacao.
Systems: webapp.py, src/runtime_pipeline.py, docs/js/app.js.
Status: validated.
-->

# Processo de Operacao da Webapp

> Migrado de `README.md` (MVP estatico) e consolidado com comportamento atual em `webapp.py`.

## Objetivo

Executar o pipeline de forma parametrica pela interface web, com upload de dataset e download do Excel.

## Subir a aplicacao

```powershell
python webapp.py
```

Endpoint base:
- `http://localhost:8777`

## Endpoints principais

- `GET /api/health`: verifica saude da API.
- `GET /api/config/default`: retorna configuracao inicial.
- `GET /api/options`: retorna opcoes e candidatos de features.
- `POST /api/candidates`: recalcula candidatos conforme payload.
- `POST /api/run`: executa runtime pipeline com payload.
- `GET /api/download/excel`: baixa `sre_previsao_trafego.xlsx`.
- `POST /api/upload`: envia `.csv`, `.xlsx`, `.xls` para `data/uploads/`.

## Fluxo operacional recomendado

1. Abrir UI em `http://localhost:8777`.
2. Confirmar API saudavel (`/api/health`).
3. Se necessario, subir novo dataset por upload.
4. Ajustar parametros (targets, features, merges, thresholds).
5. Executar corrida em `/api/run`.
6. Validar SLO retornado e baixar Excel.

## Observacoes

- Quando API nao esta disponivel, o frontend deve continuar em modo estatico lendo `docs/data/`.
- CORS esta habilitado globalmente no servidor Flask.
- Excecoes nao tratadas retornam JSON com status 500.
