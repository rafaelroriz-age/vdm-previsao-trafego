---
title: Registro de Reunioes
type: meeting
status: draft
confidence: 0.75
owner: engenharia
related:
  - ../plans/duvidas-abertas.md
  - ../decisions/ADR-0001-ols-com-smearing.md
  - ../decisions/ADR-0002-front-static-api-opcional.md
tags: [meeting, alinhamento, decisao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define formato para registrar reunioes tecnicas e converter decisoes em ADR.
Flow: reuniao -> resumo -> decisoes -> atualizar ADR/memory.
Owner: engenharia.
Systems: docs/decisions, MEMORY.md.
Status: draft.
-->

# Como registrar reunioes

Para cada reuniao relevante, criar arquivo `YYYY-MM-DD-tema.md` nesta pasta contendo:

1. Participantes.
2. Problema discutido.
3. Decisoes tomadas.
4. Acoes e responsaveis.
5. Se abriu ADR nova (sim/nao).

## Regra

Se houver decisao arquitetural, abrir/atualizar ADR no mesmo dia.
