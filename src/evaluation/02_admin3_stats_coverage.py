# -*- coding: utf-8 -*-
"""Statistiques par unité administrative de niveau 3 — surface urbaine, nombre de bâtiments, population, mouvement de sol — et part de chaque unité couverte par l'emprise d'analyse de chaque produit de dommage.

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
# CONFIGURATION — chemins generaux
# =============================================================================

BASE_DIR = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI")
ORIGINAL_DIR = os.path.join(BASE_DIR, "original")
ANALYSE_DIR = os.path.join(BASE_DIR, "analyse")

ADMIN3_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_admin_boundaries.geojson\ven_admin3.geojson")
ADMIN3_ID_FIELD = 'adm3_pcode'  # None = auto-detecte le premier champ contenant 'pcode' ou 'id'; sinon precise le nom exact

GHS_BUILT_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\GHS_BUILT_S_E2025_GLOBE_R2023A_54009_100_V1_0_R8_C12\GHS_BUILT_S_E2025_GLOBE_R2023A_54009_100_V1_0_R8_C12.tif")
POPULATION_PATH = os.path.join(DONNEES, r"VENEZUELA\HDX\ven_pop_2026_CN_100m_R2025A_v1.tif")
GROUND_MOVEMENT_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI00_GRM_PRODUCT_v2\EMSR884_AOI00_GRM_PRODUCT_groundMovementA_v2.shp")

BUILDINGS_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_overture_ven_buildings_overture_gpkg\buildings.gpkg")
BUILDINGS_OVERTURE_FIELD_OVERRIDE = [
    'id', 'name', 'name_en', 'class', 'subtype', 'height', 'level',
    'num_floors', 'source', 'adm0_pcode', 'adm0_name', 'adm1_pcode',
    'adm1_name', 'adm2_pcode', 'adm2_name', 'adm3_pcode', 'adm3_name',
    'adm4_pcode', 'adm4_name',
]  # ce fichier a un schema interne corrompu (deja rencontre dans ce projet) — contournement par position
BUILDINGS_OSM_PATH = os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_osm_ven_buildings_osm_gpkg\buildings.gpkg")
BUILDINGS_OSM_FIELD_OVERRIDE = [
    'id', 'name', 'name_en', 'name_es', 'building', 'building_levels',
    'building_materials', 'addr_full', 'addr_housenumber', 'addr_street',
    'addr_city', 'office', 'source', 'adm0_pcode', 'adm0_name',
    'adm1_pcode', 'adm1_name', 'adm2_pcode', 'adm2_name', 'adm3_pcode',
    'adm3_name', 'adm4_pcode', 'adm4_name', 'name_latin',
]

OSU_AOI_PATH = os.path.join(ORIGINAL_DIR, "osu_aoi.gpkg")  # produit par le script 1

CSV_STATS_OUT = os.path.join(ANALYSE_DIR, "admin3_stats.csv")
CSV_COVERAGE_OUT = os.path.join(ANALYSE_DIR, "admin3_coverage_par_source.csv")

# =============================================================================
# CONFIGURATION — classification dommage par source (13 sources)
#
# Pour chaque source : (kind, path, class_field, damaged_values, destroyed_values)
#   kind = 'points' (fichier de points/polygones a joindre spatialement aux
#          batiments) ou 'raster_continuous' (raster + seuil, ex: EOS)
#   damaged_values / destroyed_values : listes de valeurs brutes qui
#          comptent comme "endommage" / "detruit". Pour les sources
#          binaires (only_damaged=True, pas de sous-classe), destroyed
#          reste vide et damaged=='presence' (toute entite = endommage,
#          pas de distinction detruit — colonne destroyed restera NaN,
#          colonne 'endommages+detruits' = colonne 'endommages').
# =============================================================================

DAMAGE_CONFIG = {
    'chatmap': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_Overture.gpkg"),
        'class_field': 'cm_damaged',
        'damaged_values': ['significant', 'minimal'],
        'destroyed_values': ['complete'],
    },
    'disha': {
        'kind': 'points_csv',
        'path': os.path.join(DONNEES, r"VENEZUELA\DISHA\Caracas\nwcaracas_final_inference_result.csv"),
        'class_field': 'damaged',
        'damaged_values': ['TRUE', 'True', True],
        'destroyed_values': [],  # binaire — pas de sous-classe detruit
    },
    'ems': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture.gpkg"),
        'class_field': 'cm_damage_gra',
        'damaged_values': ['Possibly damaged', 'Damaged'],
        'destroyed_values': ['Destroyed'],
    },
    'eos': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg"),
        'class_field': 'classe',
        'damaged_values': ['damaged'],
        'destroyed_values': ['destroyed'],
    },
    'fair': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\Fair\venezuela_fair_damage_points.geojson"),
        'class_field': 'severity',
        'damaged_values': ['major'],
        'destroyed_values': ['destroyed'],
    },
    'impact': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\IMPACT Initiatives S1 DPM\impact_ven_earthquake_sentinel1_damaged_20260625_v3.geojson"),
        'class_field': None,  # binaire, only_damaged=True — pas de champ de classe
        'damaged_values': None,
        'destroyed_values': [],
    },
    'mapswipe': {
        'kind': '****',  # PLACEHOLDER — venezuela_validated_damage.geojson evoque plus tot,
        'path': r"****",  # mais son champ de classe n'a jamais ete confirme dans ce projet
        'class_field': '****',
        'damaged_values': [],
        'destroyed_values': [],
    },
    'microsoft': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\Microsoft AI for Good Lab\from_huggingFace\venezuela_microsoft_damage_points.geojson"),
        'class_field': 'severity',
        'damaged_values': None,  # PLACEHOLDER — valeurs exactes de 'severity' jamais listees precisement
        'destroyed_values': [],
    },
    'nasa_s1': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s1_on_overture.gpkg"),
        'class_field': 'classe',
        'damaged_values': ['damaged'],
        'destroyed_values': ['destroyed'],
    },
    'nasa_s2': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s2_on_overture.gpkg"),
        'class_field': 'classe',
        'damaged_values': ['damaged'],
        'destroyed_values': ['destroyed'],
    },
    'osu': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"),
        'class_field': 'damage_confidence',
        'damaged_values': ['possible', 'probable'],
        'destroyed_values': ['high_confidence'],
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
        'class_field': None,  # binaire, only_damaged=True
        'damaged_values': None,
        'destroyed_values': [],
    },
    'ungsc': {
        'kind': 'points',
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\ungsc_on_overture.gpkg"),
        'class_field': 'classe',
        'damaged_values': ['damaged'],
        'destroyed_values': [],  # UNGSC est binaire — jamais de classe 'destroyed'
    },
}

SEP = "=" * 70

# =============================================================================
# HELPERS GEOMETRIE / IO
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


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


def load_admin3_full(path):
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir admin3 : {path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    defn = lyr.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    id_field = ADMIN3_ID_FIELD
    if id_field is None:
        for fn in field_names:
            if 'pcode' in fn.lower() and '3' in fn:
                id_field = fn
                break
        if id_field is None:
            for fn in field_names:
                if 'pcode' in fn.lower():
                    id_field = fn
                    break
    out = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        if not g.IsValid():
            g = g.MakeValid()
        attrs = {fn: feat.GetField(fn) for fn in field_names}
        out.append({'geom': g, 'attrs': attrs})
    ds = None
    print(f"Admin3 : {len(out)} unite(s) — champ ID detecte: {id_field}")
    return out, field_names, id_field


def load_single_geom(path):
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
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        geoms.append(g)
    ds = None
    if not geoms:
        return None
    union = geoms[0]
    for g in geoms[1:]:
        union = union.Union(g)
    return union


def raster_sum_in_geom(raster_path, geom):
    """Somme des valeurs de pixel du raster a l'interieur de geom (masque
    par rasterisation du polygone) — utilise pour GHS_Built (surface
    urbaine en m2 par pixel) et population."""
    ds = gdal.Open(raster_path)
    if ds is None:
        return None, None
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
        return 0.0, 0

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
    total = float(np.nansum(arr[valid])) if valid.any() else 0.0
    n_px = int(valid.sum())
    return total, n_px


def count_buildings_in_geom(buildings_path, geom, field_override=None):
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


def ground_movement_area_in_geom(shp_path, geom):
    ds = ogr.Open(shp_path)
    if ds is None:
        return 0.0
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    env = geom.GetEnvelope()
    lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])
    total_km2 = 0.0
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        if not g2.Intersects(geom):
            continue
        try:
            inter = g2.Intersection(geom)
        except Exception:
            continue
        if inter and not inter.IsEmpty():
            total_km2 += area_km2(inter)
    ds = None
    return total_km2


# =============================================================================
# DOMMAGES — comptage par source, restreint a une geometrie donnee
# =============================================================================

def count_damage_points(cfg, geom):
    """Compte (endommages, detruits) parmi les entites de cfg['path'] dont
    le centroide tombe dans geom. Retourne (None, None) si non applicable
    (chemin placeholder '****' ou fichier introuvable)."""
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
            # Source binaire (only_damaged=True) : toute entite = endommage
            n_damaged += 1
            continue
        raw = feat.GetField(class_field)
        if raw in destroyed_vals:
            n_destroyed += 1
        elif damaged_vals is None or raw in damaged_vals:
            n_damaged += 1
    ds = None
    return n_damaged, n_destroyed


def count_damage_csv(cfg, geom):
    """Variante pour fichier CSV avec colonnes lon/lat (ex: DISHA)."""
    path = cfg.get('path')
    if not path or path == '****' or not os.path.exists(path):
        return None, None
    import csv as _csv
    class_field = cfg.get('class_field')
    damaged_vals = cfg.get('damaged_values')
    env = geom.GetEnvelope()
    n_damaged, n_destroyed = 0, 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = _csv.DictReader(f)
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


def count_damage_for_source(source_name, cfg, geom, buildings_overture_path):
    kind = cfg.get('kind')
    if kind == 'points':
        return count_damage_points(cfg, geom)
    elif kind == 'points_csv':
        return count_damage_csv(cfg, geom)
    else:
        return None, None  # placeholder '****' — pas de donnee disponible


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(ANALYSE_DIR, exist_ok=True)

    print(SEP)
    print("  Chargement admin3 (complet, non decoupe)")
    print(SEP)
    admin3_list, admin3_fields, id_field = load_admin3_full(ADMIN3_PATH)

    print(f"\n{SEP}")
    print("  Restriction aux admin3 touches par OSU (entiers, pas decoupes)")
    print(SEP)
    osu_geom = load_single_geom(OSU_AOI_PATH)
    if osu_geom is None:
        sys.exit(f"Impossible de charger l'AOI OSU depuis {OSU_AOI_PATH} — lance d'abord le script 1.")
    scoped = [u for u in admin3_list if u['geom'].Intersects(osu_geom)]
    print(f"  {len(scoped)} / {len(admin3_list)} admin3 retenus (touchent l'AOI OSU)")

    # ---- CSV STATS (1 ligne par admin3) --------------------------------
    print(f"\n{SEP}")
    print("  Calcul des stats par admin3 (urbain GHS, batiments, population, mouvement de sol)")
    print(SEP)
    stats_rows = []
    for i, unit in enumerate(scoped):
        g = unit['geom']
        a_km2 = area_km2(g)
        urban_m2, _ = raster_sum_in_geom(GHS_BUILT_PATH, g)
        urban_km2 = (urban_m2 or 0.0) / 1e6
        pop, _ = raster_sum_in_geom(POPULATION_PATH, g)
        n_overture = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, g, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
        n_osm = count_buildings_in_geom(BUILDINGS_OSM_PATH, g, BUILDINGS_OSM_FIELD_OVERRIDE)
        grm_km2 = ground_movement_area_in_geom(GROUND_MOVEMENT_PATH, g)
        row = {
            'admin3_id': unit['attrs'].get(id_field, i) if id_field else i,
            **{fn: unit['attrs'].get(fn) for fn in admin3_fields},
            'area_km2': a_km2,
            'urban_area_km2': urban_km2,
            'urban_pct': 100 * urban_km2 / a_km2 if a_km2 > 0 else None,
            'n_buildings_overture': n_overture,
            'n_buildings_osm': n_osm,
            'population': pop,
            'ground_movement_km2': grm_km2,
            'ground_movement_pct': 100 * grm_km2 / a_km2 if a_km2 > 0 else None,
        }
        stats_rows.append(row)
        print(f"  [{i+1}/{len(scoped)}] admin3={row['admin3_id']}  aire={a_km2:.1f}km2  "
              f"urbain={urban_km2:.2f}km2  overture={n_overture}  osm={n_osm}  pop={(pop or 0):.0f}")

    fieldnames = list(stats_rows[0].keys()) if stats_rows else []
    with open(CSV_STATS_OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(stats_rows)
    print(f"\nEcrit : {CSV_STATS_OUT}")

    # ---- CSV COVERAGE (1 ligne par admin3 x source) ---------------------
    print(f"\n{SEP}")
    print("  Calcul de la couverture par source + comptage dommages")
    print(SEP)
    coverage_rows = []
    for source_name, cfg in DAMAGE_CONFIG.items():
        aoi_path = os.path.join(ORIGINAL_DIR, f"{source_name}_aoi.gpkg")
        if not os.path.exists(aoi_path):
            print(f"  Attention: AOI introuvable pour '{source_name}' — lance le script 1 d'abord")
            continue
        source_geom = load_single_geom(aoi_path)
        if source_geom is None:
            continue
        print(f"\n  Source : {source_name}")
        for i, unit in enumerate(scoped):
            g = unit['geom']
            admin3_id = unit['attrs'].get(id_field, i) if id_field else i
            if not g.Intersects(source_geom):
                aoi_pct = 0.0
                inter_geom = None
            else:
                try:
                    inter_geom = g.Intersection(source_geom)
                except Exception:
                    inter_geom = None
                inter_km2 = area_km2(inter_geom) if inter_geom and not inter_geom.IsEmpty() else 0.0
                a_km2 = area_km2(g)
                aoi_pct = 100 * inter_km2 / a_km2 if a_km2 > 0 else 0.0

            urban_pct_covered = None
            bldg_pct_covered = None
            pop_pct_covered = None
            if inter_geom is not None and not inter_geom.IsEmpty():
                urban_inter_m2, _ = raster_sum_in_geom(GHS_BUILT_PATH, inter_geom)
                urban_total_m2, _ = raster_sum_in_geom(GHS_BUILT_PATH, g)
                if urban_total_m2 and urban_total_m2 > 0:
                    urban_pct_covered = 100 * (urban_inter_m2 or 0.0) / urban_total_m2

                pop_inter, _ = raster_sum_in_geom(POPULATION_PATH, inter_geom)
                pop_total, _ = raster_sum_in_geom(POPULATION_PATH, g)
                if pop_total and pop_total > 0:
                    pop_pct_covered = 100 * (pop_inter or 0.0) / pop_total

                n_bldg_inter = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, inter_geom, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
                n_bldg_total = count_buildings_in_geom(BUILDINGS_OVERTURE_PATH, g, BUILDINGS_OVERTURE_FIELD_OVERRIDE)
                if n_bldg_total:
                    bldg_pct_covered = 100 * (n_bldg_inter or 0) / n_bldg_total

            n_damaged, n_destroyed = (None, None)
            if inter_geom is not None and not inter_geom.IsEmpty():
                n_damaged, n_destroyed = count_damage_for_source(
                    source_name, cfg, inter_geom, BUILDINGS_OVERTURE_PATH)

            if n_damaged is None and n_destroyed is None:
                total = None
            elif n_destroyed:
                total = (n_damaged or 0) + n_destroyed
            else:
                total = n_damaged

            coverage_rows.append({
                'admin3_id': admin3_id,
                'source': source_name,
                'aoi_coverage_pct': round(aoi_pct, 2),
                'urban_coverage_pct': round(urban_pct_covered, 2) if urban_pct_covered is not None else None,
                'buildings_coverage_pct': round(bldg_pct_covered, 2) if bldg_pct_covered is not None else None,
                'population_coverage_pct': round(pop_pct_covered, 2) if pop_pct_covered is not None else None,
                'n_endommages': n_damaged,
                'n_detruits': n_destroyed if n_destroyed else None,
                'n_endommages_plus_detruits': total,
            })

    fieldnames2 = list(coverage_rows[0].keys()) if coverage_rows else []
    with open(CSV_COVERAGE_OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames2)
        w.writeheader()
        w.writerows(coverage_rows)
    print(f"\nEcrit : {CSV_COVERAGE_OUT}")


if __name__ == '__main__':
    main()
