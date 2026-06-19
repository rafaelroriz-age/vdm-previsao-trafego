---
title: ADR 0001 - OLS com log-transform e smearing
type: decision
status: validated
confidence: 0.90
owner: arquitetura
related:
  - ../knowledge/baseline-metricas.md
  - ../processes/pipeline-batch.md
  - ../systems/arquitetura-sistema.md
tags: [adr, regressao, ols, smearing, metodologia]
last_updated: 2026-06-19
---

<!-- ai-summary
System: define decisao de modelagem estatistica principal do projeto.
Flow: treinar em log(y) -> retransformar com Duan -> avaliar SLO por target.
Owner: arquitetura.
Systems: src/regression.py, config.py.
Status: validated.
-->

# Contexto

O dominio de trafego apresenta distribuicao assimetrica e risco de previsoes negativas quando modelado no espaco original. Era necessario manter explicabilidade e estabilidade operacional.

# Decisao

Adotar regressao OLS por target com:
- treino em `log(y)`;
- retransformacao com fator de Duan (smearing);
- backward elimination por p-value;
- limite de features para manter interpretabilidade.

# Consequencias

- Previsoes nao negativas e menor vies de retransformacao.
- Equacoes continuam legiveis para uso tecnico (LaTeX/Excel).
- Metricas em amostra devem ser interpretadas com ressalvas.

# Evidencias

- `config.py` (flags e thresholds).
- `src/regression.py` (pipeline de treino/predicao).
- `docs/knowledge/baseline-metricas.md` (resultados e ressalvas).
