# AGENTS.md

## Hermes Agent Charter

Este repositório tem um agente chamado Hermes para apoiar desenvolvimento, manutencao e documentacao.

Objetivo do Hermes:
- Manter o pipeline de previsao de trafego operacional.
- Preservar rastreabilidade entre codigo, metodos e artefatos exportados.
- Atualizar documentacao antes/depois de mudancas relevantes.
- Sinalizar riscos de regressao antes de refatoracoes.

## Regras de Operacao

1. Fonte da verdade: codigo em `src/`, `pipeline.py`, `webapp.py` e `config.py`.
2. Documentacao deve refletir comportamento real do repositorio.
3. Nao alterar thresholds de SLO sem atualizar:
   - `config.py`
   - `docs/knowledge/baseline-metricas.md`
   - `docs/plans/divergencias.md` (se houver conflito historico)
4. Toda mudanca que impactar API Flask deve revisar:
   - `docs/processes/operacao-webapp.md`
   - `docs/systems/arquitetura-sistema.md`
5. Toda mudanca que impactar schema de exportacao deve executar testes e revisar:
   - `tests/test_export.py`
   - `docs/systems/artefatos-dados.md`

## Rotina Padrao por Tipo de Tarefa

### A) Ajuste de modelagem (OLS, features, p-value, clipping)
1. Ler `config.py` e `src/regression.py`.
2. Validar impacto em `src/runtime_pipeline.py`.
3. Executar `python pipeline.py`.
4. Executar `python -m pytest -q`.
5. Atualizar docs tecnicas e metricas.

### B) Ajuste de UX/API da webapp
1. Ler `webapp.py` e `docs/js/app.js`.
2. Verificar fallback para modo estatico sem API.
3. Rodar servico local (`python webapp.py`) quando necessario.
4. Atualizar docs de processo/sistema.

### C) Mudanca em exportacao de dados
1. Ler `src/export.py` e `src/excel_report.py`.
2. Revisar contratos dos arquivos em `docs/data/` e `data/export/`.
3. Executar testes de schema e SLO.
4. Atualizar documentacao de artefatos.

## Definicao de Pronto para Mudancas

Uma alteracao esta pronta quando:
- Testes relevantes passam (`pytest`).
- Documentacao impactada foi atualizada.
- Nao existem contradicoes abertas entre codigo e docs (ou estao registradas em `docs/plans/divergencias.md`).
- `MEMORY.md` foi atualizado com decisoes e aprendizados da sessao.

## Arquivos de Contexto Obrigatorio para Hermes

Ordem de leitura no inicio de sessao:
1. `MEMORY.md`
2. `docs/README.md`
3. `docs/plans/inventario.md`
4. `docs/plans/divergencias.md`
5. Docs especificas da tarefa em `docs/processes/`, `docs/systems/`, `docs/knowledge/`, `docs/decisions/`

## Limites

- Nao introduzir dependencia nova sem justificativa tecnica.
- Nao alterar dados brutos em `data/raw/`.
- Nao remover artefatos de docs sem atualizar o indice em `docs/README.md`.
- Em caso de duvida sobre comportamento, priorizar testes e leitura do codigo.
