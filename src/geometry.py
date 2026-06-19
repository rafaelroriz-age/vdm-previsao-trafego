"""
geometry.py
-----------
Constrói o mapa `sre → geometria` (WGS84 lon/lat) a partir da planilha georef
(coluna WKT `geom`) com fallback para o GeometryCollection JSON simplificado.

A geometria é alinhada por índice de linha ao JSON (web-simplificado, primário)
e por WKT da planilha (fallback), exatamente como no projeto original
`vdm-traffic-predict/build_base_geojson.py`. A junção com o dataset de
regressão é feita pela chave `sre`.
"""
from __future__ import annotations

import json

import pandas as pd
from shapely import wkt
from shapely.geometry import mapping, shape
from shapely.ops import transform


def _drop_z(geom):
    return transform(lambda x, y, z=None: (x, y), geom)


def _round_coords(coords, prec=6):
    if isinstance(coords[0], (list, tuple)):
        return [_round_coords(c, prec) for c in coords]
    return [round(c, prec) for c in coords]


def build_sre_geometry(georef_file, geometry_json) -> dict[str, dict]:
    """Retorna {sre: geojson_geometry_dict} para cada SRE com geometria válida.

    Primário: geometria do JSON por índice de linha (mapshaper-simplificada).
    Fallback: WKT da coluna `geom` da planilha georef.
    """
    df = pd.read_excel(georef_file)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    with open(geometry_json, encoding="utf-8") as f:
        gc = json.load(f)
    json_geoms = gc.get("geometries", [])

    sre2geom: dict[str, dict] = {}
    json_count = wkt_count = skip_count = 0

    for i, row in df.iterrows():
        geom = None
        # Primário: JSON por índice
        if i < len(json_geoms):
            try:
                g = shape(json_geoms[i])
                if not g.is_empty:
                    geom = g
                    json_count += 1
            except Exception:
                pass
        # Fallback: WKT da planilha
        if geom is None:
            try:
                g = wkt.loads(str(row.get("geom", "")))
                if not g.is_empty:
                    geom = _drop_z(g)
                    wkt_count += 1
            except Exception:
                pass
        if geom is None:
            skip_count += 1
            continue

        sre = str(row.get("sre", "")).strip()
        if not sre or sre in sre2geom:
            continue

        geom_dict = mapping(geom)
        geom_dict["coordinates"] = _round_coords(geom_dict["coordinates"])
        sre2geom[sre] = geom_dict

    print(f"   Geometria: {json_count} JSON, {wkt_count} WKT fallback, "
          f"{skip_count} ignoradas → {len(sre2geom)} SREs com geometria")
    return sre2geom


def geometry_midpoint(geom_dict) -> tuple[float, float] | None:
    """Retorna (lon, lat) do ponto médio de uma geometria LineString/MultiLineString."""
    gtype = geom_dict.get("type")
    coords = geom_dict.get("coordinates")
    if not coords:
        return None
    if gtype == "LineString":
        mid = coords[len(coords) // 2]
        return mid[0], mid[1]
    if gtype == "MultiLineString":
        sub = coords[len(coords) // 2]
        mid = sub[len(sub) // 2]
        return mid[0], mid[1]
    return None
