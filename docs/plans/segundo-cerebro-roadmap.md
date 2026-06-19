---
title: Roadmap do Segundo Cerebro
type: plan
status: review
confidence: 0.85
owner: engenharia
related:
  - inventario.md
  - divergencias.md
  - duvidas-abertas.md
  - ../../AGENTS.md
tags: [roadmap, documentacao, automacao, agente]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define fases futuras para evoluir do baseline textual para automacao contextual completa.
Flow: base textual -> skills -> impacto -> automacao de validacao -> governance continua.
Owner: engenharia.
Systems: docs, skills, testes, pipeline de qualidade.
Status: review.
-->

# Fases futuras

## Fase 1 (concluida): Base textual

Entregas:
- Hub documental em `docs/`.
- Regras de convencao e score de confianca.
- AGENTS.md e MEMORY.md para operacao do Hermes.

Motivo:
- Criar referencia unica e navegavel para humanos e IA.

## Fase 2: Skills operacionais

Entregas:
- Consolidar uso de `skills/validate.md` e `skills/impact.md` em rotina.
- Adicionar skill `/prime` para leitura inicial de contexto.

Motivo:
- Padronizar comportamento do agente no inicio e fim das sessoes.

## Fase 3: Impact analysis com evidencia de codigo

Entregas:
- Definir checklist de impacto por modulo antes de refatoracoes.
- Conectar impactos a testes obrigatorios por area.

Motivo:
- Reduzir regressao silenciosa em runtime/exportacao/frontend.

## Fase 4: Automacao de qualidade documental

Entregas:
- Linter simples para frontmatter/ai-summary/links.
- Relatorio automatizado de docs com `status: draft` ou `confidence < 0.8`.

Motivo:
- Evitar degradacao da qualidade documental ao longo do tempo.

## Fase 5: Governance continua

Entregas:
- Ritual de revisao quinzenal de divergencias e duvidas abertas.
- Processo de atualizacao de ADR a cada decisao arquitetural relevante.

Motivo:
- Manter o segundo cerebro vivo e confiavel.
