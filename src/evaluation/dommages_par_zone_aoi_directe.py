# -*- coding: utf-8 -*-
"""Comptage des dommages par zone d'analyse par jointure spatiale directe, sans passer par les unités administratives.

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

BUILDINGS_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg")
BUILDINGS_OVERTURE_FIELD_OVERRIDE = None

DAMAGE_CONFIG = {
    'microsoft': {
        'path': os.path.join(DONNEES, r"VENEZUELA\Microsoft AI for Good Lab\from_huggingFace\venezuela_microsoft_damage_points.geojson"),
        'kind': 'points', 'class_field': 'severity',
        'damaged_values': ['damaged'], 'destroyed_values': [], 'excluded_values': [],
    },
    'impact': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\impact_on_overture.gpkg"),
        'kind': 'points', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'osu': {
        'path': os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"),
        'kind': 'points', 'class_field': 'label',
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
        'damaged_values': ['Possibly damaged', 'Damaged'], 'destroyed_values': ['Destroyed'],
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
        'kind': 'points', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'nasa_s2': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s2_on_overture.gpkg"),
        'kind': 'points', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    'eos': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg"),
        'kind': 'points', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'], 'excluded_values': [],
    },
    't_test': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\t_test_on_overture.gpkg"),
        'kind': 'points', 'class_field': 'classe',
        'damaged_values': ['Affected'], 'destroyed_values': [], 'excluded_values': [],
    },
    'bdpm': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\bdpm_on_overture.gpkg"),
        'kind': 'points', 'class_field': 'classe',
        'damaged_values': ['Affected'], 'destroyed_values': [], 'excluded_values': [],
    },
}

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
}
SOURCE_AOI_RASTER_PATHS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif"),
    'bdpm': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\BDPM.tif"),
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\dommages_par_zone_aoi_directe.csv")

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


def load_aoi_zones(path, zone_field):
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir l'AOI : {path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    zones = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        zones.append((feat.GetField(zone_field), g2))
    ds = None
    print(f"AOI chargee : {len(zones)} zone(s) — {[n for n, _ in zones]}")
    return zones


def find_zone(pt, aoi_zones):
    for name, geom in aoi_zones:
        if geom.Contains(pt):
            return name
    return None


def get_aoi_bounds(aoi_zones):
    xmin = ymin = xmax = ymax = None
    for _, g in aoi_zones:
        env = g.GetEnvelope()
        xmin = env[0] if xmin is None else min(xmin, env[0])
        xmax = env[1] if xmax is None else max(xmax, env[1])
        ymin = env[2] if ymin is None else min(ymin, env[2])
        ymax = env[3] if ymax is None else max(ymax, env[3])
    return (xmin, ymin, xmax, ymax)


def raster_bbox_polygon(path):
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


def load_source_aoi(source_name):
    if source_name in SOURCE_AOI_VECTOR_PATHS:
        path = SOURCE_AOI_VECTOR_PATHS[source_name]
        if not os.path.exists(path):
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
    elif source_name in SOURCE_AOI_RASTER_PATHS:
        path = SOURCE_AOI_RASTER_PATHS[source_name]
        if not os.path.exists(path):
            return None
        return raster_bbox_polygon(path)
    return None


def classify_raw(cfg, raw):
    class_field = cfg.get('class_field')
    damaged_vals = cfg.get('damaged_values')
    destroyed_vals = cfg.get('destroyed_values') or []
    excluded_vals = cfg.get('excluded_values') or []
    if class_field is None:
        return 'damaged'
    if raw in excluded_vals:
        return None
    if raw in destroyed_vals:
        return 'destroyed'
    if damaged_vals is None or raw in damaged_vals:
        return 'damaged'
    return 'not_damaged'


def count_buildings_per_zone(buildings_path, aoi_zones, field_override=None):
    ds = ogr.Open(buildings_path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {buildings_path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    bounds = get_aoi_bounds(aoi_zones)
    lyr.SetSpatialFilterRect(*bounds)
    counts = {}
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        c = g2.Centroid()
        zone = find_zone(c, aoi_zones)
        if zone is None:
            continue
        counts[zone] = counts.get(zone, 0) + 1
    ds = None
    return counts


def load_and_classify_source(cfg, aoi_zones):
    path = cfg['path']
    if not os.path.exists(path):
        print(f"  Attention: fichier introuvable — {path}")
        return {}

    counts = {}
    if cfg['kind'] == 'points_csv':
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    lon = float(row.get('lon') or row.get('longitude') or row.get('x'))
                    lat = float(row.get('lat') or row.get('latitude') or row.get('y'))
                except (TypeError, ValueError):
                    continue
                pt = ogr.Geometry(ogr.wkbPoint)
                pt.AddPoint(lon, lat)
                zone = find_zone(pt, aoi_zones)
                if zone is None:
                    continue
                raw = row.get(cfg['class_field'])
                cls = classify_raw(cfg, raw)
                if cls is None:
                    continue
                counts.setdefault(zone, {'damaged': 0, 'destroyed': 0})
                if cls in ('damaged', 'destroyed'):
                    counts[zone][cls] += 1
    else:
        ds = ogr.Open(path)
        if ds is None:
            print(f"  Attention: impossible d'ouvrir — {path}")
            return {}
        lyr = ds.GetLayer()
        tr = get_transform_to_wgs84(lyr)
        field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                       for i in range(lyr.GetLayerDefn().GetFieldCount())]
        class_field = cfg['class_field']
        if class_field is not None and class_field not in field_names:
            print(f"  Attention: champ '{class_field}' introuvable — champs: {field_names}")
            ds = None
            return {}
        for feat in lyr:
            g = feat.GetGeometryRef()
            if g is None:
                continue
            g2 = g.Clone()
            if tr is not None:
                g2.Transform(tr)
            gt = g2.GetGeometryType()
            pt = g2 if gt in (ogr.wkbPoint, ogr.wkbPoint25D) else g2.Centroid()
            zone = find_zone(pt, aoi_zones)
            if zone is None:
                continue
            raw = feat.GetField(class_field) if class_field else None
            cls = classify_raw(cfg, raw)
            if cls is None:
                continue
            counts.setdefault(zone, {'damaged': 0, 'destroyed': 0})
            if cls in ('damaged', 'destroyed'):
                counts[zone][cls] += 1
        ds = None
    return counts


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement de l'AOI")
    print(SEP)
    aoi_zones = load_aoi_zones(AOI_PATH, AOI_ZONE_FIELD)
    zone_names = sorted(set(n for n, _ in aoi_zones))

    print(f"\n{SEP}")
    print("  Comptage des batiments Overture par zone")
    print(SEP)
    total_buildings_by_zone = count_buildings_per_zone(BUILDINGS_OVERTURE_PATH, aoi_zones, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
    for z in zone_names:
        print(f"  {z:15s} : {total_buildings_by_zone.get(z, 0):,} batiment(s)")

    print(f"\n{SEP}")
    print("  Prechargement des AOI par source")
    print(SEP)
    source_aois = {}
    for sn in DAMAGE_CONFIG.keys():
        g = load_source_aoi(sn)
        source_aois[sn] = g
        print(f"  {sn:12s} : {'OK' if g is not None else 'ECHEC/absent'}")

    rows = []
    for source_name, cfg in DAMAGE_CONFIG.items():
        print(f"\n{SEP}\n  {source_name}\n{SEP}")
        counts = load_and_classify_source(cfg, aoi_zones)

        source_aoi_geom = source_aois.get(source_name)
        for zone_name, zone_geom in aoi_zones:
            c = counts.get(zone_name, {'damaged': 0, 'destroyed': 0})
            n_damaged, n_destroyed = c['damaged'], c['destroyed']
            n_total = n_damaged + n_destroyed
            total_b = total_buildings_by_zone.get(zone_name, 0)

            if source_aoi_geom is not None:
                inter = source_aoi_geom.Intersection(zone_geom) if source_aoi_geom.Intersects(zone_geom) else None
                source_aoi_area_km2 = area_km2(inter) if inter is not None and not inter.IsEmpty() else 0.0
            else:
                source_aoi_area_km2 = None

            rows.append({
                'source': source_name, 'zone': zone_name,
                'total_buildings': total_b,
                'source_aoi_area_km2': round(source_aoi_area_km2, 2) if source_aoi_area_km2 is not None else None,
                'n_endommages': n_damaged, 'n_detruits': n_destroyed, 'n_total': n_total,
            })
            print(f"    {zone_name:15s} : endommages={n_damaged}  detruits={n_destroyed}  total={n_total}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'zone', 'total_buildings', 'source_aoi_area_km2',
                                            'n_endommages', 'n_detruits', 'n_total'])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
