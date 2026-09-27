# -*- coding: utf-8 -*-
"""Surface de chaque zone d'analyse répartie par tranche d'intensité macrosismique MMI.

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

MMI_SHP_PATH = os.path.join(DONNEES, r"VENEZUELA\UNGSC\M 7.5 - 17 km W of Catia La Mar_Venezuela\mi.shp")
MMI_VALUE_FIELD = "PARAMVALUE"

POPULATION_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_pop_2026_CN_100m_R2025A_v1.tif")

BUILDINGS_PATHS = {
    'overture': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg"),
    'osm': os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_osm_ven_buildings_osm_gpkg\buildings.gpkg"),
    'open_buildings': os.path.join(DONNEES, r"VENEZUELA\Building\buidling_aoi_cems_open buidling_v3.gpkg"),
    'microsoft_vida': os.path.join(DONNEES, r"VENEZUELA\Building\buidling_aoi_cems_Microsoft_Vida.gpkg"),
}

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

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\zone_mmi_repartition.csv")

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
    lyr = ds.GetLayer()
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
        out.append((g2, feat.GetField(zone_field)))
    ds = None
    return out


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


def mmi_category(value):
    for lo, hi, label in MMI_BINS:
        if lo <= value < hi:
            return label
    return None


def raster_sum_in_geom(raster_path, geom):
    if geom is None or geom.IsEmpty():
        return 0.0
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


def count_buildings_in_geom(path, geom):
    if geom is None or geom.IsEmpty() or not os.path.exists(path):
        return 0
    ds = ogr.Open(path)
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


def load_mmi_cells_for_zone(mmi_path, value_field, zone_geom):
    ds = ogr.Open(mmi_path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {mmi_path}")
    lyr = ds.GetLayer()
    defn = lyr.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    if value_field not in field_names:
        sys.exit(f"Erreur: champ '{value_field}' introuvable — champs: {field_names}")
    tr = get_transform_to_wgs84(lyr)
    env = zone_geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])

    by_category_multi = {}
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.Intersects(zone_geom):
            continue
        try:
            inter = g2.Intersection(zone_geom)
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
        if cat not in by_category_multi:
            by_category_multi[cat] = ogr.Geometry(ogr.wkbMultiPolygon)
        multi = by_category_multi[cat]
        if inter.GetGeometryType() in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
            for i in range(inter.GetGeometryCount()):
                multi.AddGeometry(inter.GetGeometryRef(i))
        elif inter.GetGeometryType() in (ogr.wkbPolygon, ogr.wkbPolygon25D):
            multi.AddGeometry(inter)
    ds = None
    return by_category_multi


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement de l'AOI")
    print(SEP)
    zones = load_aoi_zones(AOI_PATH, AOI_ZONE_FIELD)
    print(f"  {len(zones)} zone(s)")

    rows = []
    for zone_geom, zone_name in zones:
        print(f"\n{SEP}\n  {zone_name}\n{SEP}")
        zone_total_km2 = area_km2(zone_geom)
        by_cat = load_mmi_cells_for_zone(MMI_SHP_PATH, MMI_VALUE_FIELD, zone_geom)

        for _, _, cat in MMI_BINS:
            cat_multi = by_cat.get(cat)
            if cat_multi is None or cat_multi.GetGeometryCount() == 0:
                cat_km2, pop = 0.0, 0.0
                counts = {k: 0 for k in BUILDINGS_PATHS}
            else:
                cat_km2 = area_km2(cat_multi)
                pop = raster_sum_in_geom(POPULATION_PATH, cat_multi) or 0.0
                counts = {k: (count_buildings_in_geom(p, cat_multi) or 0) for k, p in BUILDINGS_PATHS.items()}
            pct = 100 * cat_km2 / zone_total_km2 if zone_total_km2 > 0 else 0.0
            rows.append({
                'zone': zone_name, 'zone_area_km2': round(zone_total_km2, 3),
                'mmi_categorie': cat, 'area_km2': round(cat_km2, 3),
                'pct_de_la_zone': round(pct, 2), 'population': round(pop, 0),
                'n_buildings_overture': counts.get('overture', 0),
                'n_buildings_osm': counts.get('osm', 0),
                'n_buildings_open_buildings': counts.get('open_buildings', 0),
                'n_buildings_microsoft_vida': counts.get('microsoft_vida', 0),
            })
            print(f"    MMI {cat:8s} : {cat_km2:.2f} km2 ({pct:.1f}%)  pop={pop:.0f}  "
                  f"overture={counts.get('overture',0)}  osm={counts.get('osm',0)}  "
                  f"open_buildings={counts.get('open_buildings',0)}  "
                  f"microsoft_vida={counts.get('microsoft_vida',0)}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['zone', 'zone_area_km2', 'mmi_categorie', 'area_km2', 'pct_de_la_zone', 'population',
                  'n_buildings_overture', 'n_buildings_osm', 'n_buildings_open_buildings',
                  'n_buildings_microsoft_vida']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
