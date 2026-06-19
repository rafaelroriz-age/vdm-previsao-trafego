---
title: Convencoes da Documentacao
type: knowledge
status: validated
confidence: 0.95
owner: engenharia
related:
  - README.md
  - plans/segundo-cerebro-roadmap.md
  - plans/duvidas-abertas.md
tags: [convencoes, frontmatter, quality]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define padrao de frontmatter, ai-summary e confidence para toda doc em docs/.
Flow: criar doc -> aplicar metadados -> validar rubrica -> publicar no hub.
Owner: engenharia.
Systems: docs/*.md.
Status: validated.
-->

# Convencoes da Documentacao

Este arquivo padroniza como Hermes e o time mantem a camada textual do projeto.

## Frontmatter obrigatorio

Todos os arquivos markdown em `docs/` devem iniciar com:

```yaml
---
title: <titulo legivel>
type: <process | system | decision | knowledge | meeting | plan>
status: <draft | review | validated>
confidence: <numero de 0.00 a 1.00>
owner: <time ou pessoa responsavel, se conhecido>
related:
  - <caminho/relativo/para/outro-doc.md>
tags: [<termo>, <termo>]
last_updated: <AAAA-MM-DD>
---
```

## AI summary obrigatorio

Logo abaixo do frontmatter, incluir:

```html
<!-- ai-summary
System: <o que este doc cobre em uma linha>
Flow: <passo -> passo -> passo>
Owner: <responsavel>
Systems: <sistemas/integrações citados>
Status: <validated | review | draft>
-->
```

## Rubrica de confidence

Somar os pesos aplicaveis (maximo 1.00):

- Atualizado nos ultimos ~90 dias: 0.25
- Status validated: 0.20
- Possui ai-summary: 0.15
- Tem cross-links coerentes (`related` + links no corpo): 0.15
- Completude tecnica sem lacunas obvias: 0.15
- Aderente ao codigo atual: 0.10

## Regras adicionais

- Em conflito entre doc antiga e codigo atual: o codigo vence.
- Se faltar evidencia: usar `status: draft` e registrar em `plans/duvidas-abertas.md`.
- Nao duplicar tema; consolidar por referencia cruzada.
- Toda doc migrada deve registrar origem em uma nota de rastreabilidade.
