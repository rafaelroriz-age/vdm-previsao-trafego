# MEMORY.md

## Estado Atual do Projeto

- Projeto: previsao de trafego para malha rodoviaria de Goias com regressao OLS.
- Pipeline principal: `pipeline.py`.
- Modo web dinamico: `webapp.py` (Flask em http://localhost:8777).
- Modo estatico: site em `docs/` consumindo arquivos em `docs/data/`.

## Fontes de Verdade

- Configuracao de modelagem e SLO: `config.py`.
- Logica de regressao: `src/regression.py`.
- Exportacao GeoJSON/JSON/Excel: `src/export.py` e `src/excel_report.py`.
- Runtime configuravel para UI: `src/runtime_pipeline.py`.

## Decisoes Recentes

- O modelo usa OLS com log-transform e fator de Duan (smearing) para retransformacao.
- O frontend funciona em modo estatico e habilita recursos dinamicos quando API Flask esta saudavel.
- Artefatos finais sao persistidos em `data/export/` e `docs/data/`.

## Aprendizados Relevantes

- Alteracoes em features por target exigem revisao simultanea de pipeline batch e runtime.
- Mudancas de schema de exportacao quebram visualizacao se `docs/js/app.js` nao for revisado.
- A documentacao tecnica precisa indicar quando metricas sao em amostra para evitar interpretacao incorreta.

## Nunca Esquecer

- Nao commitar segredos.
- Nao assumir que documentacao antiga esta correta: validar no codigo.
- Sempre executar testes apos alteracoes de regressao/exportacao.

## Checklist de Encerramento de Sessao

1. Registrar decisoes tomadas hoje.
2. Registrar riscos pendentes.
3. Atualizar docs impactadas e links relacionados.
4. Confirmar se existe divergencia nova em `docs/plans/divergencias.md`.
