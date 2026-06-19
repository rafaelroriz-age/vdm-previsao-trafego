# Previsão de Tráfego — Goiás (Regressão OLS)

Sistema que **prevê e extrapola variáveis de tráfego** para toda a malha
rodoviária estadual de Goiás usando **regressão linear (OLS)** com features
explicáveis, e publica os resultados em um **mapa georreferenciado interativo**.

Une duas frentes:

- **Processamento de dados** (regressão OLS, features, fórmulas, Excel) — herdado
  de `vdm-regressao-previsto`.
- **Visualização georreferenciada** (Leaflet + GeoJSON, deploy GitHub Pages) —
  herdada de `vdm-traffic-predict`.

## Variáveis previstas (targets)

| Target | Descrição |
|---|---|
| `vmd` | Volume Médio Diário (veículos/dia) |
| `vmdc` | VMD de veículos comerciais/pesados |
| `n_usace` | Número N (repetições do eixo padrão) — método USACE |
| `n_aashto` | Número N — método AASHTO |

## Resultados (dataset oficial v4, 183 amostras de treino)

Todos os targets **atendem o critério de aceite (SLO)**:

| Target | R² global | MAPE | SLO (R² / MAPE) | Status |
|---|---|---|---|---|
| vmd | **0.632** | 69.4% | ≥0.60 / ≤75% | ✅ |
| vmdc | **0.607** | 68.4% | ≥0.55 / ≤75% | ✅ |
| n_aashto | **0.592** | 78.0% | ≥0.55 / ≤80% | ✅ |
| n_usace | **0.575** | 95.0% | ≥0.50 / ≤100% | ✅ |

> Métricas honestas, calculadas no espaço original a partir dos resíduos de
> treino. Ver `docs/knowledge/baseline-metricas.md` para a metodologia e
> ressalvas (em especial o caráter *em amostra* das features de referência).

## Metodologia (resumo)

- **OLS** (`statsmodels`) — um modelo global por target.
- **Log-transform do alvo** + **fator de Duan (smearing)** na retransformação —
  evita previsões negativas e corrige o viés de `exp(média de logs)`.
- **Backward elimination por p-value** (limite 0.15) + corte em **≤ 6 features**
  por `|t-stat|`, garantindo explicabilidade.
- `regional_macro` com merge **2+3** (região 2 tem só 7 amostras).
- **Clipping** de previsões em `[0.3×, 3.0×]` da mediana regional.
- Features de **referência por rodovia** (`<target>_media_go`): média observada
  do target na mesma GO — um valor consultável em tabela, fortemente preditivo.

As equações são exportadas em **texto, LaTeX e fórmula Excel** (PT-BR), para uso
em calculadoras, planilhas ou documentos técnicos por qualquer engenheiro.

## Estrutura

```
config.py                 # configuração: features por target, SLO, caminhos
pipeline.py               # orquestrador: dados → OLS → exportação
search.py / search_focused.py  # busca de features explicáveis (offline)
src/
  data_prep.py            # carga, merges, feature engineering
  regression.py           # OLS, backward elimination, smearing (núcleo)
  formulas.py             # equação → LaTeX / Excel
  geometry.py             # sre → geometria (WGS84) via JSON + WKT
  export.py               # GeoJSON + model_metrics + calibration_report
  excel_report.py         # planilha Excel (dados, calibração, equações)
data/
  raw/                    # entradas (xlsx + SRE-GO json)
  export/                 # saídas (json/geojson + xlsx)
docs/                     # site estático (GitHub Pages)
  index.html, css/, js/, data/
tests/                    # pytest (regressão + schema de exportação)
```

## Como rodar

```powershell
pip install -r requirements.txt

# 1) Gerar previsões + artefatos do mapa + Excel
python pipeline.py

# 2) Validar (testes + SLO)
python -m pytest -q

# 3) Visualizar MVP estático
python -m http.server 8778 --directory docs
# abra http://localhost:8778
```

> MVP atual: front-end estático, sem dependência de API. O mapa carrega apenas a partir de arquivos em `docs/data/local/` (prioritário) ou `docs/data/`.

## Dataset JSON local privado (gitignored)

Se quiser ler dados transformados em JSON sem versionar no repositório:

1. Crie a pasta `docs/data/local/`.
2. Coloque nela os quatro arquivos:
  - `segments.geojson`
  - `count_points.geojson`
  - `model_metrics.json`
  - `calibration_report.json`
3. Abra o site estático normalmente (`python -m http.server 8778 --directory docs`).

O app tenta carregar primeiro `docs/data/local/` e, se não encontrar, usa `docs/data/`.
As extensões `.json` e `.geojson` em `docs/data/local/` estão no `.gitignore` para manter esses dados fora do Git.

## Deploy

O site é estático. Publique a pasta `docs/` no **GitHub Pages** (branch +
`/docs`). O `pipeline.py` já escreve os JSON/GeoJSON em `docs/data/`.

## Frontend

- **Seletor de variável** (VMD / VMDc / N-USACE / N-AASHTO) — recolore o mapa,
  recalcula a escala e atualiza calibração e equação.
- **Resultado**: mapa georreferenciado (observado = linha cheia, previsto =
  tracejado), filtros, busca por SRE/GO, distribuição e média por regional.
- **Calibração**: dispersão observado×estimado, histograma de erro, R²/MAE/RMSE/MAPE.
- **Modelo**: SLO, equação em LaTeX (KaTeX), fórmula Excel copiável, coeficientes
  e p-valores, nota de retransformação (Duan).
