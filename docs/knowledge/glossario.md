---
title: Glossario de Features
type: knowledge
status: validated
confidence: 0.90
owner: engenharia de dados
related:
   - baseline-metricas.md
   - ../processes/pipeline-batch.md
   - ../systems/artefatos-dados.md
tags: [glossario, features, regressao]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define semanticamente cada feature usada nas equacoes de regressao.
Flow: identificar feature -> entender origem -> aplicar na formula com smearing.
Owner: engenharia de dados.
Systems: config.py, src/formulas.py, src/regression.py.
Status: validated.
-->

# Glossário de Features

> Migrado e consolidado de documentacao tecnica existente no projeto.

Variáveis usadas nas equações de regressão, para engenheiros e técnicos.

| Feature | Significado | Como obter |
|---|---|---|
| `go` | Número da rodovia estadual (ex.: 010, 020). Proxy de eixo/importância. | Cadastro SRE |
| `situacao_is_dup` | 1 se a pista é **duplicada** (situação = DUP), senão 0. | Cadastro SRE (campo `situacao`) |
| `perim_urb` / `perim_urb_s` | 1 se o trecho está em **perímetro urbano** ("s"), senão 0. | Cadastro SRE |
| `log_media_pib` | Logaritmo natural (ln(1+x)) do **PIB médio** dos municípios do trecho. | Base socioeconômica |
| `log_media_empresas_ativas` | ln(1+x) do número médio de **empresas ativas**. | Base socioeconômica |
| `log_distancia_cid_1` | ln(1+x) da **distância à cidade principal** (km). | Geoprocessamento |
| `log_excesso_frotas_km` | ln(1+x) do **excesso de frota por km** relativo à média da região. | Derivado (frota/extensão ÷ média regional) |
| `<target>_media_go` | **Valor de referência**: média observada do target (vmd/vmdc/n) na **mesma rodovia (GO)**. | Tabela de referência por rodovia |

## Como aplicar a equação (passo a passo)

Os modelos são **em log**. Para um segmento:

1. Calcule o lado direito da fórmula (texto/Excel) com as features acima.
   Resultado = `log(ŷ)`.
2. Aplique a retransformação: `ŷ = EXP(log(ŷ)) × smearing`.
   O fator `smearing` (Duan) está na aba **Modelo** do mapa e na planilha Excel.

Exemplo (VMD): `smearing ≈ 1.193`.

> A aba **Modelo** do site mostra a fórmula pronta (LaTeX e Excel) e o fator de
> smearing para cada variável. A planilha `data/export/sre_previsao_trafego.xlsx`
> (aba `equacoes`) traz fórmulas Excel que já referenciam as colunas dos dados.
