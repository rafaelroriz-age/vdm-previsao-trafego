---
title: ADR 0002 - Frontend estatico com API opcional
type: decision
status: validated
confidence: 0.90
owner: arquitetura
related:
  - ../processes/operacao-webapp.md
  - ../systems/arquitetura-sistema.md
  - ../systems/artefatos-dados.md
tags: [adr, frontend, flask, fallback, operacao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define estrategia de operacao do frontend em modo estatico e dinamico.
Flow: tentar API health -> se ok habilitar runtime -> senao consumir docs/data.
Owner: arquitetura.
Systems: webapp.py, docs/js/app.js.
Status: validated.
-->

# Contexto

O projeto precisava funcionar tanto em publicacao estatica (GitHub Pages) quanto em modo local com execucao dinamica do pipeline.

# Decisao

Manter frontend independente de backend:
- modo estatico: leitura de `docs/data/` (e `docs/data/local/` quando disponivel);
- modo dinamico: habilitacao condicional de endpoints Flask quando `/api/health` responde com sucesso.

# Consequencias

- Maior robustez operacional e menor acoplamento com infraestrutura.
- O app continua util mesmo sem API ativa.
- Mudancas de schema exigem sincronizacao entre exportador e frontend.

# Evidencias

- `webapp.py` (endpoints e health).
- `README.md` (MVP estatico e fallback local).
- nota em memoria de repositorio (`/memories/repo/run-notes.md`).
