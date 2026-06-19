---
title: Divergencias entre Documentacao e Codigo
type: plan
status: review
confidence: 0.80
owner: engenharia
related:
  - inventario.md
  - duvidas-abertas.md
  - ../processes/operacao-webapp.md
  - ../knowledge/baseline-metricas.md
tags: [divergencia, rastreabilidade, manutencao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: registra conflitos entre narrativa documental e comportamento real do codigo.
Flow: identificar conflito -> registrar evidencia -> definir acao corretiva.
Owner: engenharia.
Systems: README.md, webapp.py, src/runtime_pipeline.py, docs/knowledge.
Status: review.
-->

# Divergencias registradas

## 1) Runtime default de log-transform

- Contexto antigo: README descreve log-transform como metodologia padrao do projeto.
- Codigo atual: `src/runtime_pipeline.py` define `log_transform: False` no `default_runtime_config()` para o modo runtime.
- Impacto: usuario pode executar runtime sem log-transform, obtendo comportamento diferente do batch padrao.
- Acao: manter divergencia documentada e revisar se default runtime deve alinhar com batch.

## 2) Artefatos locais em docs/data/local

- Contexto antigo: README menciona fallback para `docs/data/local/` no frontend estatico.
- Codigo verificado aqui: comportamento de fallback depende de implementacao em `docs/js/app.js` (nao documentada em detalhe tecnico no momento).
- Impacto: risco de expectativa incorreta se logica JS divergir da documentacao textual.
- Acao: manter `status: review` em docs de artefatos ate validar fluxo JS com teste manual.

## 3) Metricas "honestas" vs avaliacao em amostra

- Contexto antigo: baseline destaca honestidade e ressalvas de metrica em amostra.
- Codigo atual: testes e relatorios continuam centrados em metrica interna da amostra de treino.
- Impacto: risco de interpretar metricas como generalizacao fora de amostra.
- Acao: manter alerta explicito em `docs/knowledge/baseline-metricas.md` e no processo de validacao.
