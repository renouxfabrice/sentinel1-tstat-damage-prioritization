# -*- coding: utf-8 -*-
"""Comptage des dommages par tranche d'intensité MMI et par produit, puis vérification que le taux de dommage de chaque produit croît bien avec l'intensité sismique.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
from config import DONNEES

try:
    from osgeo import ogr, osr
    import numpy as np
except ImportError:
    sys.exit("osgeo (gdal/ogr) et numpy requis.")

ogr.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v3.gpkg")

BUILDINGS_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg")
BUILDINGS_OVERTURE_ID_FIELD = "id"

MMI_SHP_PATH = os.path.join(DONNEES, r"VENEZUELA\UNGSC\M 7.5 - 17 km W of Catia La Mar_Venezuela\mi.shp")
MMI_VALUE_FIELD = "PARAMVALUE"

MMI_BINS = [
    (float('-inf'), 1.5, 'I', 1),
    (1.5, 3.5, 'II-III', 2),
    (3.5, 4.5, 'IV', 3),
    (4.5, 5.5, 'V', 4),
    (5.5, 6.5, 'VI', 5),
    (6.5, 7.5, 'VII', 6),
    (7.5, 8.5, 'VIII', 7),
    (8.5, 9.5, 'IX', 8),
    (9.5, float('inf'), 'X+', 9),
]

# MEME DAMAGE_CONFIG que le script 1 — copie ici pour rester autonome.
DAMAGE_CONFIG = {
    'microsoft': {
        'path': os.path.join(DONNEES, r"VENEZUELA\Microsoft AI for Good Lab\from_huggingFace\venezuela_microsoft_damage_points.geojson"),
        'kind': 'points', 'class_field': 'severity',
        'damaged_values': ['damaged'], 'destroyed_values': [], 'excluded_values': [],
    },
    'impact': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\impact_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'osu': {
        'path': os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'label',
        'damaged_values': ['likely_damaged'], 'destroyed_values': [], 'excluded_values': ['not_assessed'],
    },
    'uhsail': {
        'path': os.path.join(DONNEES, r"VENEZUELA\UH SAIL\Building damaged.gpkg"),
        'kind': 'points', 'class_field': 'grade',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'unep': {
        'path': os.path.join(DONNEES, r"VENEZUELA\UNEP\debris_buildings.gpkg"),
        'kind': 'points', 'class_field': None,
        'damaged_values': None, 'destroyed_values': [], 'excluded_values': [],
    },
    'fair': {
        'path': os.path.join(DONNEES, r"VENEZUELA\Fair\ALL\damage_polygones_fair.gpkg"),
        'kind': 'points', 'class_field': 'damage',
        'damaged_values': ['minor-damage', 'major-damage'], 'destroyed_values': ['destroyed'],
        'excluded_values': ['no-data (cloud)', 'no-data (no pre)'],
    },
    'ems': {
        'path': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpPV2.gpkg"),
        'kind': 'points', 'class_field': 'damage_gra',
        'damaged_values': ['Damaged'], 'destroyed_values': ['Destroyed'],
        'probably_damaged_values': ['Possibly damaged'],
        'excluded_values': [],
    },
    'disha': {
        'path': os.path.join(DONNEES, r"VENEZUELA\DISHA\Caracas\nwcaracas_final_inference_result.csv"),
        'kind': 'points_csv', 'class_field': 'damaged',
        'damaged_values': ['TRUE', 'True', True], 'destroyed_values': [], 'excluded_values': [],
    },
    'chatmap': {
        'path': os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_venezuela_points.geojson"),
        'kind': 'points', 'class_field': 'damaged',
        'damaged_values': ['significant', 'minimal'], 'destroyed_values': ['complete'], 'excluded_values': [],
    },
    'nasa_s1': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s1_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'nasa_s2': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s2_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'eos': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    't_test': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\t_test_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'bdpm': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\bdpm_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
}

OUT_CSV_COMPTAGE = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\mmi_source_comptage.csv")
OUT_CSV_COHERENCE = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\mmi_coherence_analyse.csv")

SEP = "=" * 70

# =============================================================================
# HELPERS (identiques aux scripts 1 et 3)
# =============================================================================

WGS84 = osr.SpatialReference()
WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def get_transform_to_wgs84(lyr):
    src_srs = lyr.GetSpatialRef()
    if src_srs is None:
        return None
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if src_srs.IsSame(WGS84):
        return None
    return osr.CoordinateTransformation(src_srs, WGS84)


def load_union_geom(path):
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    geoms = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        geoms.append(g2)
    ds = None
    if not geoms:
        return None
    union = geoms[0]
    for g in geoms[1:]:
        union = union.Union(g)
    return union


def get_aoi_bounds(geom):
    return geom.GetEnvelope()[0], geom.GetEnvelope()[2], geom.GetEnvelope()[1], geom.GetEnvelope()[3]


def load_overture_buildings(path, id_field, aoi_bounds):
    ds = ogr.Open(path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        out[feat.GetField(id_field)] = g2
    ds = None
    print(f"  {len(out):,} batiment(s) Overture charge(s)")
    return out


def mmi_category(value):
    for lo, hi, label, rank in MMI_BINS:
        if lo <= value < hi:
            return label, rank
    return None, None


def load_mmi_grid_for_bounds(mmi_path, value_field, aoi_bounds):
    """Charge les cellules MMI (geometrie + valeur) restreintes a
    l'emprise — pour un test point-dans-cellule rapide par batiment."""
    ds = ogr.Open(mmi_path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {mmi_path}")
    lyr = ds.GetLayer()
    defn = lyr.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    if value_field not in field_names:
        sys.exit(f"Erreur: champ '{value_field}' introuvable — champs: {field_names}")
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    cells = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        val = feat.GetField(value_field)
        if val is None:
            continue
        cells.append((g2, float(val)))
    ds = None
    print(f"  {len(cells):,} cellule(s) MMI chargee(s)")
    return cells


def build_bucket_index(cells, bucket_size=0.02):
    buckets = {}
    for i, (g, _) in enumerate(cells):
        env = g.GetEnvelope()
        cx, cy = (env[0] + env[1]) / 2, (env[2] + env[3]) / 2
        key = (int(cx / bucket_size), int(cy / bucket_size))
        buckets.setdefault(key, []).append(i)
    return buckets, bucket_size


def mmi_for_point(pt, cells, buckets, bucket_size):
    bx, by = int(pt.GetX() / bucket_size), int(pt.GetY() / bucket_size)
    cand = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cand.extend(buckets.get((bx + dx, by + dy), []))
    for i in cand:
        g, val = cells[i]
        if g.Contains(pt):
            return val
    return None


def standardize(cfg, raw):
    if raw in (cfg.get('excluded_values') or []):
        return None, None, None, None
    destroyed_vals = cfg.get('destroyed_values') or []
    probably_vals = cfg.get('probably_damaged_values') or []
    damaged_vals = cfg.get('damaged_values')
    if cfg.get('class_field') is None:
        return 'damaged', 0, 1, 0  # (classe, probably, damaged, destroyed)
    if raw in destroyed_vals:
        return 'destroyed', 0, 0, 1
    if raw in probably_vals:
        return 'probably_damaged', 1, 0, 0
    if damaged_vals is None or raw in damaged_vals:
        return 'damaged', 0, 1, 0
    return 'not_damaged', 0, 0, 0


def load_overture_source(cfg):
    ds = ogr.Open(cfg['path'])
    if ds is None:
        print(f"    Attention: impossible d'ouvrir — {cfg['path']}")
        return {}
    lyr = ds.GetLayer()
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if cfg['id_field'] not in field_names or (cfg['class_field'] and cfg['class_field'] not in field_names):
        print(f"    ERREUR: champ manquant — champs disponibles: {field_names}")
        ds = None
        return {}
    out = {}
    for feat in lyr:
        out[feat.GetField(cfg['id_field'])] = feat.GetField(cfg['class_field'])
    ds = None
    return out


def load_points_source(cfg):
    ds = ogr.Open(cfg['path'])
    if ds is None:
        print(f"    Attention: impossible d'ouvrir — {cfg['path']}")
        return []
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    class_field = cfg.get('class_field')
    if class_field is not None and class_field not in field_names:
        print(f"    ERREUR: champ '{class_field}' introuvable — champs: {field_names}")
        ds = None
        return []
    out = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        raw = feat.GetField(class_field) if class_field else None
        out.append((g2, raw))
    ds = None
    return out


def load_points_csv_source(cfg):
    class_field = cfg.get('class_field')
    out = []
    with open(cfg['path'], newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lon = float(row.get('lon') or row.get('longitude') or row.get('x'))
                lat = float(row.get('lat') or row.get('latitude') or row.get('y'))
            except (TypeError, ValueError):
                continue
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint(lon, lat)
            out.append((pt, row.get(class_field)))
    return out


def match_points_to_buildings(source_entities, buildings_dict, bucket_size=0.005):
    buckets = {}
    for i, (g, _) in enumerate(source_entities):
        env = g.GetEnvelope()
        cx, cy = (env[0] + env[1]) / 2, (env[2] + env[3]) / 2
        key = (int(cx / bucket_size), int(cy / bucket_size))
        buckets.setdefault(key, []).append(i)
    out = {}
    for oid, bgeom in buildings_dict.items():
        env = bgeom.GetEnvelope()
        cx, cy = (env[0] + env[1]) / 2, (env[2] + env[3]) / 2
        bx, by = int(cx / bucket_size), int(cy / bucket_size)
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand.extend(buckets.get((bx + dx, by + dy), []))
        best_raw, best_area, found = None, 0.0, False
        for i in cand:
            g, raw = source_entities[i]
            if not g.Intersects(bgeom):
                continue
            found = True
            try:
                inter = g.Intersection(bgeom)
                area = inter.Area() if inter else 0.0
            except Exception:
                area = 1e-12
            if area >= best_area:
                best_area = area
                best_raw = raw
        if found:
            out[oid] = best_raw
    return out


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement de l'AOI et des batiments Overture")
    print(SEP)
    aoi_geom = load_union_geom(AOI_PATH)
    aoi_bounds = get_aoi_bounds(aoi_geom)
    buildings = load_overture_buildings(BUILDINGS_OVERTURE_PATH, BUILDINGS_OVERTURE_ID_FIELD, aoi_bounds)

    print(f"\n{SEP}\n  Chargement de la grille MMI\n{SEP}")
    mmi_cells = load_mmi_grid_for_bounds(MMI_SHP_PATH, MMI_VALUE_FIELD, aoi_bounds)
    mmi_buckets, mmi_bucket_size = build_bucket_index(mmi_cells)

    print(f"\n  Attribution de la categorie MMI par batiment...")
    bld_mmi_cat = {}
    bld_mmi_rank = {}
    for oid, g in buildings.items():
        val = mmi_for_point(g.Centroid(), mmi_cells, mmi_buckets, mmi_bucket_size)
        if val is None:
            continue
        cat, rank = mmi_category(val)
        bld_mmi_cat[oid] = cat
        bld_mmi_rank[oid] = rank

    # comptage[source][mmi_cat] = {'probably':n,'damaged':n,'destroyed':n,'total':n,'analyses':n}
    comptage = {}
    for source_name, cfg in DAMAGE_CONFIG.items():
        print(f"\n{SEP}\n  {source_name}\n{SEP}")
        comptage[source_name] = {cat: {'probably': 0, 'damaged': 0, 'destroyed': 0, 'total': 0, 'analyses': 0}
                                  for _, _, cat, _ in MMI_BINS}

        if cfg['kind'] == 'overture':
            raw_by_id = load_overture_source(cfg)
            for oid in buildings:
                cat = bld_mmi_cat.get(oid)
                if cat is None or oid not in raw_by_id:
                    continue
                raw = raw_by_id.get(oid)
                cls, prob, dmg, det = standardize(cfg, raw)
                if cls is None:
                    continue
                c = comptage[source_name][cat]
                c['analyses'] += 1
                c['probably'] += prob; c['damaged'] += dmg; c['destroyed'] += det
                c['total'] += (dmg + det)
        else:
            entities = (load_points_csv_source(cfg) if cfg['kind'] == 'points_csv' else load_points_source(cfg))
            print(f"  {len(entities)} entite(s) source")
            matched = match_points_to_buildings(entities, buildings)
            for oid, raw in matched.items():
                cat = bld_mmi_cat.get(oid)
                if cat is None:
                    continue
                cls, prob, dmg, det = standardize(cfg, raw)
                if cls is None:
                    continue
                c = comptage[source_name][cat]
                c['analyses'] += 1
                c['probably'] += prob; c['damaged'] += dmg; c['destroyed'] += det
                c['total'] += (dmg + det)

    # --- Fichier 1 : comptage brut ---
    rows1 = []
    for source_name in DAMAGE_CONFIG:
        for _, _, cat, rank in MMI_BINS:
            c = comptage[source_name][cat]
            rows1.append({
                'source': source_name, 'mmi_categorie': cat, 'mmi_rang': rank,
                'n_probablement_endommage': c['probably'], 'n_endommage': c['damaged'],
                'n_detruit': c['destroyed'], 'n_total': c['total'], 'n_batiments_analyses': c['analyses'],
            })
    os.makedirs(os.path.dirname(OUT_CSV_COMPTAGE), exist_ok=True)
    with open(OUT_CSV_COMPTAGE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows1[0].keys()))
        w.writeheader(); w.writerows(rows1)
    print(f"\nEcrit : {OUT_CSV_COMPTAGE}")

    # --- Fichier 2 : analyse de coherence ---
    print(f"\n{SEP}\n  Analyse de coherence (taux de dommage vs intensite MMI)\n{SEP}")
    rows2 = []
    for source_name in DAMAGE_CONFIG:
        ranks, fractions = [], []
        detail = {}
        for _, _, cat, rank in MMI_BINS:
            c = comptage[source_name][cat]
            frac = c['total'] / c['analyses'] if c['analyses'] > 0 else None
            detail[cat] = frac
            if frac is not None:
                ranks.append(rank)
                fractions.append(frac)
        if len(ranks) >= 3:
            corr = float(np.corrcoef(ranks, fractions)[0, 1])
        else:
            corr = None
        verdict = ("coherent (croissant avec MMI)" if (corr is not None and corr > 0.3) else
                   "incertain" if (corr is not None and corr > -0.3) else
                   "INCOHERENT (ne suit pas l'intensite)" if corr is not None else "donnees insuffisantes")
        row = {'source': source_name, 'correlation_rang_mmi_vs_taux': round(corr, 3) if corr is not None else None,
               'verdict': verdict}
        for _, _, cat, _ in MMI_BINS:
            row[f'taux_{cat}'] = round(detail[cat], 4) if detail[cat] is not None else None
        rows2.append(row)
        print(f"  {source_name:12s} : correlation={corr}  -> {verdict}")

    with open(OUT_CSV_COHERENCE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows2[0].keys()))
        w.writeheader(); w.writerows(rows2)
    print(f"\nEcrit : {OUT_CSV_COHERENCE}")


if __name__ == '__main__':
    main()
