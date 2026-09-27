# -*- coding: utf-8 -*-
"""Reproduction de la première méthode de cohérence publiée, calculée en parallèle sur deux résolutions — traitement par rafales à 20 m et scène entière à 40 m rééchantillonnée à 30 m — pour mesurer l'effet de la résolution sur le classement.

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

# --- Version BURST 20m ---
COEVENT_ASC_PATH_20M = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst\mosaic_asc.tif")
COEVENT_DESC_PATH_20M = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst\mosaic_desc.tif")
PRE_ASC_DIR_20M = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\burst Cariballada_20m\PRE\ASC_tiff")
PRE_DESC_DIR_20M = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\burst Cariballada_20m\PRE\DESC_tiff")
MOSAIC_CACHE_DIR = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst")

# --- Version FULL-SCENE 40m -> reechantillonnee 30m ---
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
RESAMPLE_CACHE_DIR = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\reech_30m")
TARGET_RES_M = 30.0

EARTHQUAKE_DATE = '20260624'  # YYYYMMDD

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.1)]
DIFF_THRESHOLDS = [round(x, 3) for x in np.arange(-0.5, 0.51, 0.02)]
WEIGHT_STEPS = [round(x, 1) for x in np.arange(0.0, 1.01, 0.1)]
SCORE_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.001, 0.02)]

OUT_CSV_BURST = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\dpm1_burst_20m_resultats.csv")
OUT_CSV_FULLSCENE = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\dpm1_fullscene_40mto30m_resultats.csv")

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


def build_mosaic_if_needed(burst_dir, cache_dir, cache_name):
    os.makedirs(cache_dir, exist_ok=True)
    out_path = os.path.join(cache_dir, cache_name)
    tifs = sorted(glob.glob(os.path.join(burst_dir, '**', '*.tif'), recursive=True))
    if not tifs:
        print(f"  ATTENTION — aucun .tif trouve dans {burst_dir}")
        return None, 0
    if os.path.exists(out_path):
        newest_src = max(os.path.getmtime(t) for t in tifs)
        if os.path.getmtime(out_path) >= newest_src:
            print(f"  Mosaique en cache (a jour) : {out_path} ({len(tifs)} tuile(s) source)")
            return out_path, len(tifs)
    print(f"  Construction de la mosaique ({len(tifs)} tuile(s)) -> {out_path}")
    gdal.Warp(out_path, tifs, format='GTiff', resampleAlg=gdal.GRA_NearestNeighbour)
    return out_path, len(tifs)


def resample_to_30m(src_path, cache_dir, cache_name):
    """Reechantillonnage (interpolation bilineaire) du natif 40m vers
    une grille cible ~30m. PAS un regeocodage — le geocodage (avec DEM
    SRTM/Copernicus) est deja fait par ASF/HyP3 en amont ; on change
    seulement l'espacement de pixel."""
    os.makedirs(cache_dir, exist_ok=True)
    out_path = os.path.join(cache_dir, cache_name)
    if os.path.exists(out_path) and os.path.getmtime(out_path) >= os.path.getmtime(src_path):
        return out_path
    ds = gdal.Open(src_path)
    prj = ds.GetProjection()
    srs = osr.SpatialReference(); srs.ImportFromWkt(prj)
    if srs.IsProjected():
        gdal.Warp(out_path, src_path, format='GTiff', xRes=TARGET_RES_M, yRes=TARGET_RES_M,
                  resampleAlg=gdal.GRA_Bilinear)
    else:
        gdal.Warp(out_path, src_path, format='GTiff', dstSRS='EPSG:32619',
                  xRes=TARGET_RES_M, yRes=TARGET_RES_M, resampleAlg=gdal.GRA_Bilinear)
    ds = None
    return out_path


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
    po = (tp + tn) / n if n > 0 else np.nan
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
    return dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn, precision=precision, recall=recall, kappa=kappa)


def minmax_norm(arr):
    valid = arr[np.isfinite(arr)]
    if len(valid) == 0:
        return arr
    lo, hi = np.min(valid), np.max(valid)
    if hi <= lo:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def find_best_solo(y_true, vals, thresholds, direction):
    best = None
    for thr in thresholds:
        pred = ((vals >= thr) if direction == 'ge' else (vals <= thr)).astype(int)
        m = compute_metrics_np(y_true, pred)
        if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
            best = {'seuil': thr, **m}
    return best


def find_best_and_fusion(y_true, vals_a, thr_a, vals_b, thr_b):
    best = None
    for ta in thr_a:
        cond_a = vals_a >= ta
        for tb in thr_b:
            cond_b = vals_b >= tb
            pred = (cond_a & cond_b).astype(int)
            m = compute_metrics_np(y_true, pred)
            if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
                best = {'seuil_a': ta, 'seuil_b': tb, **m}
    return best


def find_best_weighted(y_true, vals_a, vals_b):
    a_n = minmax_norm(vals_a)
    b_n = minmax_norm(vals_b)
    best = None
    for w1 in WEIGHT_STEPS:
        w2 = round(1.0 - w1, 1)
        if w2 < 0:
            continue
        score = w1 * a_n + w2 * b_n
        for thr in SCORE_THRESHOLDS:
            pred = (score >= thr).astype(int)
            m = compute_metrics_np(y_true, pred)
            if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
                best = {'poids_a': w1, 'poids_b': w2, 'seuil_score': thr, **m}
    return best


DATE_PATTERN = re.compile(r'(\d{8})')


def parse_pairs_in_dir(pile_dir):
    tifs = sorted(glob.glob(os.path.join(pile_dir, '**', '*.tif'), recursive=True))
    out = []
    for t in tifs:
        dates = DATE_PATTERN.findall(os.path.basename(t))
        if len(dates) < 2:
            continue
        d1, d2 = dates[0], dates[1]
        try:
            dt1 = datetime.strptime(d1, '%Y%m%d')
            dt2 = datetime.strptime(d2, '%Y%m%d')
        except ValueError:
            continue
        eq_dt = datetime.strptime(EARTHQUAKE_DATE, '%Y%m%d')
        ptype = 'PRE' if dt2 < eq_dt else 'CO'
        out.append((t, dt1, dt2, ptype))
    return out


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"{SEP}\n  Chargement AOI, zones, batiments, verite terrain\n{SEP}")
    aoi_geom = load_union_geom(AOI_PATH)
    aoi_bounds = get_aoi_bounds(aoi_geom)
    zones = load_zones(AOI_PATH, AOI_ZONE_FIELD, ZONES_A_ETUDIER)

    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)
    ems_gt = load_field_by_id(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)

    common_ids = list(set(overture.keys()) & set(ems_gt.keys()))
    print(f"  {len(common_ids):,} batiment(s) en commun (Overture + EMS)")
    geoms = [overture[oid] for oid in common_ids]
    raw_classes = [ems_gt[oid] for oid in common_ids]
    y_true_all = np.array([1 if r in ('Possibly damaged', 'Damaged', 'Destroyed') else (0 if r == 'not_reported' else np.nan)
                            for r in raw_classes])

    print(f"\n{SEP}\n  T-stat par batiment\n{SEP}")
    t_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(T_TEST_RASTER, geoms)])

    zone_of_building = np.array([None] * len(common_ids), dtype=object)
    for zone_name, zone_geom in zones.items():
        for i, g in enumerate(geoms):
            if zone_of_building[i] is None and zone_geom.Contains(g.Centroid()):
                zone_of_building[i] = zone_name

    def evaluate_and_write(diff_by_orbite, out_path, label):
        rows = []
        for orbite, diff_vals in diff_by_orbite.items():
            def run_scope(scope_name, mask):
                yt = y_true_all[mask]
                tv = t_vals[mask]
                dv = diff_vals[mask]
                valid_base = np.isfinite(yt)
                n_pos = int(np.nansum(yt[valid_base])) if valid_base.sum() else 0
                print(f"    [{orbite}] {scope_name} (n={int(valid_base.sum())}, positifs={n_pos})")

                v = valid_base & np.isfinite(dv)
                if v.sum() >= 20 and yt[v].sum() > 0:
                    b = find_best_solo(yt[v].astype(int), dv[v], DIFF_THRESHOLDS, 'ge')
                    if b:
                        rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'dpm1_seul',
                                      'seuil_a': b['seuil'], 'seuil_b': None, 'poids_a': None, 'poids_b': None,
                                      **{k: b[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                        print(f"      dpm1_seul : seuil={b['seuil']}  kappa={b['kappa']:.3f}")

                v = valid_base & np.isfinite(tv) & np.isfinite(dv)
                if v.sum() >= 20 and yt[v].sum() > 0:
                    yv = yt[v].astype(int)
                    b_et = find_best_and_fusion(yv, tv[v], T_TEST_THRESHOLDS, dv[v], DIFF_THRESHOLDS)
                    if b_et:
                        rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm1_ET',
                                      'seuil_a': b_et['seuil_a'], 'seuil_b': b_et['seuil_b'], 'poids_a': None, 'poids_b': None,
                                      **{k: b_et[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                        print(f"      fusion_ET : kappa={b_et['kappa']:.3f}")
                    b_w = find_best_weighted(yv, tv[v], dv[v])
                    if b_w:
                        rows.append({'orbite': orbite, 'portee': scope_name, 'methode': 'fusion_tstat_dpm1_pondere',
                                      'seuil_a': None, 'seuil_b': None, 'poids_a': b_w['poids_a'], 'poids_b': b_w['poids_b'],
                                      'seuil_score': b_w['seuil_score'],
                                      **{k: b_w[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                        print(f"      fusion_pondere : kappa={b_w['kappa']:.3f}")

            mask_global = np.array([z in ZONES_A_ETUDIER for z in zone_of_building])
            run_scope('global', mask_global)
            for zn in zones:
                run_scope(f'zone_{zn}', zone_of_building == zn)

        fieldnames = ['orbite', 'portee', 'methode', 'seuil_a', 'seuil_b', 'poids_a', 'poids_b', 'seuil_score',
                      'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa']
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fieldnames})
        print(f"\nEcrit ({label}) : {out_path}")

    # =========================================================================
    # VERSION BURST 20m
    # =========================================================================
    print(f"\n{SEP}\n  VERSION BURST 20m\n{SEP}")
    pre_asc_20m, n1 = build_mosaic_if_needed(PRE_ASC_DIR_20M, MOSAIC_CACHE_DIR, 'mosaic_pre_asc.tif')
    pre_desc_20m, n2 = build_mosaic_if_needed(PRE_DESC_DIR_20M, MOSAIC_CACHE_DIR, 'mosaic_pre_desc.tif')
    print(f"  PRE ASC: {n1} tuile(s)   PRE DESC: {n2} tuile(s)")

    diff_by_orbite_burst = {}
    for orbite, pre_path, co_path in (('ASC', pre_asc_20m, COEVENT_ASC_PATH_20M),
                                       ('DESC', pre_desc_20m, COEVENT_DESC_PATH_20M)):
        if pre_path is None or not os.path.exists(co_path):
            print(f"  [{orbite}] donnees manquantes — ignore")
            continue
        pre_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(pre_path, geoms)])
        gc.collect()
        co_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(co_path, geoms)])
        gc.collect()
        diff_by_orbite_burst[orbite] = pre_vals - co_vals
        print(f"  [{orbite}] DPM1 burst 20m calcule — {np.isfinite(diff_by_orbite_burst[orbite]).sum():,} batiment(s)")

    print(f"\n  Evaluation version BURST 20m...")
    evaluate_and_write(diff_by_orbite_burst, OUT_CSV_BURST, 'burst 20m')

    # =========================================================================
    # VERSION FULL-SCENE 40m -> 30m
    # =========================================================================
    print(f"\n{SEP}\n  VERSION FULL-SCENE 40m -> reechantillonnee 30m\n{SEP}")

    diff_by_orbite_fs = {}
    for orbite, dirs in PILE_DIRS_40M.items():
        print(f"\n  Orbite {orbite} :")
        all_pairs = []
        for d in dirs:
            found = parse_pairs_in_dir(d)
            print(f"    {d} : {len(found)} fichier(s) date-parse")
            all_pairs.extend(found)

        pre_pairs = sorted([p for p in all_pairs if p[3] == 'PRE'], key=lambda p: p[2])
        co_pairs = [p for p in all_pairs if p[3] == 'CO']
        if not pre_pairs or not co_pairs:
            print(f"    [{orbite}] paires PRE ou CO-event manquantes — ignore")
            continue

        pre_path, pre_d1, pre_d2, _ = pre_pairs[-1]
        co_path, co_d1, co_d2, _ = co_pairs[0]
        print(f"    PRE retenue : {os.path.basename(pre_path)} ({pre_d1.date()}->{pre_d2.date()})")
        print(f"    CO retenue  : {os.path.basename(co_path)} ({co_d1.date()}->{co_d2.date()})")

        pre_30m = resample_to_30m(pre_path, RESAMPLE_CACHE_DIR, f'pre_{orbite}_30m.tif')
        co_30m = resample_to_30m(co_path, RESAMPLE_CACHE_DIR, f'co_{orbite}_30m.tif')

        pre_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(pre_30m, geoms)])
        gc.collect()
        co_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(co_30m, geoms)])
        gc.collect()
        diff_by_orbite_fs[orbite] = pre_vals - co_vals
        print(f"    [{orbite}] DPM1 full-scene 30m calcule — {np.isfinite(diff_by_orbite_fs[orbite]).sum():,} batiment(s)")

    print(f"\n  Evaluation version FULL-SCENE 40m->30m...")
    evaluate_and_write(diff_by_orbite_fs, OUT_CSV_FULLSCENE, 'full-scene 40m->30m')


if __name__ == '__main__':
    main()
