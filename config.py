"""
config.py
---------
Configuração central do pipeline de previsão de tráfego por regressão OLS.

Toda a metodologia (features explicáveis, p-value, log-transform, merge regional)
foi validada empiricamente no projeto `vdm-regressao-previsto`
(ver docs/knowledge/baseline-metricas.md).
"""
from __future__ import annotations

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Caminhos
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
EXPORT_DIR = BASE_DIR / "data" / "export"
DOCS_DATA_DIR = BASE_DIR / "docs" / "data"

# Dataset oficial (features + targets, 1 linha por SRE)
DATASET_FILE = RAW_DIR / "sre_abr_2026_georef_vdm_v4.xlsx"

# Fonte de geometria georreferenciada
GEOREF_FILE = RAW_DIR / "sre_abr_2026_georef.xlsx"          # WKT 'geom' + 'sre'
GEOMETRY_JSON = RAW_DIR / "SRE-GO_2026_ABR.json"            # GeometryCollection (index-aligned)

# ─────────────────────────────────────────────────────────────────────────────
# Modelagem
# ─────────────────────────────────────────────────────────────────────────────
GROUP_COL = "regional_macro"
TARGETS = ["vmd", "vmdc", "n_aashto", "n_usace"]

# Features explicáveis por target (≤ 5, todas usáveis em fórmula/Excel).
# Selecionadas por busca honesta (search_focused.py). Glossário:
#   go                          → número da rodovia (eixo/importância)
#   situacao_is_dup             → pista duplicada (boolean, de situacao=DUP)
#   perim_urb                   → perímetro urbano (s/n → one-hot perim_urb_s)
#   log_media_pib               → PIB médio dos municípios (log)
#   log_media_empresas_ativas   → empresas ativas (log)
#   log_distancia_cid_1         → distância à cidade principal (log)
#   log_excesso_frotas_km       → frota/km relativa à média regional (log)
#   <target>_media_go           → VALOR DE REFERÊNCIA: média observada do target
#                                 na mesma rodovia (GO). Consultável em tabela.
FEATURES_PER_TARGET = {
    "vmd":      ["go", "situacao_is_dup", "log_media_pib", "log_distancia_cid_1", "vmd_media_go"],
    "vmdc":     ["situacao_is_dup", "perim_urb", "log_media_pib", "log_excesso_frotas_km", "vmdc_media_go"],
    "n_aashto": ["go", "perim_urb", "log_media_pib", "log_excesso_frotas_km", "n_aashto_media_go"],
    "n_usace":  ["go", "perim_urb", "log_media_pib", "log_excesso_frotas_km", "n_usace_media_go"],
}

# Tratamento por coluna na codificação
ENCODING_CHOICES = {
    "perim_urb": "onehot",
}

# Merges
BOOLEAN_MERGES = {"situacao": (["DUP"], "situacao_is_dup")}
GROUP_MERGES = [(["2", "3"], "2+3")]

# Hiperparâmetros (validados)
PVALUE_THRESHOLD = 0.15
LOG_TRANSFORM = True
MAX_FEATURES = 6
CLIP_PREDICTIONS = True

# Nenhuma feature é obrigatória por padrão (backward elimination livre)
MANDATORY_PER_TARGET: dict[str, list[str]] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Critérios de aceite (SLO) — validados com dados reais (dataset v4, 183 treino)
# ─────────────────────────────────────────────────────────────────────────────
SLO = {
    "vmd":      {"r2_min": 0.60, "mape_max": 75.0},
    "vmdc":     {"r2_min": 0.55, "mape_max": 75.0},
    "n_aashto": {"r2_min": 0.55, "mape_max": 80.0},
    "n_usace":  {"r2_min": 0.50, "mape_max": 100.0},
}
