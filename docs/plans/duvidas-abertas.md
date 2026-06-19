---
title: Duvidas Abertas
type: plan
status: draft
confidence: 0.70
owner: engenharia
related:
  - inventario.md
  - divergencias.md
  - segundo-cerebro-roadmap.md
tags: [duvidas, pendencias, validacao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: lista ambiguidades que precisam de confirmacao para elevar confianca da documentacao.
Flow: capturar duvida -> apontar evidencia -> definir proximo passo.
Owner: engenharia.
Systems: docs/js/app.js, src/runtime_pipeline.py, infraestrutura de deploy.
Status: draft.
-->

# Pendencias

1. Validar em teste manual o fallback completo do frontend para `docs/data/local/`.
2. Decidir se `default_runtime_config().log_transform` deve ser `True` para alinhar com batch.
3. Confirmar estrategia oficial de deploy dinamico (somente local Flask ou algum ambiente server-side previsto).
4. Definir owner nominal (pessoa/time) para cada categoria de documentacao.
