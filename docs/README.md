---
title: Hub de Documentacao Operacional
type: knowledge
status: validated
confidence: 0.95
owner: engenharia
related:
	- CONVENTIONS.md
	- plans/inventario.md
	- plans/divergencias.md
tags: [hub, documentacao, navegacao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: indice central da documentacao operacional para humanos e agente Hermes.
Flow: abrir memory -> consultar inventario/divergencias -> navegar por processos/sistemas/decisoes.
Owner: engenharia.
Systems: docs/*, MEMORY.md.
Status: validated.
-->

# Documentacao Operacional (Segundo Cerebro)

Hub de navegacao para humanos e para o agente Hermes.

## Como usar este hub

1. Leia `../MEMORY.md` para estado atual.
2. Leia `plans/inventario.md` para saber o que foi migrado, atualizado ou criado.
3. Se houver conflito doc x codigo, veja `plans/divergencias.md`.
4. Para executar tarefas, siga os runbooks de `processes/`.

## Convencoes

- [CONVENTIONS.md](CONVENTIONS.md)

## Processos

- [pipeline-batch.md](processes/pipeline-batch.md): execucao do pipeline offline, validacao e exportacao.
- [operacao-webapp.md](processes/operacao-webapp.md): execucao da webapp Flask e fluxo runtime.

## Sistemas

- [arquitetura-sistema.md](systems/arquitetura-sistema.md): componentes e fluxos entre batch, runtime e frontend.
- [artefatos-dados.md](systems/artefatos-dados.md): contratos de arquivos JSON/GeoJSON/XLSX.

## Conhecimento de Dominio

- [baseline-metricas.md](knowledge/baseline-metricas.md): metodologia, metricas e SLO do projeto.
- [glossario.md](knowledge/glossario.md): definicoes das features usadas nas equacoes.

## Decisoes (ADRs)

- [ADR-0001-ols-com-smearing.md](decisions/ADR-0001-ols-com-smearing.md)
- [ADR-0002-front-static-api-opcional.md](decisions/ADR-0002-front-static-api-opcional.md)

## Planos e Governanca

- [inventario.md](plans/inventario.md): inventario de conhecimento consolidado.
- [divergencias.md](plans/divergencias.md): registro de divergencias entre docs antigas e codigo atual.
- [duvidas-abertas.md](plans/duvidas-abertas.md): pendencias de contexto.
- [segundo-cerebro-roadmap.md](plans/segundo-cerebro-roadmap.md): proximas camadas de automacao.

## Meetings

- [README.md](meetings/README.md): como registrar reunioes e decisoes futuras.
