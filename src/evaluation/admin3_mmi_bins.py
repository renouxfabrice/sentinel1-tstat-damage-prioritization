# -*- coding: utf-8 -*-
"""Comptage du bâti, de la population et de la surface urbaine par unité administrative de niveau 3 et par tranche d'intensité macrosismique MMI, sur l'emprise effectivement analysée.

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
# CONFIGURATION — PARAMETRABLE
# =============================================================================

# Change ce chemin pour basculer entre l'AOI EMS reellement analysee et
# l'AOI CEMS complete prevue au depart (All_EMSR884.gpkg)
AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v3.gpkg")
AOI_AREA_FIELD = "area"  # None si le fichier AOI n'a pas de champ de zone nommee

MMI_SHP_PATH = os.path.join(DONNEES, r"VENEZUELA\UNGSC\M 7.5 - 17 km W of Catia La Mar_Venezuela\mi.shp")
MMI_VALUE_FIELD = "PARAMVALUE"

ADMIN3_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_admin_boundaries.geojson\ven_admin3.geojson")
ADMIN3_ID_FIELD = 'adm3_pcode'

BUILDINGS_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_overture_ven_buildings_overture_gpkg\buildings.gpkg")
BUILDINGS_OVERTURE_FIELD_OVERRIDE = [
    'id', 'name', 'name_en', 'class', 'subtype', 'height', 'level',
    'num_floors', 'source', 'adm0_pcode', 'adm0_name', 'adm1_pcode',
    'adm1_name', 'adm2_pcode', 'adm2_name', 'adm3_pcode', 'adm3_name',
    'adm4_pcode', 'adm4_name',
]
BUILDINGS_OSM_PATH = os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_osm_ven_buildings_osm_gpkg\buildings.gpkg")
BUILDINGS_OSM_FIELD_OVERRIDE = [
    'id', 'name', 'name_en', 'name_es', 'building', 'building_levels',
    'building_materials', 'addr_full', 'addr_housenumber', 'addr_street',
    'addr_city', 'office', 'source', 'adm0_pcode', 'adm0_name',
    'adm1_pcode', 'adm1_name', 'adm2_pcode', 'adm2_name', 'adm3_pcode',
    'adm3_name', 'adm4_pcode', 'adm4_name', 'name_latin',
]
POPULATION_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_pop_2026_CN_100m_R2025A_v1.tif")

# Seuils Worden et al. 2012 — demi-entiers, meme convention que la
# grille de reference USGS ShakeMap
MMI_BINS = [
    (float('-inf'), 1.5, 'I'),
    (1.5, 3.5, 'II-III'),
    (3.5, 4.5, 'IV'),
    (4.5, 5.5, 'V'),
    (5.5, 6.5, 'VI'),
    (6.5, 7.5, 'VII'),
    (7.5, 8.5, 'VIII'),
    (8.5, 9.5, 'IX'),
    (9.5, float('inf'), 'X+'),
]

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\admin3_mmi_bins.csv")

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


def mmi_category(value):
    for lo, hi, label in MMI_BINS:
        if lo <= value < hi:
            return label
    return None


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


def load_aoi_features_with_area(path, area_field):
    if area_field is None:
        return []
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


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


def load_mmi_cells_for_admin3(mmi_path, value_field, admin3_geom):
    ds = ogr.Open(mmi_path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {mmi_path}")
    lyr = ds.GetLayer()
    defn = lyr.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    if value_field not in field_names:
        sys.exit(f"Erreur: champ '{value_field}' introuvable dans {mmi_path}.\n"
                  f"Champs disponibles: {field_names}")
    tr = get_transform_to_wgs84(lyr)
    env = admin3_geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])

    by_category = {}
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.Intersects(admin3_geom):
            continue
        try:
            inter = g2.Intersection(admin3_geom)
        except Exception:
            continue
        if inter is None or inter.IsEmpty():
            continue
        val = feat.GetField(value_field)
        if val is None:
            continue
        cat = mmi_category(float(val))
        if cat is None:
            continue
        by_category.setdefault(cat, []).append(inter)
    ds = None

    out = {}
    for cat, geoms in by_category.items():
        multi = ogr.Geometry(ogr.wkbMultiPolygon)
        for g in geoms:
            if g.GetGeometryType() in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
                for i in range(g.GetGeometryCount()):
                    multi.AddGeometry(g.GetGeometryRef(i))
            elif g.GetGeometryType() in (ogr.wkbPolygon, ogr.wkbPolygon25D):
                multi.AddGeometry(g)
        out[cat] = multi
    return out


def raster_sum_in_geom(raster_path, geom):
    ds = gdal.Open(raster_path)
    if ds is None:
        return None
    gt = ds.GetGeoTransform()
    prj = ds.GetProjection()
    nx_full, ny_full = ds.RasterXSize, ds.RasterYSize
    band = ds.GetRasterBand(1)
    nd = band.GetNoDataValue()

    src_srs = osr.SpatialReference(); src_srs.ImportFromWkt(prj)
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr_to_raster = None
    if not src_srs.IsSame(WGS84):
        tr_to_raster = osr.CoordinateTransformation(WGS84, src_srs)
    geom_r = geom.Clone()
    if tr_to_raster is not None:
        geom_r.Transform(tr_to_raster)

    env = geom_r.GetEnvelope()
    px0 = max(0, int((env[0] - gt[0]) / gt[1]) - 1)
    px1 = min(nx_full - 1, int((env[1] - gt[0]) / gt[1]) + 1)
    py0 = max(0, int((env[3] - gt[3]) / gt[5]) - 1)
    py1 = min(ny_full - 1, int((env[2] - gt[3]) / gt[5]) + 1)
    if px0 > px1 or py0 > py1:
        ds = None
        return 0.0

    win_nx, win_ny = px1 - px0 + 1, py1 - py0 + 1
    arr = band.ReadAsArray(px0, py0, win_nx, win_ny).astype(np.float64)
    if nd is not None:
        arr[np.isclose(arr, nd)] = np.nan
    ds = None

    win_gt = (gt[0] + px0 * gt[1], gt[1], 0, gt[3] + py0 * gt[5], 0, gt[5])
    mem_drv = gdal.GetDriverByName('MEM')
    mask_ds = mem_drv.Create('', win_nx, win_ny, 1, gdal.GDT_Byte)
    mask_ds.SetGeoTransform(win_gt)
    mask_ds.SetProjection(prj)

    mem_vec_drv = ogr.GetDriverByName('Memory')
    mem_vec_ds = mem_vec_drv.CreateDataSource('mask')
    mem_lyr = mem_vec_ds.CreateLayer('mask', srs=src_srs, geom_type=ogr.wkbMultiPolygon)
    feat = ogr.Feature(mem_lyr.GetLayerDefn())
    feat.SetGeometry(geom_r)
    mem_lyr.CreateFeature(feat)
    gdal.RasterizeLayer(mask_ds, [1], mem_lyr, burn_values=[1])
    mask_arr = mask_ds.GetRasterBand(1).ReadAsArray().astype(bool)
    mask_ds = None
    mem_vec_ds = None

    valid = mask_arr & np.isfinite(arr)
    return float(np.nansum(arr[valid])) if valid.any() else 0.0


def count_buildings_in_geom(buildings_path, geom, field_override):
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
    print(f"  Chargement de l'AOI : {AOI_PATH}")
    print(SEP)
    aoi_geom = load_union_geom(AOI_PATH)
    if aoi_geom is None:
        sys.exit(f"AOI vide ou illisible : {AOI_PATH}")
    aoi_features = load_aoi_features_with_area(AOI_PATH, AOI_AREA_FIELD)

    print(f"\n{SEP}")
    print("  Admin3 dans cette AOI")
    print(SEP)
    admin3_list = load_admin3_in_aoi(ADMIN3_PATH, aoi_geom)
    if not admin3_list:
        sys.exit("Aucun admin3 trouve dans cette AOI.")

    print(f"\n{SEP}")
    print("  Calcul par admin3 x tranche MMI")
    print(SEP)
    rows = []
    for i, unit in enumerate(admin3_list):
        g = unit['geom']
        admin3_id = unit['attrs'].get(ADMIN3_ID_FIELD, i)
        aoi_zones = aoi_zones_for_geom(aoi_features, g)
        aoi_zone_str = '; '.join(str(z) for z in aoi_zones) if aoi_zones else None

        print(f"\n{SEP}")
        print(f"  [{i+1}/{len(admin3_list)}] {admin3_id} (zones={aoi_zones})")
        print(SEP)

        cells_by_cat = load_mmi_cells_for_admin3(MMI_SHP_PATH, MMI_VALUE_FIELD, g)

        for _, _, cat in MMI_BINS:
            cat_geom = cells_by_cat.get(cat)
            if cat_geom is None or cat_geom.GetGeometryCount() == 0:
                area_km2_val, n_overture, n_osm, pop = 0.0, 0, 0, 0.0
            else:
                area_km2_val = area_km2(cat_geom)
                n_overture = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, cat_geom, BUILDINGS_OVERTURE_FIELD_OVERRIDE) or 0
                n_osm = count_buildings_in_geom(BUILDINGS_OSM_PATH, cat_geom, BUILDINGS_OSM_FIELD_OVERRIDE) or 0
                pop = raster_sum_in_geom(POPULATION_PATH, cat_geom) or 0.0

            rows.append({
                'admin3_id': admin3_id, 'aoi_zone': aoi_zone_str,
                **unit['attrs'],
                'mmi_categorie': cat,
                'area_km2': round(area_km2_val, 3),
                'n_buildings_overture': n_overture,
                'n_buildings_osm': n_osm,
                'population': round(pop, 0),
            })
            print(f"    MMI {cat:8s} : aire={area_km2_val:.2f}km2  overture={n_overture}  "
                  f"osm={n_osm}  pop={pop:.0f}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
