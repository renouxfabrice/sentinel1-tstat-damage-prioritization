# -*- coding: utf-8 -*-
"""Matrice de recoupement entre les emprises d'analyse des produits, deux à deux, et couches des zones couvertes par au moins N produits, calculées sur une grille raster commune plutôt que par superposition vectorielle.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import gc
import numpy as np
from config import DONNEES

try:
    from osgeo import ogr, osr, gdal
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()
gdal.UseExceptions()
gdal.SetCacheMax(256 * 1024 * 1024)

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI")
ORIGINAL_DIR = os.path.join(BASE_DIR, "original")
ANALYSE_DIR = os.path.join(BASE_DIR, "analyse")

SOURCE_NAMES = [
    'mapswipe', 'chatmap', 'disha', 'ems', 'eos', 'fair', 'impact',
    'microsoft', 'nasa_s1', 'nasa_s2', 'osu', 'uhsail', 'unep', 'ungsc',
]  # ordre = ordre des bits du masque (bit 0 = mapswipe, etc.)

CHATMAP_INDEX = SOURCE_NAMES.index('chatmap')
N_SOURCES = len(SOURCE_NAMES)

# Resolution de la grille commune — ~110m (0.001 deg). Assez fin pour
# sur l'etendue combinee de toutes les AOI.
GRID_RES_DEG = 0.001

# Seuils "au moins N sources" pour les couches de sortie
N_THRESHOLDS = [3, 5, 7, 10]

CSV_MATRIX_OUT = os.path.join(ANALYSE_DIR, "matrice_recoupement_sources.csv")
LAYERS_OUT_DIR = os.path.join(ANALYSE_DIR, "couches_multi_sources")

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


def load_aoi_geom(path):
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
    if len(geoms) == 1:
        return geoms[0]
    multi = ogr.Geometry(ogr.wkbMultiPolygon)
    for g in geoms:
        if g.GetGeometryType() in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
            for i in range(g.GetGeometryCount()):
                multi.AddGeometry(g.GetGeometryRef(i))
        else:
            multi.AddGeometry(g)
    return multi


def cell_area_km2(lat_mid, res_deg):
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return res_deg * deg_to_km_lon * res_deg * deg_to_km_lat


def rasterize_geom(geom, xmin, ymax, nx, ny, res_deg):
    """Rasterise une geometrie sur la grille commune -> tableau booleen."""
    mem_drv = gdal.GetDriverByName('MEM')
    mask_ds = mem_drv.Create('', nx, ny, 1, gdal.GDT_Byte)
    mask_ds.SetGeoTransform((xmin, res_deg, 0, ymax, 0, -res_deg))
    mask_ds.SetProjection(WGS84.ExportToWkt())

    mem_vec_drv = ogr.GetDriverByName('Memory')
    mem_vec_ds = mem_vec_drv.CreateDataSource('rz')
    mem_lyr = mem_vec_ds.CreateLayer('rz', srs=WGS84, geom_type=ogr.wkbMultiPolygon)
    feat = ogr.Feature(mem_lyr.GetLayerDefn())
    feat.SetGeometry(geom)
    mem_lyr.CreateFeature(feat)
    gdal.RasterizeLayer(mask_ds, [1], mem_lyr, burn_values=[1])
    arr = mask_ds.GetRasterBand(1).ReadAsArray().astype(bool)
    mask_ds = None
    mem_vec_ds = None
    return arr


def polygonize_mask(mask, xmin, ymax, res_deg, out_path, layer_name):
    ny, nx = mask.shape
    mem_drv = gdal.GetDriverByName('MEM')
    mask_ds = mem_drv.Create('', nx, ny, 1, gdal.GDT_Byte)
    mask_ds.SetGeoTransform((xmin, res_deg, 0, ymax, 0, -res_deg))
    mask_ds.SetProjection(WGS84.ExportToWkt())
    mask_ds.GetRasterBand(1).WriteArray(mask.astype(np.uint8))

    drv = ogr.GetDriverByName('GPKG')
    if os.path.exists(out_path):
        drv.DeleteDataSource(out_path)
    ds_o = drv.CreateDataSource(out_path)
    lyr_o = ds_o.CreateLayer(layer_name, srs=WGS84, geom_type=ogr.wkbPolygon)
    lyr_o.CreateField(ogr.FieldDefn('val', ogr.OFTInteger))
    gdal.Polygonize(mask_ds.GetRasterBand(1), mask_ds.GetRasterBand(1), lyr_o, 0, [], callback=None)

    # Retirer les entites val=0 (hors zone) — ne garder que val=1
    lyr_o.SetAttributeFilter('val = 0')
    for feat in lyr_o:
        lyr_o.DeleteFeature(feat.GetFID())
    lyr_o.SetAttributeFilter(None)
    n = lyr_o.GetFeatureCount()
    ds_o = None
    mask_ds = None
    return n


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(ANALYSE_DIR, exist_ok=True)
    os.makedirs(LAYERS_OUT_DIR, exist_ok=True)

    print(SEP)
    print("  Chargement des AOI et calcul de l'emprise commune")
    print(SEP)
    geoms = {}
    xmin_g, ymin_g, xmax_g, ymax_g = None, None, None, None
    for name in SOURCE_NAMES:
        path = os.path.join(ORIGINAL_DIR, f"{name}_aoi.gpkg")
        if not os.path.exists(path):
            print(f"  Attention: AOI introuvable pour '{name}' — ignore (lance le script 1 d'abord)")
            continue
        g = load_aoi_geom(path)
        if g is None:
            print(f"  Attention: geometrie vide pour '{name}'")
            continue
        geoms[name] = g
        env = g.GetEnvelope()  # xmin,xmax,ymin,ymax
        xmin_g = env[0] if xmin_g is None else min(xmin_g, env[0])
        xmax_g = env[1] if xmax_g is None else max(xmax_g, env[1])
        ymin_g = env[2] if ymin_g is None else min(ymin_g, env[2])
        ymax_g = env[3] if ymax_g is None else max(ymax_g, env[3])
        print(f"  {name} : emprise ({env[0]:.3f},{env[2]:.3f}) -> ({env[1]:.3f},{env[3]:.3f})")

    if not geoms:
        sys.exit("Aucune AOI chargee — rien a faire.")

    nx = int(np.ceil((xmax_g - xmin_g) / GRID_RES_DEG)) + 1
    ny = int(np.ceil((ymax_g - ymin_g) / GRID_RES_DEG)) + 1
    print(f"\n  Grille commune : {nx} x {ny} cellules (~{GRID_RES_DEG*111320:.0f}m/cellule)")
    if nx * ny > 200_000_000:
        sys.exit(f"Grille trop grande ({nx*ny:,} cellules) — augmente GRID_RES_DEG.")

    print(f"\n{SEP}")
    print("  Rasterisation de chaque source + construction du bitmask")
    print(SEP)
    bitmask = np.zeros((ny, nx), dtype=np.uint16)
    for i, name in enumerate(SOURCE_NAMES):
        if name not in geoms:
            continue
        arr = rasterize_geom(geoms[name], xmin_g, ymax_g, nx, ny, GRID_RES_DEG)
        bitmask |= (arr.astype(np.uint16) << i)
        n_cells = int(arr.sum())
        print(f"  {name} (bit {i}) : {n_cells:,} cellules")
        del arr
        gc.collect()

    lat_mid = (ymin_g + ymax_g) / 2
    cell_km2 = cell_area_km2(lat_mid, GRID_RES_DEG)
    print(f"\n  Aire par cellule (latitude moyenne {lat_mid:.2f}°) : {cell_km2:.4f} km2")

    # --- Matrice de recoupement pairwise ---
    print(f"\n{SEP}")
    print("  Calcul de la matrice de recoupement (paires de sources)")
    print(SEP)
    present = [n for n in SOURCE_NAMES if n in geoms]
    rows = []
    for name_i in present:
        i = SOURCE_NAMES.index(name_i)
        mask_i = (bitmask & (1 << i)) != 0
        area_i_km2 = float(mask_i.sum()) * cell_km2
        for name_j in present:
            j = SOURCE_NAMES.index(name_j)
            mask_j = (bitmask & (1 << j)) != 0
            overlap_km2 = float((mask_i & mask_j).sum()) * cell_km2
            pct_of_i = 100 * overlap_km2 / area_i_km2 if area_i_km2 > 0 else None
            rows.append({
                'source_ligne': name_i, 'source_colonne': name_j,
                'aire_ligne_km2': round(area_i_km2, 2),
                'recoupement_km2': round(overlap_km2, 2),
                'pct_de_la_source_ligne': round(pct_of_i, 2) if pct_of_i is not None else None,
            })
        del mask_i
        gc.collect()

    with open(CSV_MATRIX_OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source_ligne', 'source_colonne', 'aire_ligne_km2',
                                            'recoupement_km2', 'pct_de_la_source_ligne'])
        w.writeheader()
        w.writerows(rows)
    print(f"  Ecrit : {CSV_MATRIX_OUT}")

    # --- Couches multi-sources ---
    print(f"\n{SEP}")
    print("  Construction des couches multi-sources")
    print(SEP)
    counts = np.zeros((ny, nx), dtype=np.uint8)
    for bit_pos in range(N_SOURCES):
        counts += ((bitmask & (1 << bit_pos)) != 0).astype(np.uint8)

    for n_thr in N_THRESHOLDS:
        mask = counts >= n_thr
        n_cells = int(mask.sum())
        out_path = os.path.join(LAYERS_OUT_DIR, f"au_moins_{n_thr}_sources.gpkg")
        n_poly = polygonize_mask(mask, xmin_g, ymax_g, GRID_RES_DEG, out_path, f"au_moins_{n_thr}_sources")
        print(f"  >= {n_thr} sources : {n_cells:,} cellules, {n_poly} polygone(s) -> {os.path.basename(out_path)}")
        del mask
        gc.collect()

    # Toutes sauf chatmap (tous les autres presents, chatmap absent ou pas — peu importe)
    mask_no_chatmap_bit = np.uint16(0xFFFF) ^ np.uint16(1 << CHATMAP_INDEX)
    n_present_excl_chatmap = len(present) - (1 if 'chatmap' in present else 0)
    counts_excl_chatmap = np.zeros((ny, nx), dtype=np.uint8)
    for bit_pos in range(N_SOURCES):
        if bit_pos == CHATMAP_INDEX:
            continue
        counts_excl_chatmap += ((bitmask & (1 << bit_pos)) != 0).astype(np.uint8)
    mask_all_excl_chatmap = counts_excl_chatmap >= n_present_excl_chatmap
    n_cells = int(mask_all_excl_chatmap.sum())
    out_path = os.path.join(LAYERS_OUT_DIR, "toutes_sauf_chatmap.gpkg")
    n_poly = polygonize_mask(mask_all_excl_chatmap, xmin_g, ymax_g, GRID_RES_DEG, out_path, "toutes_sauf_chatmap")
    print(f"  Toutes sauf chatmap ({n_present_excl_chatmap} sources) : {n_cells:,} cellules, "
          f"{n_poly} polygone(s) -> {os.path.basename(out_path)}")
    del counts_excl_chatmap, mask_all_excl_chatmap
    gc.collect()

    # Toutes les sources, chatmap inclus
    mask_all = counts >= len(present)
    n_cells = int(mask_all.sum())
    out_path = os.path.join(LAYERS_OUT_DIR, "toutes_sources_avec_chatmap.gpkg")
    n_poly = polygonize_mask(mask_all, xmin_g, ymax_g, GRID_RES_DEG, out_path, "toutes_sources_avec_chatmap")
    print(f"  Toutes les sources ({len(present)}) : {n_cells:,} cellules, "
          f"{n_poly} polygone(s) -> {os.path.basename(out_path)}")

    print(f"\n{SEP}")
    print(f"  Termine.")
    print(f"    Matrice : {CSV_MATRIX_OUT}")
    print(f"    Couches : {LAYERS_OUT_DIR}")
    print(SEP)


if __name__ == '__main__':
    main()
