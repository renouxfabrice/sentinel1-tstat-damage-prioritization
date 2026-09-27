# -*- coding: utf-8 -*-
"""Population, nombre de bâtiments selon quatre bases d'empreintes, surface totale et surface urbaine de chaque zone, déclinées en zones couvertes par les nuages, non couvertes, et total.

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

NOT_ANALYSED_PATHS = [
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI02_GRA_MONIT01_v2\EMSR884_AOI02_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI06_GRA_MONIT01_v2\EMSR884_AOI06_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI08_GRA_MONIT01_v2\EMSR884_AOI08_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI12_GRA_MONIT01_v3\EMSR884_AOI12_GRA_MONIT01_notAnalysedA_v1.shp"),
]

BUILDINGS_PATHS = {
    'overture': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg"),
    'osm': os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_osm_ven_buildings_osm_gpkg\buildings.gpkg"),
    'open_buildings': os.path.join(DONNEES, r"VENEZUELA\Building\buidling_aoi_cems_open buidling_v3.gpkg"),
    'microsoft_vida': os.path.join(DONNEES, r"VENEZUELA\Building\buidling_aoi_cems_Microsoft_Vida.gpkg"),
}

GHS_BUILT_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\GHS_BUILT_S_E2025_GLOBE_R2023A_54009_100_V1_0_R8_C12\GHS_BUILT_S_E2025_GLOBE_R2023A_54009_100_V1_0_R8_C12.tif")
POPULATION_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_pop_2026_CN_100m_R2025A_v1.tif")

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\stats_par_zone_cloud.csv")

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


def load_union_geom(path):
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


def load_multi_union(paths):
    all_geoms = [g for g in (load_union_geom(p) for p in paths) if g is not None]
    if not all_geoms:
        return None
    union = all_geoms[0]
    for g in all_geoms[1:]:
        union = union.Union(g)
    return union


def safe_intersection(a, b):
    try:
        if not a.Intersects(b):
            return None
        inter = a.Intersection(b)
        if inter is None or inter.IsEmpty():
            return None
        return inter
    except Exception:
        return None


def safe_difference(a, b):
    try:
        diff = a.Difference(b)
        if diff is None or diff.IsEmpty():
            return None
        return diff
    except Exception:
        return a


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


def count_buildings_in_geom(path, geom):
    if geom is None or not os.path.exists(path):
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


def raster_sum_in_geom(raster_path, geom):
    if geom is None:
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


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement de l'AOI et des zones nuageuses")
    print(SEP)
    zones = load_aoi_zones(AOI_PATH, AOI_ZONE_FIELD)
    cloud_geom = load_multi_union(NOT_ANALYSED_PATHS)
    print(f"  {len(zones)} zone(s) — zones nuageuses {'chargees' if cloud_geom is not None else 'AUCUNE'}")

    rows = []
    for zone_geom, zone_name in zones:
        print(f"\n{SEP}\n  {zone_name}\n{SEP}")

        if cloud_geom is not None:
            cloud_part = safe_intersection(zone_geom, cloud_geom)
            noncloud_part = safe_difference(zone_geom, cloud_geom)
        else:
            cloud_part = None
            noncloud_part = zone_geom

        for portion_name, portion_geom in [('sans_nuage', noncloud_part),
                                            ('avec_nuage', cloud_part),
                                            ('total', zone_geom)]:
            if portion_geom is None:
                row = {'zone': zone_name, 'portion': portion_name, 'area_km2': 0.0, 'urban_area_km2': 0.0,
                       'population': 0.0, 'n_buildings_overture': 0, 'n_buildings_osm': 0,
                       'n_buildings_open_buildings': 0, 'n_buildings_microsoft_vida': 0}
                rows.append(row)
                continue

            a_km2 = area_km2(portion_geom)
            urban_km2 = (raster_sum_in_geom(GHS_BUILT_PATH, portion_geom) or 0.0) / 1e6
            pop = raster_sum_in_geom(POPULATION_PATH, portion_geom) or 0.0

            counts = {}
            for src_name, src_path in BUILDINGS_PATHS.items():
                counts[src_name] = count_buildings_in_geom(src_path, portion_geom) or 0

            row = {
                'zone': zone_name, 'portion': portion_name,
                'area_km2': round(a_km2, 3), 'urban_area_km2': round(urban_km2, 3),
                'population': round(pop, 0),
                'n_buildings_overture': counts.get('overture', 0),
                'n_buildings_osm': counts.get('osm', 0),
                'n_buildings_open_buildings': counts.get('open_buildings', 0),
                'n_buildings_microsoft_vida': counts.get('microsoft_vida', 0),
            }
            rows.append(row)
            print(f"  {portion_name:12s} : aire={a_km2:.2f}km2  urbain={urban_km2:.3f}km2  "
                  f"pop={pop:.0f}  overture={row['n_buildings_overture']}  osm={row['n_buildings_osm']}  "
                  f"open_buildings={row['n_buildings_open_buildings']}  "
                  f"microsoft_vida={row['n_buildings_microsoft_vida']}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['zone', 'portion', 'area_km2', 'urban_area_km2', 'population',
                  'n_buildings_overture', 'n_buildings_osm', 'n_buildings_open_buildings',
                  'n_buildings_microsoft_vida']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
