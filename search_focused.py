"""Busca focada por target incluindo features de localização (referência por rodovia)."""
from itertools import combinations

import config as cfg
from search import eval_features
from src import data_prep


def main():
    df = data_prep.load_dataset(cfg.DATASET_FILE)
    df = data_prep.apply_boolean_merge(df, cfg.BOOLEAN_MERGES)
    df = data_prep.apply_group_merge(df, cfg.GROUP_COL, cfg.GROUP_MERGES)
    df = data_prep.feature_engineering(df, cfg.TARGETS, cfg.GROUP_COL)
    for t in cfg.TARGETS:
        pool = ["go", "situacao_is_dup", "perim_urb", "log_media_empresas_ativas",
                "log_media_pib", "log_excesso_frotas_km", "log_distancia_cid_1",
                f"{t}_media_go", f"{t}_media_regional"]
        slo = cfg.SLO[t]
        best = []
        for k in (4, 5):
            for c in combinations(pool, k):
                ev = eval_features(df, t, list(c), max_features=6)
                if ev:
                    best.append((ev[0] * 100 - ev[1] / 5.0, ev[0], ev[1], ev[3]))
        best.sort(key=lambda z: z[0], reverse=True)
        print(f"=== {t} (SLO R2>={slo['r2_min']}, MAPE<={slo['mape_max']}) ===")
        for s, r2, mape, kept in best[:5]:
            ok = "OK" if (r2 >= slo["r2_min"] and mape <= slo["mape_max"]) else "  "
            print(f"  {ok} R2={r2:.3f} MAPE={mape:5.1f}% {kept}")


if __name__ == "__main__":
    main()
