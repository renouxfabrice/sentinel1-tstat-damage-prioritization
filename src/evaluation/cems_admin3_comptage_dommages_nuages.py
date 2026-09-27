# -*- coding: utf-8 -*-
"""Comptage des bâtiments endommagés et détruits par unité administrative de niveau 3, en séparant les zones où la couverture nuageuse a empêché l'analyse optique, afin de mesurer l'apport propre des produits radar.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import numpy as np
from config import DONNEES

try:
    from osgeo import ogr, osr
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()

# =============================================================================
# CONFIGURATION — AOI / ADMIN3 / NUAGES
# =============================================================================

EMS_AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v3.gpkg")
EMS_AOI_AREA_FIELD = "area"

ADMIN3_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_admin_boundaries.geojson\ven_admin3.geojson")
ADMIN3_ID_FIELD = 'adm3_pcode'

NOT_ANALYSED_PATHS = [
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI02_GRA_MONIT01_v2\EMSR884_AOI02_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI06_GRA_MONIT01_v2\EMSR884_AOI06_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI08_GRA_MONIT01_v2\EMSR884_AOI08_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI12_GRA_MONIT01_v3\EMSR884_AOI12_GRA_MONIT01_notAnalysedA_v1.shp"),
]

# =============================================================================
# CONFIGURATION — 9 sources vectorielles natives (COPIE, pas import)
# =============================================================================

DAMAGE_CONFIG = {
    'chatmap': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_venezuela_points.geojson"),
        'class_field': 'damaged',
        'damaged_values': ['significant', 'minimal'],
        'destroyed_values': ['complete'],
    },
    'disha': {
        'kind': 'points_csv',
        'path': os.path.join(DONNEES, r"VENEZUELA\DISHA\Caracas\nwcaracas_final_inference_result.csv"),
        'class_field': 'damaged',
        'damaged_values': ['TRUE', 'True', True],
        'destroyed_values': [],
    },
    'ems': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP.gpkg"),
        'class_field': 'damage_gra',
        'damaged_values': ['Possibly damaged', 'Damaged'],
        'destroyed_values': ['Destroyed'],
    },
    'fair': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\Fair\ALL\damage_polygones_fair.gpkg"),
        'class_field': 'damage',
        'damaged_values': ['minor-damage', 'major-damage'],
        'destroyed_values': ['destroyed'],
        'excluded_values': ['no-data (cloud)', 'no-data (no pre)'],
    },
    'impact': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\IMPACT Initiatives S1 DPM\impact_ven_earthquake_sentinel1_damaged_20260625_v3.geojson"),
        'class_field': None,
        'damaged_values': None,
        'destroyed_values': [],
    },
    'microsoft': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\Microsoft AI for Good Lab\from_huggingFace\venezuela_microsoft_damage_points.geojson"),
        'class_field': None,
        'damaged_values': None,
        'destroyed_values': [],
    },
    'osu': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"),
        'class_field': 'label',
        'damaged_values': ['likely_damaged'],
        'destroyed_values': [],  # OSU ne distingue pas 'detruit' — damage_confidence
        # est un niveau de CONFIANCE sur 'likely_damaged', pas une gravite distincte
        # (verifie : below_floor==not_damaged, possible+probable+high_confidence==likely_damaged,
        # exactement — pas d'echelle de gravite independante)
        'excluded_values': ['not_assessed'],
    },
    'uhsail': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\UH SAIL\Building damaged.gpkg"),
        'class_field': 'grade',
        'damaged_values': ['damaged'],
        'destroyed_values': ['destroyed'],
    },
    'unep': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\UNEP\debris_buildings.gpkg"),
        'class_field': None,
        'damaged_values': None,
        'destroyed_values': [],
    },
}

# =============================================================================
# CONFIGURATION — 6 sources raster projetees sur Overture (deja calculees)
# =============================================================================

RASTER_METHODS_ON_OVERTURE = {
    'eos':     os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg"),
    'nasa_s1': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s1_on_overture.gpkg"),
    'nasa_s2': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s2_on_overture.gpkg"),
    'ungsc':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\ungsc_on_overture.gpkg"),
    't_test':  os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\t_test_on_overture.gpkg"),
    'bdpm':    os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\bdpm_on_overture.gpkg"),
}
RASTER_METHOD_CLASS_FIELD = 'classe'
RASTER_METHOD_DAMAGED_VALUES = ['damaged']
RASTER_METHOD_DESTROYED_VALUES = ['destroyed']

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\CEMS_admin3_comptage_dommages_nuages.csv")

# Bâtiments Overture — pour "Total buildings" et "Analysed". UTILISE LA
# VERSION INDEXEE (ogr2ogr -spat_index yes) si tu l'as deja creee — sans
# index spatial, ce fichier national (3.6M entites) rend chaque comptage
# tres lent (deja constate plus tot dans ce projet).
BUILDINGS_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_overture_ven_buildings_overture_gpkg\buildings.gpkg")
BUILDINGS_OVERTURE_FIELD_OVERRIDE = None  # None si le fichier indexe a un schema propre (probable)

# =============================================================================
# CONFIGURATION — AOI de chaque source, pour calculer la surface de
# recouvrement avec la portion cloud/non-cloud de chaque admin3.
#
# 13 sources : fichier AOI vectoriel deja produit (Source_AOI/original/,
# script 01_build_source_aoi.py).
# t_test/bdpm : PAS de fichier AOI persistant — bbox calculee ICI
# coincide avec celle d'EMS, meme si c'est probable).
# =============================================================================

SOURCE_AOI_VECTOR_PATHS = {
    'chatmap':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\chatmap_aoi.gpkg"),
    'disha':     os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\disha_aoi.gpkg"),
    'ems':       os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\ems_aoi.gpkg"),
    'fair':      os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\fair_aoi.gpkg"),
    'impact':    os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\impact_aoi.gpkg"),
    'microsoft': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\microsoft_aoi.gpkg"),
    'osu':       os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\osu_aoi.gpkg"),
    'uhsail':    os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\uhsail_aoi.gpkg"),
    'unep':      os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\unep_aoi.gpkg"),
    'eos':       os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\eos_aoi.gpkg"),
    'nasa_s1':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\nasa_s1_aoi.gpkg"),
    'nasa_s2':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\nasa_s2_aoi.gpkg"),
    'ungsc':     os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\ungsc_aoi.gpkg"),
}

# t_test/bdpm — bbox calculee depuis le raster d'origine (pas de fichier
# AOI persistant pour ces deux methodes)
SOURCE_AOI_RASTER_PATHS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\ALL_AOI_HOTOSM\T_stat_all_zones.tif"),
    'bdpm': os.path.join(DONNEES, r"VENEZUELA\MOI\BDPM\ALL_AOI_HOTOSM\coh_diff_fused.tif"),
}

SEP = "=" * 70

# =============================================================================
# HELPERS
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


def load_multi_union(paths):
    all_geoms = []
    for p in paths:
        if not os.path.exists(p):
            print(f"  Attention: fichier introuvable — {p}")
            continue
        g = load_union_geom(p)
        if g is not None:
            all_geoms.append(g)
    if not all_geoms:
        return None
    union = all_geoms[0]
    for g in all_geoms[1:]:
        union = union.Union(g)
    return union


def load_aoi_features_with_area(path, area_field):
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir l'AOI : {path}")
    lyr = ds.GetLayer()
    defn = lyr.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    if area_field not in field_names:
        sys.exit(f"Erreur: champ '{area_field}' introuvable dans {path}.\n"
                  f"Champs disponibles: {field_names}")
    tr = get_transform_to_wgs84(lyr)
    out = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        out.append((g2, feat.GetField(area_field)))
    ds = None
    return out


def aoi_zones_for_geom(aoi_features, geom):
    labels = []
    for g, label in aoi_features:
        if g.Intersects(geom):
            labels.append(label)
    return sorted(set(labels), key=lambda x: str(x))


def load_admin3_in_aoi(admin3_path, aoi_geom):
    ds = ogr.Open(admin3_path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {admin3_path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                   for i in range(lyr.GetLayerDefn().GetFieldCount())]
    env = aoi_geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])
    out = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.Intersects(aoi_geom):
            continue
        attrs = {fn: feat.GetField(fn) for fn in field_names}
        out.append({'geom': g2, 'attrs': attrs})
    ds = None
    print(f"  {len(out)} admin3 dans l'AOI (entiers, non decoupes)")
    return out


def load_source_aoi(source_name):
    """Charge l'AOI d'une source — fichier vectoriel deja produit, ou
    bbox calculee depuis son raster d'origine (t_test/bdpm)."""
    if source_name in SOURCE_AOI_VECTOR_PATHS:
        path = SOURCE_AOI_VECTOR_PATHS[source_name]
        if not os.path.exists(path):
            print(f"  Attention: AOI introuvable pour '{source_name}' — {path}")
            return None
        return load_union_geom(path)
    elif source_name in SOURCE_AOI_RASTER_PATHS:
        path = SOURCE_AOI_RASTER_PATHS[source_name]
        if not os.path.exists(path):
            print(f"  Attention: raster introuvable pour '{source_name}' — {path}")
            return None
        return raster_bbox_polygon(path)
    return None


def raster_bbox_polygon(path):
    """Boite englobante simple depuis l'en-tete du raster (aucun pixel
    lu) — meme principe que 01_build_source_aoi.py."""
    from osgeo import gdal
    gdal.UseExceptions()
    ds = gdal.Open(path)
    if ds is None:
        return None
    gt = ds.GetGeoTransform()
    prj = ds.GetProjection()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    ds = None

    corners = [
        (gt[0], gt[3]),
        (gt[0] + nx * gt[1], gt[3]),
        (gt[0] + nx * gt[1], gt[3] + ny * gt[5]),
        (gt[0], gt[3] + ny * gt[5]),
    ]
    srs = osr.SpatialReference()
    srs.ImportFromWkt(prj)
    tr = None
    if not srs.IsSame(WGS84):
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        tr = osr.CoordinateTransformation(srs, WGS84)

    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in corners:
        if tr is not None:
            x, y, _ = tr.TransformPoint(x, y)
        ring.AddPoint(x, y)
    ring.CloseRings()
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


def safe_intersection(geom_a, geom_b):
    try:
        if not geom_a.Intersects(geom_b):
            return None
        inter = geom_a.Intersection(geom_b)
        if inter is None or inter.IsEmpty():
            return None
        return inter
    except Exception:
        return None


def safe_difference(geom_a, geom_b):
    try:
        diff = geom_a.Difference(geom_b)
        if diff is None or diff.IsEmpty():
            return None
        return diff
    except Exception:
        return geom_a


def count_damage_points(cfg, geom):
    path = cfg.get('path')
    if not path or path == '****' or not os.path.exists(path):
        return None, None
    ds = ogr.Open(path)
    if ds is None:
        return None, None
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    env = geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])
    class_field = cfg.get('class_field')
    damaged_vals = cfg.get('damaged_values')
    destroyed_vals = cfg.get('destroyed_values') or []
    excluded_vals = cfg.get('excluded_values') or []
    n_damaged, n_destroyed = 0, 0
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        c = g2.Centroid()
        if not geom.Contains(c):
            continue
        if class_field is None:
            n_damaged += 1
            continue
        raw = feat.GetField(class_field)
        if raw in excluded_vals:
            continue
        if raw in destroyed_vals:
            n_destroyed += 1
        elif damaged_vals is None or raw in damaged_vals:
            n_damaged += 1
    ds = None
    return n_damaged, n_destroyed


def count_damage_csv(cfg, geom):
    path = cfg.get('path')
    if not path or path == '****' or not os.path.exists(path):
        return None, None
    class_field = cfg.get('class_field')
    damaged_vals = cfg.get('damaged_values')
    env = geom.GetEnvelope()
    n_damaged, n_destroyed = 0, 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lon = float(row.get('lon') or row.get('longitude') or row.get('x'))
                lat = float(row.get('lat') or row.get('latitude') or row.get('y'))
            except (TypeError, ValueError):
                continue
            if not (env[0] <= lon <= env[1] and env[2] <= lat <= env[3]):
                continue
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint(lon, lat)
            if not geom.Contains(pt):
                continue
            raw = row.get(class_field)
            if damaged_vals is not None and raw in [str(v) for v in damaged_vals]:
                n_damaged += 1
    return n_damaged, n_destroyed


def count_damage_for_source(cfg, geom):
    kind = cfg.get('kind')
    if kind == 'points':
        return count_damage_points(cfg, geom)
    elif kind == 'points_csv':
        return count_damage_csv(cfg, geom)
    else:
        return None, None


def count_raster_method_on_overture(path, geom):
    if not os.path.exists(path):
        return None, None
    ds = ogr.Open(path)
    if ds is None:
        return None, None
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    env = geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])
    n_damaged, n_destroyed = 0, 0
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        c = g2.Centroid()
        if not geom.Contains(c):
            continue
        raw = feat.GetField(RASTER_METHOD_CLASS_FIELD)
        if raw in RASTER_METHOD_DESTROYED_VALUES:
            n_destroyed += 1
        elif raw in RASTER_METHOD_DAMAGED_VALUES:
            n_damaged += 1
    ds = None
    return n_damaged, n_destroyed


def count_buildings_in_geom(buildings_path, geom, field_override=None):
    """Compte les batiments Overture dont le centroide tombe dans geom —
    pour 'Total buildings' et 'Analysed' (meme methodologie que la
    reference : batiments DANS l'unite, ou DANS l'AOI de la source)."""
    if geom is None:
        return 0
    ds = ogr.Open(buildings_path)
    if ds is None:
        return None
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    env = geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])
    n = 0
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        c = g2.Centroid()
        if geom.Contains(c):
            n += 1
    ds = None
    return n


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement de l'AOI EMS complete")
    print(SEP)
    ems_aoi_geom = load_union_geom(EMS_AOI_PATH)
    if ems_aoi_geom is None:
        sys.exit(f"AOI vide ou illisible : {EMS_AOI_PATH}")
    aoi_features = load_aoi_features_with_area(EMS_AOI_PATH, EMS_AOI_AREA_FIELD)

    print(f"\n{SEP}")
    print("  Chargement des zones NON ANALYSEES (couverture nuageuse)")
    print(SEP)
    cloud_geom = load_multi_union(NOT_ANALYSED_PATHS)
    if cloud_geom is None:
        print("  Attention: aucune zone nuageuse chargee — tout sera compte 'non-cloud'")

    print(f"\n{SEP}")
    print("  Admin3 dans l'AOI EMS")
    print(SEP)
    admin3_list = load_admin3_in_aoi(ADMIN3_PATH, ems_aoi_geom)
    if not admin3_list:
        sys.exit("Aucun admin3 trouve dans cette AOI.")

    source_names = list(DAMAGE_CONFIG.keys()) + list(RASTER_METHODS_ON_OVERTURE.keys())
    print(f"\n  {len(source_names)} source(s) traitee(s) : {source_names}")

    print(f"\n{SEP}")
    print("  Prechargement des AOI par source (une seule fois, pas par admin3)")
    print(SEP)
    source_aois = {}
    for source_name in source_names:
        g = load_source_aoi(source_name)
        source_aois[source_name] = g
        status = "OK" if g is not None else "ECHEC"
        print(f"  {source_name:12s} : {status}")

    rows = []
    for i, unit in enumerate(admin3_list):
        g = unit['geom']
        admin3_id = unit['attrs'].get(ADMIN3_ID_FIELD, i)
        aoi_zones = aoi_zones_for_geom(aoi_features, g)
        aoi_zone_str = '; '.join(str(z) for z in aoi_zones) if aoi_zones else None
        admin3_area_km2 = area_km2(g)

        within_ems = safe_intersection(g, ems_aoi_geom)
        if within_ems is None:
            continue

        if cloud_geom is not None:
            cloud_portion = safe_intersection(within_ems, cloud_geom)
            non_cloud_portion = safe_difference(within_ems, cloud_geom)
        else:
            cloud_portion = None
            non_cloud_portion = within_ems

        cloud_km2 = area_km2(cloud_portion) if cloud_portion is not None else 0.0
        cloud_pct_admin3 = 100 * cloud_km2 / admin3_area_km2 if admin3_area_km2 > 0 else None

        # "Total buildings" — tous les batiments Overture DANS la zone,
        # peu importe la source (calcule une fois, pas par source).
        total_buildings_non_cloud = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, non_cloud_portion, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
        total_buildings_cloud = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, cloud_portion, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
        total_buildings_by_zone = {'non_cloud': total_buildings_non_cloud, 'cloud': total_buildings_cloud}

        print(f"\n{SEP}")
        pct_str = f"{cloud_pct_admin3:.1f}%" if cloud_pct_admin3 is not None else "N/A"
        print(f"  [{i+1}/{len(admin3_list)}] {admin3_id} (zones={aoi_zones}) — "
              f"aire={admin3_area_km2:.1f}km2  cloud={cloud_km2:.1f}km2 ({pct_str})  "
              f"total_batiments: non_cloud={total_buildings_non_cloud} cloud={total_buildings_cloud}")
        print(SEP)

        for source_name in source_names:
            for zone_type, zone_geom in (('non_cloud', non_cloud_portion), ('cloud', cloud_portion)):
                if zone_geom is None:
                    n_damaged, n_destroyed = None, None
                elif source_name in DAMAGE_CONFIG:
                    n_damaged, n_destroyed = count_damage_for_source(DAMAGE_CONFIG[source_name], zone_geom)
                else:
                    n_damaged, n_destroyed = count_raster_method_on_overture(
                        RASTER_METHODS_ON_OVERTURE[source_name], zone_geom)
                n_total = ((n_damaged or 0) + (n_destroyed or 0)
                           if (n_damaged is not None or n_destroyed is not None) else None)

                # Surface de l'AOI de CETTE source qui recoupe CETTE
                # sous-zone (cloud ou non-cloud) de l'admin3 — permet de
                # distinguer "0 dommage car pas de dommage" de "0 dommage
                # car cette source ne couvre pas cette zone du tout".
                source_aoi_geom = source_aois.get(source_name)
                if source_aoi_geom is not None and zone_geom is not None:
                    inter = safe_intersection(source_aoi_geom, zone_geom)
                    source_aoi_area_km2 = area_km2(inter) if inter is not None else 0.0
                    # "Analysed" — batiments Overture DANS l'AOI de CETTE
                    # source ET dans cette zone (meme methodologie que la
                    # reference fournie par l'utilisateur).
                    n_analysed = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, inter, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
                else:
                    source_aoi_area_km2 = None
                    n_analysed = 0

                total_buildings_zone = total_buildings_by_zone.get(zone_type) or 0
                coverage = (n_analysed / total_buildings_zone) if total_buildings_zone > 0 and n_analysed is not None else None
                damage_fraction = (n_total / n_analysed) if (n_analysed and n_total is not None) else None

                rows.append({
                    'admin3_id': admin3_id, 'aoi_zone': aoi_zone_str,
                    **unit['attrs'],
                    'admin3_area_km2': round(admin3_area_km2, 2),
                    'cloud_area_km2': round(cloud_km2, 2),
                    'cloud_pct_admin3': round(cloud_pct_admin3, 1) if cloud_pct_admin3 is not None else None,
                    'source': source_name, 'zone_type': zone_type,
                    'source_aoi_area_km2': round(source_aoi_area_km2, 2) if source_aoi_area_km2 is not None else None,
                    'total_buildings': total_buildings_zone,
                    'analysed': n_analysed,
                    'coverage': round(coverage, 4) if coverage is not None else None,
                    'n_endommages': n_damaged, 'n_detruits': n_destroyed, 'n_total': n_total,
                    'damage_fraction': round(damage_fraction, 4) if damage_fraction is not None else None,
                })
            print(f"    {source_name:12s} — non_cloud: dmg={rows[-2]['n_endommages']} "
                  f"detr={rows[-2]['n_detruits']} | cloud: dmg={rows[-1]['n_endommages']} "
                  f"detr={rows[-1]['n_detruits']}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
