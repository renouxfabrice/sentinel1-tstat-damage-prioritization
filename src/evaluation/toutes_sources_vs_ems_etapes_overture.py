# -*- coding: utf-8 -*-
"""Même comparaison par inclusion progressive, tous les produits étant au préalable reprojetés sur une base d'empreintes unique.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import numpy as np
from config import DONNEES

try:
    from osgeo import ogr, osr, gdal
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()
gdal.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v3.gpkg")
AOI_ZONE_FIELD = "area"
ZONES_A_ETUDIER = ['caraballeda', 'catia_la_mar', 'la_guaira']

OVERTURE_BUILDINGS_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg")
OVERTURE_ID_FIELD = "id"

EMS_GT_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture_v3_AOI.gpkg")
EMS_ID_FIELD = "id"
EMS_CLASS_FIELD = "cm_damage_gra"

T_TEST_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif")
BDPM_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\BDPM.tif")
BURST_MOSAIC_PATH_ASC = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst\mosaic_asc.tif")
BURST_MOSAIC_PATH_DESC = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst\mosaic_desc.tif")

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.15)]
BDPM_THRESHOLDS = [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)]
BURST_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.01, 0.03)]

# AOI vecteur de chaque source (pour la couverture/l'ordre des etapes)
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
    'ungsc':     os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\ungsc_aoi.gpkg")
}
SOURCE_AOI_RASTER_PATHS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif"),
    'bdpm': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\BDPM.tif"),
}

# Sources CATEGORIELLES — deja classifiees, pas de seuil a optimiser.
# 'kind': 'overture' (fichier deja aligne, lecture directe par
# overture_id) ou 'points' (jointure par recouvrement necessaire).
CATEGORICAL_SOURCES = {
    # TOUTES les sources ci-dessous utilisent leur fichier _on_overture.gpkg
    # OFFICIEL (dossier partage, schema uniforme overture_id/classe) —
    # SAUF uhsail et unep, qui n'ont AUCUNE version Overture officielle
    # confirmee dans ce projet (absentes du dossier partage) : elles
    # restent sur un appariement "meilleur recouvrement" fait a la volee,
    # PAS la meme methode que les autres — a interpreter avec prudence
    # dans une comparaison stricte "tout sur Overture".
    'chatmap': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\chatmap_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'disha': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\disha_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'id', 'class_field': 'cm_damaged',
        'damaged_values': ['TRUE', 'True', True], 'destroyed_values': [], 'excluded_values': [],
    },
    'fair': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\fair_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'id', 'class_field': 'cm_damage',
        'damaged_values': ['minor-damage', 'major-damage'], 'destroyed_values': ['destroyed'],
        'excluded_values': ['no-data (cloud)', 'no-data (no pre)'],
    },
    'impact': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\impact_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'microsoft': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\microsoft_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'id', 'class_field': 'cm_severity',
        'damaged_values': ['damaged'], 'destroyed_values': [], 'excluded_values': [],
    },
    'osu': {
        # OSU fournit deja son propre overture_id natif (pas besoin d'un
        'path': os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'label',
        'damaged_values': ['likely_damaged'], 'destroyed_values': [], 'excluded_values': ['not_assessed'],
    },
    'uhsail': {
        # ATTENTION — AUCUN fichier _on_overture.gpkg officiel confirme
        # pour cette source (absent du dossier partage). Reste sur un
        # appariement "meilleur recouvrement" different des autres —
        # PAS strictement comparable dans un tableau "tout sur Overture".
        'path': os.path.join(DONNEES, r"VENEZUELA\UH SAIL\Building damaged.gpkg"),
        'kind': 'points', 'class_field': 'grade',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'unep': {
        # MEME RESERVE que uhsail — aucune version Overture officielle
        # confirmee pour cette source.
        'path': os.path.join(DONNEES, r"VENEZUELA\UNEP\debris_buildings.gpkg"),
        'kind': 'points', 'class_field': None,
        'damaged_values': None, 'destroyed_values': [], 'excluded_values': [],
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
    'ungsc': {
        # NON CONFIRME dans ce projet — supposition basee sur la
        # convention uniforme du dossier partage.
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\ungsc_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'eos': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg"),
        'kind': 'overture', 'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
}
EOS_VALUE_FIELD = "raster_max"  # pour la version CONTINUE (fusion T-stat+EOS)

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\toutes_sources_vs_ems_etapes.csv")

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


def load_zones(path, zone_field, keep_names):
    ds = ogr.Open(path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    out = {}
    for feat in lyr:
        name = feat.GetField(zone_field)
        if name not in keep_names:
            continue
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        out[name] = g2
    ds = None
    return out


def load_union_geom(path):
    if path is None or not os.path.exists(path):
        return None
    ds = ogr.Open(path)
    if ds is None:
        return None
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


def raster_bbox_polygon(path):
    if path is None or not os.path.exists(path):
        return None
    ds = gdal.Open(path)
    if ds is None:
        return None
    gt = ds.GetGeoTransform()
    prj = ds.GetProjection()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    ds = None
    corners = [(gt[0], gt[3]), (gt[0] + nx * gt[1], gt[3]),
               (gt[0] + nx * gt[1], gt[3] + ny * gt[5]), (gt[0], gt[3] + ny * gt[5])]
    srs = osr.SpatialReference(); srs.ImportFromWkt(prj)
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


def get_aoi_bounds(geom):
    env = geom.GetEnvelope()
    return env[0], env[2], env[1], env[3]


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
    return out


def load_field_by_id(path, id_field, value_field, aoi_bounds):
    if not os.path.exists(path):
        return {}
    ds = ogr.Open(path)
    if ds is None:
        return {}
    lyr = ds.GetLayer()
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if id_field not in field_names or value_field not in field_names:
        print(f"    ERREUR champ manquant dans {path} — champs: {field_names}")
        ds = None
        return {}
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for feat in lyr:
        out[feat.GetField(id_field)] = feat.GetField(value_field)
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


def classify_raw(cfg, raw):
    destroyed_vals = cfg.get('destroyed_values') or []
    damaged_vals = cfg.get('damaged_values')
    excluded_vals = cfg.get('excluded_values') or []
    if raw in excluded_vals:
        return None
    if cfg.get('class_field') is None:
        return 1  # source binaire — toute entite presente = endommage
    if raw in destroyed_vals:
        return 1
    if damaged_vals is None or raw in damaged_vals:
        return 1
    return 0


def compute_max_per_building(raster_path, geoms):
    if raster_path is None or not os.path.exists(raster_path):
        return [None] * len(geoms)
    ds = gdal.Open(raster_path)
    gt = ds.GetGeoTransform()
    prj = ds.GetProjection()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    band = ds.GetRasterBand(1)
    nd = band.GetNoDataValue()
    tr_wgs84_to_raster = None
    if prj:
        raster_srs = osr.SpatialReference(); raster_srs.ImportFromWkt(prj)
        if not raster_srs.IsSame(WGS84):
            raster_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            tr_wgs84_to_raster = osr.CoordinateTransformation(WGS84, raster_srs)
    out = []
    for geom in geoms:
        env = geom.GetEnvelope()
        if tr_wgs84_to_raster is not None:
            p1 = tr_wgs84_to_raster.TransformPoint(env[0], env[2])
            p2 = tr_wgs84_to_raster.TransformPoint(env[1], env[3])
            rxmin, rxmax = min(p1[0], p2[0]), max(p1[0], p2[0])
            rymin, rymax = min(p1[1], p2[1]), max(p1[1], p2[1])
        else:
            rxmin, rxmax, rymin, rymax = env[0], env[1], env[2], env[3]
        px0 = max(0, int((rxmin - gt[0]) / gt[1]))
        px1 = min(nx - 1, int((rxmax - gt[0]) / gt[1]))
        py0 = max(0, int((rymax - gt[3]) / gt[5]))
        py1 = min(ny - 1, int((rymin - gt[3]) / gt[5]))
        val = None
        if px0 <= px1 and py0 <= py1:
            sub = band.ReadAsArray(px0, py0, px1 - px0 + 1, py1 - py0 + 1)
            if sub is not None:
                sub = sub.astype(np.float64)
                if nd is not None:
                    sub[np.isclose(sub, nd)] = np.nan
                valid = sub[np.isfinite(sub)]
                if len(valid) > 0:
                    val = float(np.max(valid))
        out.append(val)
    ds = None
    return out


def compute_metrics_np(y_true, y_pred):
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else np.nan
    recall = tp / (tp + fn) if (tp + fn) > 0 else np.nan
    po = (tp + tn) / n if n > 0 else np.nan
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
    return dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn, precision=precision, recall=recall, kappa=kappa)


def find_best_solo(y_true, vals, thresholds, direction):
    best = None
    for thr in thresholds:
        pred = ((vals >= thr) if direction == 'ge' else (vals <= thr)).astype(int)
        m = compute_metrics_np(y_true, pred)
        if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
            best = {'seuil_a': thr, 'seuil_b': None, **m}
    return best


def find_best_fusion(y_true, vals_a, thr_a, vals_b, thr_b, dir_b):
    best = None
    for ta in thr_a:
        for tb in thr_b:
            cond_b = (vals_b >= tb) if dir_b == 'ge' else (vals_b <= tb)
            pred = ((vals_a >= ta) & cond_b).astype(int)
            m = compute_metrics_np(y_true, pred)
            if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
                best = {'seuil_a': ta, 'seuil_b': tb, **m}
    return best


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"{SEP}\n  Chargement des zones et des AOI sources (couverture)\n{SEP}")
    zones = load_zones(AOI_PATH, AOI_ZONE_FIELD, ZONES_A_ETUDIER)
    all_source_names = list(SOURCE_AOI_VECTOR_PATHS.keys()) + list(SOURCE_AOI_RASTER_PATHS.keys())
    source_geoms = {}
    for name, path in SOURCE_AOI_VECTOR_PATHS.items():
        source_geoms[name] = load_union_geom(path) if path else None
    for name, path in SOURCE_AOI_RASTER_PATHS.items():
        source_geoms[name] = raster_bbox_polygon(path)

    union_zones = None
    for z in zones.values():
        union_zones = z if union_zones is None else union_zones.Union(z)
    aoi_bounds = get_aoi_bounds(union_zones)

    print(f"\n{SEP}\n  Chargement Overture / EMS / rasters continus (une fois)\n{SEP}")
    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)
    ems_gt = load_field_by_id(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)
    common_ids = list(set(overture.keys()) & set(ems_gt.keys()))
    print(f"  {len(common_ids)} batiment(s) en commun Overture+EMS")
    geoms_all = [overture[oid] for oid in common_ids]
    y_true_full = {oid: (1 if ems_gt[oid] in ('Possibly damaged', 'Damaged', 'Destroyed')
                         else (0 if ems_gt[oid] == 'not_reported' else None)) for oid in common_ids}

    t_vals_all = dict(zip(common_ids, compute_max_per_building(T_TEST_RASTER, geoms_all)))
    bdpm_vals_all = dict(zip(common_ids, compute_max_per_building(BDPM_RASTER, geoms_all)))
    asc_vals_all = dict(zip(common_ids, compute_max_per_building(BURST_MOSAIC_PATH_ASC, geoms_all)))
    desc_vals_all = dict(zip(common_ids, compute_max_per_building(BURST_MOSAIC_PATH_DESC, geoms_all)))
    burst_vals_all = {oid: (np.nanmean([asc_vals_all[oid], desc_vals_all[oid]])
                             if (asc_vals_all[oid] is not None or desc_vals_all[oid] is not None) else None)
                       for oid in common_ids}
    eos_raw_field = load_field_by_id(CATEGORICAL_SOURCES['eos']['path'],
                                       CATEGORICAL_SOURCES['eos']['id_field'], EOS_VALUE_FIELD, aoi_bounds)
    eos_continuous_all = {oid: eos_raw_field.get(oid) for oid in common_ids}

    print(f"\n{SEP}\n  Classification de chaque source CATEGORIELLE (une fois)\n{SEP}")
    binary_by_source = {}
    for src_name, cfg in CATEGORICAL_SOURCES.items():
        print(f"  {src_name} ...")
        if cfg['kind'] == 'overture':
            raw_by_id = load_field_by_id(cfg['path'], cfg['id_field'], cfg['class_field'], aoi_bounds)
            binary_by_source[src_name] = {oid: classify_raw(cfg, raw_by_id[oid]) for oid in raw_by_id}
        else:
            entities = (load_points_csv_source(cfg) if cfg['kind'] == 'points_csv' else load_points_source(cfg))
            matched = match_points_to_buildings(entities, dict(zip(common_ids, geoms_all)))
            binary_by_source[src_name] = {oid: classify_raw(cfg, raw) for oid, raw in matched.items()}

    oid_to_geom = dict(zip(common_ids, geoms_all))
    rows = []

    for zone_name, zone_geom in zones.items():
        print(f"\n{SEP}\n  Zone : {zone_name}\n{SEP}")
        pcts = {}
        for s in all_source_names:
            g = source_geoms.get(s)
            if g is None:
                continue
            inter = g.Intersection(zone_geom) if g.Intersects(zone_geom) else None
            pct = 100 * area_km2(inter) / area_km2(zone_geom) if inter is not None and not inter.IsEmpty() else 0.0
            pcts[s] = pct
        ordered_sources = sorted(pcts.keys(), key=lambda s: -pcts[s])
        print(f"  Ordre de couverture decroissante : {[(s, round(pcts[s],1)) for s in ordered_sources]}")

        included = []
        for step_i, src in enumerate(ordered_sources, start=1):
            included.append(src)
            common_geom = zone_geom
            for s in included:
                g = source_geoms.get(s)
                if g is None:
                    continue
                common_geom = common_geom.Intersection(g) if common_geom.Intersects(g) else None
                if common_geom is None or common_geom.IsEmpty():
                    break
            if common_geom is None or common_geom.IsEmpty():
                print(f"  Etape {step_i} ({src}) : intersection VIDE — arret pour cette zone")
                break

            ref_id = f"{zone_name}_etape{step_i}_+{src}"
            common_area = area_km2(common_geom)
            ids_in_common = [oid for oid, g in oid_to_geom.items() if common_geom.Contains(g.Centroid())]
            valid_ids = [oid for oid in ids_in_common if y_true_full[oid] is not None]
            y_true = np.array([y_true_full[oid] for oid in valid_ids])
            n_batiments = len(valid_ids)
            n_pos = int(y_true.sum()) if len(y_true) else 0
            taux_dommage = n_pos / n_batiments if n_batiments > 0 else None
            print(f"\n  -- Etape {step_i} : +{src} — aire={common_area:.2f}km2  n={n_batiments}  positifs={n_pos} --")

            base_row = {'reference_etape': ref_id, 'zone': zone_name, 'etape': step_i,
                        'source_ajoutee': src, 'aire_commune_km2': round(common_area, 3),
                        'n_batiments_evalues': n_batiments, 'n_positifs_ems': n_pos,
                        'taux_dommage': round(taux_dommage, 4) if taux_dommage is not None else None}
            for s in all_source_names:
                base_row[f'inclus_{s}'] = (s in included)

            if n_batiments < 20 or n_pos == 0:
                print("     Trop peu de donnees — sources ignorees pour cette etape")
                continue

            # --- Sources categorielles : classification fixe, pas de seuil ---
            for src_name in CATEGORICAL_SOURCES:
                bys = binary_by_source[src_name]
                ids_avail = [oid for oid in valid_ids if oid in bys and bys[oid] is not None]
                if len(ids_avail) < 20:
                    continue
                yt = np.array([y_true_full[oid] for oid in ids_avail])
                yp = np.array([bys[oid] for oid in ids_avail])
                if yt.sum() == 0:
                    continue
                m = compute_metrics_np(yt, yp)
                rows.append({**base_row, 'methode': src_name, 'seuil_a': None, 'seuil_b': None, **m})
                print(f"     {src_name:12s} : n={m['n']}  kappa={m['kappa']:.3f}  tp={m['tp']}  fp={m['fp']}  "
                      f"rappel={m['recall']:.3f}")

            # --- Sources continues : seuil re-optimise sur cette empreinte ---
            tv = np.array([t_vals_all[oid] if t_vals_all[oid] is not None else np.nan for oid in valid_ids])
            bv = np.array([bdpm_vals_all[oid] if bdpm_vals_all[oid] is not None else np.nan for oid in valid_ids])
            bu = np.array([burst_vals_all[oid] if burst_vals_all[oid] is not None else np.nan for oid in valid_ids])
            ev = np.array([eos_continuous_all[oid] if eos_continuous_all[oid] is not None else np.nan for oid in valid_ids])

            valid_t = np.isfinite(tv)
            if valid_t.sum() >= 20 and y_true[valid_t].sum() > 0:
                best = find_best_solo(y_true[valid_t], tv[valid_t], T_TEST_THRESHOLDS, 'ge')
                if best:
                    rows.append({**base_row, 'methode': 't_test_seul', **best})
                    print(f"     t_test_seul  : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

            valid_b = np.isfinite(bv)
            if valid_b.sum() >= 20 and y_true[valid_b].sum() > 0:
                best = find_best_solo(y_true[valid_b], bv[valid_b], BDPM_THRESHOLDS, 'ge')
                if best:
                    rows.append({**base_row, 'methode': 'bdpm_seul', **best})
                    print(f"     bdpm_seul    : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

            valid_tb = np.isfinite(tv) & np.isfinite(bu)
            if valid_tb.sum() >= 20 and y_true[valid_tb].sum() > 0:
                best = find_best_fusion(y_true[valid_tb], tv[valid_tb], T_TEST_THRESHOLDS,
                                         bu[valid_tb], BURST_THRESHOLDS, 'le')
                if best:
                    rows.append({**base_row, 'methode': 'fusion_tstat_coevent', **best})
                    print(f"     fusion+coevent: kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

            valid_te = np.isfinite(tv) & np.isfinite(ev)
            if valid_te.sum() >= 20 and y_true[valid_te].sum() > 0:
                eos_thr = [round(x, 3) for x in np.linspace(np.nanmin(ev[valid_te]), np.nanmax(ev[valid_te]), 30)]
                best = find_best_fusion(y_true[valid_te], tv[valid_te], T_TEST_THRESHOLDS,
                                         ev[valid_te], eos_thr, 'ge')
                if best:
                    rows.append({**base_row, 'methode': 'fusion_tstat_eos', **best})
                    print(f"     fusion+eos    : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = (['reference_etape', 'zone', 'etape', 'source_ajoutee', 'aire_commune_km2',
                   'n_batiments_evalues', 'n_positifs_ems', 'taux_dommage']
                  + [f'inclus_{s}' for s in all_source_names]
                  + ['methode', 'seuil_a', 'seuil_b', 'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa'])
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
