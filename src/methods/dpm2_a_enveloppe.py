# -*- coding: utf-8 -*-
"""Reproduction de la seconde méthode de cohérence publiée dans sa variante en enveloppe simple, sans correction de tendance : empilement de toutes les paires antérieures, puis recherche du paramétrage et projection sur tous les bâtiments.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import re
import sys
import csv
import glob
import gc
from datetime import datetime
import numpy as np
from config import COHERENCE, DONNEES

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

PILE_DIRS_40M = {
    'ASC': [
        os.path.join(COHERENCE, r"VENEZ\Methode BDPM\Full scene 40m\VEN_Caraballeda_ASC33_S1A_20260729T1604"),
        os.path.join(COHERENCE, r"VENEZ\Methode BDPM\Full scene 40m\VEN_Caraballeda_ASC33_S1C_20260729T1604"),
    ],
    'DESC': [
        os.path.join(COHERENCE, r"VENEZ\Methode BDPM\Full scene 40m\VEN_Caraballeda_DESC25_S1A_20260729T1604"),
        os.path.join(COHERENCE, r"VENEZ\Methode BDPM\Full scene 40m\VEN_Caraballeda_DESC25_S1C_20260729T1604"),
    ],
}
EARTHQUAKE_DATE = '20260624'
TARGET_RES_M = 30.0

BASE_OUT_DIR = os.path.join(DONNEES, r"VENEZUELA\DPM\DPM2")
WORK_DIR = os.path.join(BASE_OUT_DIR, "raster_cache_A")
OUT_RASTER_ASC = os.path.join(BASE_OUT_DIR, "dpm2_A_enveloppe_ASC_30m.tif")
OUT_RASTER_DESC = os.path.join(BASE_OUT_DIR, "dpm2_A_enveloppe_DESC_30m.tif")
OUT_CSV = os.path.join(BASE_OUT_DIR, "dpm2_A_enveloppe_resultats_complets.csv")
OUT_GPKG = os.path.join(BASE_OUT_DIR, "dpm2_A_enveloppe_couches_finales.gpkg")

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.1)]
DPM2_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.001, 0.02)]
WEIGHT_STEPS = [round(x, 1) for x in np.arange(0.0, 1.01, 0.1)]
SCORE_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.001, 0.02)]
RECALL_TARGETS = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]

SEP = "=" * 70

# =============================================================================
# HELPERS geographiques
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
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        if name in keep_names:
            out.setdefault(name, []).append(g2)
    ds = None
    unioned = {}
    for name, geoms in out.items():
        u = geoms[0]
        for g in geoms[1:]:
            u = u.Union(g)
        unioned[name] = u
    return unioned


def load_union_geom(path):
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
    print(f"  {len(out):,} batiment(s) Overture charge(s)")
    return out


def load_field_by_id(path, id_field, value_field, aoi_bounds):
    ds = ogr.Open(path)
    if ds is None:
        return {}
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for feat in lyr:
        out[feat.GetField(id_field)] = feat.GetField(value_field)
    ds = None
    return out


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
    f1 = (2 * precision * recall / (precision + recall)
          if (precision == precision and recall == recall and (precision + recall) > 0) else np.nan)
    po = (tp + tn) / n if n > 0 else np.nan
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
    return dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn, precision=precision, recall=recall, f1=f1, kappa=kappa)


def minmax_norm_fixed(arr, lo, hi):
    if hi <= lo:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def predict_weighted(vals_a, vals_b, minmax_a, minmax_b, w1, w2, thr):
    a_n = minmax_norm_fixed(vals_a, *minmax_a)
    b_n = minmax_norm_fixed(vals_b, *minmax_b)
    score = w1 * a_n + w2 * b_n
    return (score >= thr).astype(int)


def search_solo(y_true, vals, thresholds):
    best_kappa, best_f1 = None, None
    palier_results = {t: None for t in RECALL_TARGETS}
    for thr in thresholds:
        pred = (vals >= thr).astype(int)
        m = compute_metrics_np(y_true, pred)
        row = {'seuil': thr, **m}
        if m['kappa'] == m['kappa'] and (best_kappa is None or m['kappa'] > best_kappa['kappa']):
            best_kappa = row
        if m['f1'] == m['f1'] and (best_f1 is None or m['f1'] > best_f1['f1']):
            best_f1 = row
        if m['recall'] == m['recall']:
            for target in RECALL_TARGETS:
                if m['recall'] >= target:
                    if palier_results[target] is None or m['fp'] < palier_results[target]['fp']:
                        palier_results[target] = row
    return best_kappa, best_f1, palier_results


def search_and(y_true, vals_a, thr_a, vals_b, thr_b):
    best_kappa, best_f1 = None, None
    palier_results = {t: None for t in RECALL_TARGETS}
    for ta in thr_a:
        cond_a = vals_a >= ta
        for tb in thr_b:
            pred = (cond_a & (vals_b >= tb)).astype(int)
            m = compute_metrics_np(y_true, pred)
            row = {'seuil_a': ta, 'seuil_b': tb, **m}
            if m['kappa'] == m['kappa'] and (best_kappa is None or m['kappa'] > best_kappa['kappa']):
                best_kappa = row
            if m['f1'] == m['f1'] and (best_f1 is None or m['f1'] > best_f1['f1']):
                best_f1 = row
            if m['recall'] == m['recall']:
                for target in RECALL_TARGETS:
                    if m['recall'] >= target:
                        if palier_results[target] is None or m['fp'] < palier_results[target]['fp']:
                            palier_results[target] = row
    return best_kappa, best_f1, palier_results


def search_weighted(y_true, vals_a, vals_b, minmax_a, minmax_b):
    best_kappa, best_f1 = None, None
    palier_results = {t: None for t in RECALL_TARGETS}
    a_n = minmax_norm_fixed(vals_a, *minmax_a)
    b_n = minmax_norm_fixed(vals_b, *minmax_b)
    for w1 in WEIGHT_STEPS:
        w2 = round(1.0 - w1, 1)
        if w2 < 0:
            continue
        score = w1 * a_n + w2 * b_n
        for thr in SCORE_THRESHOLDS:
            pred = (score >= thr).astype(int)
            m = compute_metrics_np(y_true, pred)
            row = {'poids_a': w1, 'poids_b': w2, 'seuil_score': thr, **m}
            if m['kappa'] == m['kappa'] and (best_kappa is None or m['kappa'] > best_kappa['kappa']):
                best_kappa = row
            if m['f1'] == m['f1'] and (best_f1 is None or m['f1'] > best_f1['f1']):
                best_f1 = row
            if m['recall'] == m['recall']:
                for target in RECALL_TARGETS:
                    if m['recall'] >= target:
                        if palier_results[target] is None or m['fp'] < palier_results[target]['fp']:
                            palier_results[target] = row
    return best_kappa, best_f1, palier_results


DATE_PATTERN = re.compile(r'(\d{8})')


def parse_pairs_in_dir(pile_dir):
    tifs = sorted(glob.glob(os.path.join(pile_dir, '**', '*_corr.tif'), recursive=True))
    out = []
    for t in tifs:
        dates = DATE_PATTERN.findall(os.path.basename(t))
        if len(dates) < 2:
            continue
        try:
            dt1 = datetime.strptime(dates[0], '%Y%m%d')
            dt2 = datetime.strptime(dates[1], '%Y%m%d')
        except ValueError:
            continue
        eq_dt = datetime.strptime(EARTHQUAKE_DATE, '%Y%m%d')
        ptype = 'PRE' if dt2 < eq_dt else 'CO'
        out.append((t, dt1, dt2, ptype))
    return out


def get_ref_grid_30m(co_event_path, work_dir, cache_name):
    os.makedirs(work_dir, exist_ok=True)
    out_path = os.path.join(work_dir, cache_name)
    if os.path.exists(out_path) and os.path.getmtime(out_path) >= os.path.getmtime(co_event_path):
        ds = gdal.Open(out_path)
        gt = ds.GetGeoTransform()
        grid = dict(xmin=gt[0], ymax=gt[3], xres=gt[1], yres=gt[5],
                    xsize=ds.RasterXSize, ysize=ds.RasterYSize, srs_wkt=ds.GetProjection())
        ds = None
        return out_path, grid
    ds = gdal.Open(co_event_path)
    prj = ds.GetProjection()
    srs = osr.SpatialReference(); srs.ImportFromWkt(prj)
    dst_srs = prj if srs.IsProjected() else 'EPSG:32619'
    gdal.Warp(out_path, co_event_path, format='GTiff', dstSRS=dst_srs,
              xRes=TARGET_RES_M, yRes=TARGET_RES_M, resampleAlg=gdal.GRA_Bilinear)
    ds = None
    ds2 = gdal.Open(out_path)
    gt = ds2.GetGeoTransform()
    grid = dict(xmin=gt[0], ymax=gt[3], xres=gt[1], yres=gt[5],
                xsize=ds2.RasterXSize, ysize=ds2.RasterYSize, srs_wkt=ds2.GetProjection())
    ds2 = None
    return out_path, grid


def warp_to_ref_grid(src_path, grid, out_path):
    if os.path.exists(out_path) and os.path.getmtime(out_path) >= os.path.getmtime(src_path):
        return out_path
    xmin, ymax, xres, yres = grid['xmin'], grid['ymax'], grid['xres'], grid['yres']
    xmax = xmin + grid['xsize'] * xres
    ymin = ymax + grid['ysize'] * yres
    gdal.Warp(out_path, src_path, format='GTiff', dstSRS=grid['srs_wkt'],
              outputBounds=(xmin, ymin, xmax, ymax), width=grid['xsize'], height=grid['ysize'],
              resampleAlg=gdal.GRA_Bilinear)
    return out_path


def read_band_as_array(path):
    ds = gdal.Open(path)
    band = ds.GetRasterBand(1)
    nd = band.GetNoDataValue()
    arr = band.ReadAsArray().astype(np.float32)
    if nd is not None:
        arr[np.isclose(arr, nd)] = np.nan
    ds = None
    return arr


def write_array_as_raster(arr, grid, out_path):
    drv = gdal.GetDriverByName('GTiff')
    ds = drv.Create(out_path, grid['xsize'], grid['ysize'], 1, gdal.GDT_Float32)
    ds.SetGeoTransform((grid['xmin'], grid['xres'], 0, grid['ymax'], 0, grid['yres']))
    ds.SetProjection(grid['srs_wkt'])
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(-9999.0)
    band.WriteArray(np.where(np.isfinite(arr), arr, -9999.0).astype(np.float32))
    band.FlushCache()
    ds = None


def build_dpm2a_raster(orbite, dirs, work_dir, out_raster_path):
    print(f"\n{SEP}\n  ORBITE {orbite} — construction du raster DPM2 (Methode A)\n{SEP}")
    all_pairs = []
    for d in dirs:
        found = parse_pairs_in_dir(d)
        print(f"  {d} : {len(found)} fichier(s) date-parse (corr.tif uniquement)")
        all_pairs.extend(found)
    pre_pairs = [p for p in all_pairs if p[3] == 'PRE']
    co_pairs = [p for p in all_pairs if p[3] == 'CO']
    if len(pre_pairs) < 3 or not co_pairs:
        print(f"  [{orbite}] donnees insuffisantes — ignore")
        return None

    co_path = co_pairs[0][0]
    orbite_work_dir = os.path.join(work_dir, orbite)
    os.makedirs(orbite_work_dir, exist_ok=True)

    ref_raster_path, grid = get_ref_grid_30m(co_path, orbite_work_dir, 'grille_reference_30m.tif')
    co_warped = warp_to_ref_grid(co_path, grid, os.path.join(orbite_work_dir, 'co_event_aligne.tif'))
    co_arr = read_band_as_array(co_warped)

    print(f"  Reechantillonnage + cache des {len(pre_pairs)} paire(s) PRE...")
    pre_arrays = []
    for idx, (p, d1, d2, _) in enumerate(pre_pairs):
        cache_name = f'pre_{idx:03d}_{d1.strftime("%Y%m%d")}_{d2.strftime("%Y%m%d")}_aligne.tif'
        cache_path = os.path.join(orbite_work_dir, cache_name)
        warp_to_ref_grid(p, grid, cache_path)
        pre_arrays.append(read_band_as_array(cache_path))
        if (idx + 1) % 10 == 0 or (idx + 1) == len(pre_pairs):
            print(f"    {idx+1}/{len(pre_pairs)} paire(s) PRE traitee(s)")
        gc.collect()

    pre_stack = np.stack(pre_arrays, axis=0)
    del pre_arrays
    gc.collect()
    valid_count = np.sum(np.isfinite(pre_stack), axis=0).astype(np.float32)
    greater_count = np.nansum(pre_stack > co_arr[np.newaxis, :, :], axis=0).astype(np.float32)
    with np.errstate(invalid='ignore', divide='ignore'):
        idpm2_a = np.where(valid_count >= 3, greater_count / valid_count, np.nan)
    idpm2_a = np.where(np.isfinite(co_arr), idpm2_a, np.nan)

    write_array_as_raster(idpm2_a, grid, out_raster_path)
    print(f"  Raster DPM2_A ecrit : {out_raster_path}")
    return out_raster_path


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.makedirs(BASE_OUT_DIR, exist_ok=True)

    print(f"{SEP}\n  ETAPE 1 — Construction des rasters DPM2 (Methode A)\n{SEP}")
    raster_paths = {}
    raster_asc = build_dpm2a_raster('ASC', PILE_DIRS_40M['ASC'], WORK_DIR, OUT_RASTER_ASC)
    raster_desc = build_dpm2a_raster('DESC', PILE_DIRS_40M['DESC'], WORK_DIR, OUT_RASTER_DESC)
    if raster_asc:
        raster_paths['ASC'] = raster_asc
    if raster_desc:
        raster_paths['DESC'] = raster_desc

    print(f"\n{SEP}\n  ETAPE 2 — Recherche de parametrage contre EMS\n{SEP}")
    aoi_geom = load_union_geom(AOI_PATH)
    aoi_bounds = get_aoi_bounds(aoi_geom)
    zones = load_zones(AOI_PATH, AOI_ZONE_FIELD, ZONES_A_ETUDIER)
    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)
    ems_gt = load_field_by_id(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)

    all_ids = list(overture.keys())
    all_geoms = [overture[oid] for oid in all_ids]
    common_ids = [oid for oid in all_ids if oid in ems_gt]
    id_to_idx = {oid: i for i, oid in enumerate(all_ids)}
    calib_idx = np.array([id_to_idx[oid] for oid in common_ids])

    raw_classes = [ems_gt[oid] for oid in common_ids]
    y_true_calib = np.array([1 if r in ('Possibly damaged', 'Damaged', 'Destroyed') else (0 if r == 'not_reported' else np.nan)
                              for r in raw_classes])

    t_vals_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(T_TEST_RASTER, all_geoms)])
    minmax_t = (float(np.nanmin(t_vals_full)), float(np.nanmax(t_vals_full)))

    zone_of_building_full = np.array([None] * len(all_ids), dtype=object)
    for zone_name, zone_geom in zones.items():
        for i, g in enumerate(all_geoms):
            if zone_of_building_full[i] is None and zone_geom.Contains(g.Centroid()):
                zone_of_building_full[i] = zone_name
    mask_global_full = np.array([z in ZONES_A_ETUDIER for z in zone_of_building_full])

    rows = []
    best_params_global = {}

    for orbite, raster_path in raster_paths.items():
        print(f"\n  [{orbite}] extraction par batiment...")
        dpm2_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(raster_path, all_geoms)])
        minmax_dpm2 = (float(np.nanmin(dpm2_full)), float(np.nanmax(dpm2_full)))
        dpm2_calib = dpm2_full[calib_idx]
        t_calib = t_vals_full[calib_idx]

        def run_scope(scope_name, mask):
            yt = y_true_calib[mask]
            tv = t_calib[mask]
            dv = dpm2_calib[mask]
            valid = np.isfinite(yt) & np.isfinite(dv)
            n_pos = int(np.nansum(yt[valid])) if valid.sum() else 0
            print(f"    {scope_name} (n={int(valid.sum())}, positifs={n_pos})")
            if valid.sum() < 20 or n_pos == 0:
                return

            yv = yt[valid].astype(int)
            bk, bf1, paliers = search_solo(yv, dv[valid], DPM2_THRESHOLDS)
            if bk:
                rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'dpm2A_seul', 'critere': 'kappa', **bk})
                print(f"      dpm2A_seul kappa  : seuil={bk['seuil']}  kappa={bk['kappa']:.3f}")
            if bf1:
                rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'dpm2A_seul', 'critere': 'f1', **bf1})
            for target, r in paliers.items():
                if r:
                    rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'dpm2A_seul',
                                  'critere': f'rappel_{int(target*100)}pct', **r})

            valid_tv = valid & np.isfinite(tv)
            yv2 = yt[valid_tv].astype(int)
            bk_et, bf1_et, paliers_et = search_and(yv2, tv[valid_tv], T_TEST_THRESHOLDS, dv[valid_tv], DPM2_THRESHOLDS)
            if bk_et:
                rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm2A_ET', 'critere': 'kappa', **bk_et})
                print(f"      fusion_ET kappa   : kappa={bk_et['kappa']:.3f}")
                if scope_name == 'global':
                    best_params_global[(orbite, 'ET')] = ('and', bk_et['seuil_a'], bk_et['seuil_b'])
            if bf1_et:
                rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm2A_ET', 'critere': 'f1', **bf1_et})
            for target, r in paliers_et.items():
                if r:
                    rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm2A_ET',
                                  'critere': f'rappel_{int(target*100)}pct', **r})

            bk_w, bf1_w, paliers_w = search_weighted(yv2, tv[valid_tv], dv[valid_tv], minmax_t, minmax_dpm2)
            if bk_w:
                rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm2A_pondere', 'critere': 'kappa', **bk_w})
                print(f"      fusion_pondere kappa : kappa={bk_w['kappa']:.3f}")
                if scope_name == 'global':
                    best_params_global[(orbite, 'pondere')] = ('weighted', bk_w['poids_a'], bk_w['poids_b'], bk_w['seuil_score'])
            if bf1_w:
                rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm2A_pondere', 'critere': 'f1', **bf1_w})
            for target, r in paliers_w.items():
                if r:
                    rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm2A_pondere',
                                  'critere': f'rappel_{int(target*100)}pct', **r})

            if scope_name == 'global' and bk:
                best_params_global[(orbite, 'seul')] = ('solo', bk['seuil'])

        run_scope('global', mask_global_full[calib_idx])
        for zn in zones:
            run_scope(f'zone_{zn}', zone_of_building_full[calib_idx] == zn)

    fieldnames = ['orbite', 'portee', 'methode', 'critere', 'seuil', 'seuil_a', 'seuil_b',
                  'poids_a', 'poids_b', 'seuil_score', 'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\nEcrit : {OUT_CSV}")

    print(f"\n{SEP}\n  ETAPE 3 — Projection sur tous les batiments Overture\n{SEP}")
    drv = ogr.GetDriverByName('GPKG')
    if os.path.exists(OUT_GPKG):
        drv.DeleteDataSource(OUT_GPKG)
    ds_out = drv.CreateDataSource(OUT_GPKG)
    srs_out = osr.SpatialReference(); srs_out.ImportFromEPSG(4326)

    for orbite, raster_path in raster_paths.items():
        dpm2_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(raster_path, all_geoms)])
        minmax_dpm2 = (float(np.nanmin(dpm2_full)), float(np.nanmax(dpm2_full)))

        for method_name in ('seul', 'ET', 'pondere'):
            key = (orbite, method_name)
            if key not in best_params_global:
                continue
            param = best_params_global[key]
            layer_name = f"dpm2A_{orbite.lower()}_{method_name}"
            lyr = ds_out.CreateLayer(layer_name, srs=srs_out, geom_type=ogr.wkbUnknown)
            lyr.CreateField(ogr.FieldDefn('overture_id', ogr.OFTString))
            lyr.CreateField(ogr.FieldDefn('zone', ogr.OFTString))
            lyr.CreateField(ogr.FieldDefn('damaged', ogr.OFTInteger))
            lyr.CreateField(ogr.FieldDefn('t_test_val', ogr.OFTReal))
            lyr.CreateField(ogr.FieldDefn('dpm2_val', ogr.OFTReal))
            if param[0] == 'solo':
                lyr.CreateField(ogr.FieldDefn('seuil', ogr.OFTReal))
            elif param[0] == 'and':
                lyr.CreateField(ogr.FieldDefn('seuil_a', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('seuil_b', ogr.OFTReal))
            else:
                lyr.CreateField(ogr.FieldDefn('poids_a', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('poids_b', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('seuil_score', ogr.OFTReal))

            n_written = 0
            for i in range(len(all_ids)):
                dval, tval = dpm2_full[i], t_vals_full[i]
                if param[0] == 'solo':
                    if not np.isfinite(dval):
                        continue
                    damaged = int(dval >= param[1])
                elif param[0] == 'and':
                    if not (np.isfinite(dval) and np.isfinite(tval)):
                        continue
                    damaged = int((tval >= param[1]) and (dval >= param[2]))
                else:
                    if not (np.isfinite(dval) and np.isfinite(tval)):
                        continue
                    damaged = int(predict_weighted(np.array([tval]), np.array([dval]), minmax_t, minmax_dpm2,
                                                    param[1], param[2], param[3])[0])
                of = ogr.Feature(lyr.GetLayerDefn())
                of.SetGeometry(all_geoms[i])
                of.SetField('overture_id', str(all_ids[i]))
                if zone_of_building_full[i] is not None:
                    of.SetField('zone', str(zone_of_building_full[i]))
                of.SetField('damaged', damaged)
                if np.isfinite(tval):
                    of.SetField('t_test_val', float(tval))
                if np.isfinite(dval):
                    of.SetField('dpm2_val', float(dval))
                if param[0] == 'solo':
                    of.SetField('seuil', float(param[1]))
                elif param[0] == 'and':
                    of.SetField('seuil_a', float(param[1])); of.SetField('seuil_b', float(param[2]))
                else:
                    of.SetField('poids_a', float(param[1])); of.SetField('poids_b', float(param[2]))
                    of.SetField('seuil_score', float(param[3]))
                lyr.CreateFeature(of)
                n_written += 1
            print(f"  couche {layer_name} : {n_written:,} batiment(s)")

    ds_out = None
    print(f"\n{SEP}\nTermine — {OUT_GPKG}\n{SEP}")


if __name__ == '__main__':
    main()
