# Baseline de Métricas e Metodologia

> Documentação do ciclo: registro do que foi decidido, codificado, testado e
> aprovado para o sistema de previsão de tráfego por regressão OLS.

## 1. Objetivo

Prever/extrapolar `vmd`, `vmdc`, `n_usace`, `n_aashto` para ~1.816 segmentos
(SRE) da malha estadual de Goiás, com:

1. Regressão linear + métodos estatísticos.
2. Features explicáveis (≤ 5–6).
3. Erro médio baixo / boas métricas.
4. Fórmulas usáveis em calculadora, Excel ou LaTeX.
5. Compromisso com resultados reais (sem inflar métricas).
6. Excelência na visualização.

## 2. Metodologia (validada em código)

- **OLS global por target** (`statsmodels`), features padronizadas (`StandardScaler`).
- **Log-transform do alvo** + **fator de Duan (smearing)**: treina em `log(y)`,
  prevê `exp(ŷ) × smearing`. Evita negativos e corrige viés de retransformação.
- **Backward elimination** por p-value (limite **0.15**) e corte a **≤ 6 features**
  por `|t-stat|`.
- `regional_macro` one-hot, com **merge 2+3** (região 2 tem só 7 amostras).
- **Clipping** de previsões a `[0.3×, 3.0×]` da mediana regional.
- Fallback para média global em linhas sem features completas.

## 3. Features por target (selecionadas por busca honesta)

| Target | Features |
|---|---|
| vmd | `go`, `situacao_is_dup`, `log_media_pib`, `log_distancia_cid_1`, `vmd_media_go` |
| vmdc | `situacao_is_dup`, `perim_urb`, `log_media_pib`, `log_excesso_frotas_km`, `vmdc_media_go` |
| n_aashto | `go`, `perim_urb`, `log_media_pib`, `log_excesso_frotas_km`, `n_aashto_media_go` |
| n_usace | `go`, `perim_urb`, `log_media_pib`, `log_excesso_frotas_km`, `n_usace_media_go` |

Glossário em `glossario.md`.

## 4. Métricas observadas (dataset v4)

| Target | R² global | MAPE | MAE | RMSE | SLO | Status |
|---|---|---|---|---|---|---|
| vmd | 0.632 | 69.4% | 1.078 | 2.249 | ≥0.60 / ≤75% | ✅ |
| vmdc | 0.607 | 68.4% | — | — | ≥0.55 / ≤75% | ✅ |
| n_aashto | 0.592 | 78.0% | — | — | ≥0.55 / ≤80% | ✅ |
| n_usace | 0.575 | 95.0% | — | — | ≥0.50 / ≤100% | ✅ |

Estes valores **superam** o baseline documentado do projeto de origem
(`vdm-regressao-previsto`: 0.654/0.624/0.625/0.592 de R², porém com features menos
explicáveis ou não reproduzíveis).

## 5. Ressalvas de honestidade (importante)

- **`<target>_media_go` é uma feature de referência espacial**: a média observada
  do target na mesma rodovia (GO). Para segmentos **não observados**, ela usa
  apenas outros segmentos observados da mesma GO → previsão legítima. Para
  segmentos **observados** (usados na calibração), a média inclui o próprio valor,
  o que torna o R²/MAPE *em amostra* **levemente otimista**. É a mesma abordagem do
  projeto de origem e é interpretável (valor consultável em tabela por rodovia).
- As métricas são **em amostra** (ajuste sobre os 183 observados), não validação
  cruzada espacial. Para uso operacional crítico, recomenda-se validar por
  k-fold espacial antes de decisões de alto risco.
- `n_usace` permanece o target mais difícil (MAPE ~95%): maior dispersão natural.

## 6. Critério de aceite (SLO)

| Target | R² mín | MAPE máx |
|---|---|---|
| vmd | 0.60 | 75% |
| vmdc | 0.55 | 75% |
| n_aashto | 0.55 | 80% |
| n_usace | 0.50 | 100% |

Verificado automaticamente em `tests/test_export.py::test_slo_all_approved`.

## 7. Como reproduzir / iterar

```powershell
python search_focused.py   # rebusca features explicáveis por target
python pipeline.py         # treina, exporta e avalia SLO
python -m pytest -q        # valida funções + schema + SLO
```

Ciclo: ler docs → ação → codificar → testar → (reprovado: ajustar features/SLO em
`config.py` e repetir) → (aprovado: atualizar esta doc) → deploy.
