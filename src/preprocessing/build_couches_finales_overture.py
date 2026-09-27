# -*- coding: utf-8 -*-
"""Documente le seuil et les poids retenus pour chaque combinaison de méthode et de portée, puis projette ces paramètres sur l'ensemble des bâtiments pour produire les couches finales.

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
EOS_ON_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg")
EOS_ID_FIELD = "overture_id"
EOS_VALUE_FIELD = "raster_max"

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.1)]
BDPM_THRESHOLDS = [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)]
BURST_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.01, 0.02)]
WEIGHT_STEPS = [round(x, 1) for x in np.arange(0.0, 1.01, 0.1)]
SCORE_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.001, 0.02)]

OUT_CSV_REF = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\reference_parametres.csv")
OUT_GPKG = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\couches_finales_overture.gpkg")

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


def find_best_and_fusion(y_true, vals_a, thr_a, vals_b, thr_b, dir_b):
    best = None
    for ta in thr_a:
        cond_a = vals_a >= ta
        for tb in thr_b:
            cond_b = (vals_b >= tb) if dir_b == 'ge' else (vals_b <= tb)
            pred = (cond_a & cond_b).astype(int)
            m = compute_metrics_np(y_true, pred)
            if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
                best = {'seuil_a': ta, 'seuil_b': tb, **m}
    return best


def scale_with_fixed_minmax(arr, lo, hi):
    """Normalisation avec un min/max FIXE (celui de la POPULATION
    COMPLETE, pas recalcule sur le sous-ensemble en cours) — necessaire
    pour que la normalisation apprise pendant la calibration reste
    valable sur un batiment quelconque plus tard, meme un seul a la
    fois, meme sans verite terrain."""
    if hi <= lo:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def find_best_weighted(y_true, vals_a, vals_b, dir_b, minmax_a, minmax_b):
    a_n = scale_with_fixed_minmax(vals_a, *minmax_a)
    b_n = scale_with_fixed_minmax(vals_b, *minmax_b)
    if dir_b == 'le':
        b_n = 1.0 - b_n
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
    eos_raw = load_field_by_id(EOS_ON_OVERTURE_PATH, EOS_ID_FIELD, EOS_VALUE_FIELD, aoi_bounds)

    # TOUS les batiments Overture de l'AOI — c'est LA POPULATION DE
    # REFERENCE pour la normalisation (min/max), pas seulement ceux avec
    # verite terrain : en usage reel, on n'a PAS de verite terrain, donc
    # la normalisation doit etre valable sur n'importe quel batiment,
    # pas seulement le sous-ensemble ayant servi a calibrer.
    all_ids = list(overture.keys())
    all_geoms = [overture[oid] for oid in all_ids]
    print(f"  {len(all_ids):,} batiment(s) Overture au TOTAL dans l'AOI")

    print(f"\n{SEP}\n  Calcul T-stat/BDPM/burst/EOS sur TOUS les batiments (population complete)\n{SEP}")
    t_vals_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(T_TEST_RASTER, all_geoms)])
    bdpm_vals_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(BDPM_RASTER, all_geoms)])
    asc_vals_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(BURST_MOSAIC_PATH_ASC, all_geoms)])
    desc_vals_full = np.array([v if v is not None else np.nan for v in compute_max_per_building(BURST_MOSAIC_PATH_DESC, all_geoms)])
    burst_vals_full = np.nanmean(np.vstack([asc_vals_full, desc_vals_full]), axis=0)
    eos_vals_full = np.array([eos_raw.get(oid) if eos_raw.get(oid) is not None else np.nan for oid in all_ids])

    # Min/max de la POPULATION COMPLETE — figes une fois pour toutes,
    # reutilises PARTOUT (calibration ET application), jamais recalcules
    # sur un sous-ensemble ni sur un seul batiment.
    def population_minmax(arr):
        valid = arr[np.isfinite(arr)]
        return (float(np.min(valid)), float(np.max(valid))) if len(valid) else (0.0, 1.0)

    minmax_t = population_minmax(t_vals_full)
    minmax_bdpm = population_minmax(bdpm_vals_full)
    minmax_burst = population_minmax(burst_vals_full)
    minmax_eos = population_minmax(eos_vals_full)
    print(f"  min/max population — t_test:{minmax_t}  bdpm:{minmax_bdpm}  "
          f"burst:{minmax_burst}  eos:{minmax_eos}")

    id_to_idx = {oid: i for i, oid in enumerate(all_ids)}

    print(f"\n{SEP}\n  Extraction du sous-ensemble CALIBRATION (Overture + EMS)\n{SEP}")
    common_ids = [oid for oid in all_ids if oid in ems_gt]
    print(f"  {len(common_ids):,} batiment(s) avec verite terrain (pour calibrer les seuils)")
    calib_idx = np.array([id_to_idx[oid] for oid in common_ids])
    geoms = [all_geoms[i] for i in calib_idx]
    raw_classes = [ems_gt[oid] for oid in common_ids]
    # PD_endommage — Possibly damaged compte comme endommage (pas exclu)
    y_true_all = np.array([1 if r in ('Possibly damaged', 'Damaged', 'Destroyed') else (0 if r == 'not_reported' else np.nan)
                            for r in raw_classes])

    t_vals_all = t_vals_full[calib_idx]
    bdpm_vals_all = bdpm_vals_full[calib_idx]
    burst_vals_all = burst_vals_full[calib_idx]
    eos_vals_all = eos_vals_full[calib_idx]

    zone_of_building_full = np.array([None] * len(all_ids), dtype=object)
    for zone_name, zone_geom in zones.items():
        for i, g in enumerate(all_geoms):
            if zone_of_building_full[i] is None and zone_geom.Contains(g.Centroid()):
                zone_of_building_full[i] = zone_name
    zone_of_building = zone_of_building_full[calib_idx]

    ref_rows = []

    def run_scope(scope_name, mask):
        yt = y_true_all[mask]
        tv = t_vals_all[mask]
        bv = bdpm_vals_all[mask]
        bu = burst_vals_all[mask]
        ev = eos_vals_all[mask]
        valid_base = np.isfinite(yt)

        results = {}

        v = valid_base & np.isfinite(tv)
        if v.sum() >= 20 and yt[v].sum() > 0:
            best = find_best_solo(yt[v].astype(int), tv[v], T_TEST_THRESHOLDS, 'ge')
            if best:
                ref_rows.append({'portee': scope_name, 'methode': 't_test_seul', 'seuil_a': best['seuil'],
                                  'seuil_b': None, 'poids_a': None, 'poids_b': None, **{k: best[k] for k in
                                  ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                results['t_test_seul'] = ('solo', best['seuil'], None, 'ge')

        v = valid_base & np.isfinite(bv)
        if v.sum() >= 20 and yt[v].sum() > 0:
            best = find_best_solo(yt[v].astype(int), bv[v], BDPM_THRESHOLDS, 'ge')
            if best:
                ref_rows.append({'portee': scope_name, 'methode': 'bdpm_seul', 'seuil_a': best['seuil'],
                                  'seuil_b': None, 'poids_a': None, 'poids_b': None, **{k: best[k] for k in
                                  ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                results['bdpm_seul'] = ('solo', best['seuil'], None, 'ge')

        v = valid_base & np.isfinite(tv) & np.isfinite(bu)
        if v.sum() >= 20 and yt[v].sum() > 0:
            yv = yt[v].astype(int)
            best_et = find_best_and_fusion(yv, tv[v], T_TEST_THRESHOLDS, bu[v], BURST_THRESHOLDS, 'le')
            if best_et:
                ref_rows.append({'portee': scope_name, 'methode': 'fusion_coevent_ET', 'seuil_a': best_et['seuil_a'],
                                  'seuil_b': best_et['seuil_b'], 'poids_a': None, 'poids_b': None,
                                  **{k: best_et[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                results['fusion_coevent_ET'] = ('and', best_et['seuil_a'], best_et['seuil_b'], 'le')
            best_w = find_best_weighted(yv, tv[v], bu[v], 'le', minmax_t, minmax_burst)
            if best_w:
                ref_rows.append({'portee': scope_name, 'methode': 'fusion_coevent_pondere', 'seuil_a': None,
                                  'seuil_b': None, 'poids_a': best_w['poids_a'], 'poids_b': best_w['poids_b'],
                                  'seuil_score': best_w['seuil_score'],
                                  **{k: best_w[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                results['fusion_coevent_pondere'] = ('weighted', best_w['poids_a'], best_w['poids_b'],
                                                       best_w['seuil_score'], 'le', minmax_t, minmax_burst)

        v = valid_base & np.isfinite(tv) & np.isfinite(ev)
        if v.sum() >= 20 and yt[v].sum() > 0:
            yv = yt[v].astype(int)
            eos_thr = [round(x, 3) for x in np.linspace(np.nanmin(ev[v]), np.nanmax(ev[v]), 40)]
            best_et = find_best_and_fusion(yv, tv[v], T_TEST_THRESHOLDS, ev[v], eos_thr, 'ge')
            if best_et:
                ref_rows.append({'portee': scope_name, 'methode': 'fusion_eos_ET', 'seuil_a': best_et['seuil_a'],
                                  'seuil_b': best_et['seuil_b'], 'poids_a': None, 'poids_b': None,
                                  **{k: best_et[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                results['fusion_eos_ET'] = ('and', best_et['seuil_a'], best_et['seuil_b'], 'ge')
            best_w = find_best_weighted(yv, tv[v], ev[v], 'ge', minmax_t, minmax_eos)
            if best_w:
                ref_rows.append({'portee': scope_name, 'methode': 'fusion_eos_pondere', 'seuil_a': None,
                                  'seuil_b': None, 'poids_a': best_w['poids_a'], 'poids_b': best_w['poids_b'],
                                  'seuil_score': best_w['seuil_score'],
                                  **{k: best_w[k] for k in ('n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa')}})
                results['fusion_eos_pondere'] = ('weighted', best_w['poids_a'], best_w['poids_b'],
                                                  best_w['seuil_score'], 'ge', minmax_t, minmax_eos)
        return results

    print(f"\n{SEP}\n  Calcul GLOBAL\n{SEP}")
    # 'global' = restreint aux 3 zones etudiees (Caraballeda/Catia la
    # Mar/La Guaira), PAS toute l'AOI CEMS — Caracas/Moron/San Felipe ont
    # un signal quasi nul et fausseraient l'optimum si inclus (deja
    # constate dans les analyses precedentes).
    mask_global = np.array([z in ZONES_A_ETUDIER for z in zone_of_building])
    params_global = run_scope('global', mask_global)
    for k, v in params_global.items():
        print(f"  {k:25s} : {v}")

    params_par_zone = {}
    for zone_name in zones:
        print(f"\n{SEP}\n  Calcul ZONE : {zone_name}\n{SEP}")
        mask_zone = (zone_of_building == zone_name)
        params_par_zone[zone_name] = run_scope(f'zone_{zone_name}', mask_zone)
        for k, v in params_par_zone[zone_name].items():
            print(f"  {k:25s} : {v}")

    os.makedirs(os.path.dirname(OUT_CSV_REF), exist_ok=True)
    with open(OUT_CSV_REF, 'w', newline='', encoding='utf-8') as f:
        f.write(f"# min/max de POPULATION utilises pour toute normalisation ponderee "
                f"(figes sur TOUS les batiments Overture de l'AOI, pas seulement ceux avec verite terrain)\n")
        f.write(f"# t_test: {minmax_t}  bdpm: {minmax_bdpm}  burst_moyenne: {minmax_burst}  eos_raster_max: {minmax_eos}\n")
        fieldnames = ['portee', 'methode', 'seuil_a', 'seuil_b', 'poids_a', 'poids_b', 'seuil_score',
                      'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in ref_rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV_REF}\n{SEP}")

    # =========================================================================
    # VOLET B — UNE COUCHE SEPAREE par (methode x portee) — 12 au total.
    # Chaque couche contient, en plus du champ 'damaged' (0/1) :
    #   - la ou les valeurs brutes utilisees pour ce calcul
    #   - les PARAMETRES REELS utilises pour CHAQUE batiment (seuil pour
    #     les methodes seules/ET, poids+seuil+min/max pour les ponderees)
    #     — pour une portee 'parzone', ces valeurs different reellement
    #     d'une ligne a l'autre selon la zone du batiment ; pour 'global',
    #     elles sont identiques partout (repetees, mais explicites).
    # =========================================================================
    print(f"\n{SEP}\n  Ecriture d'une couche separee par methode\n{SEP}")

    def apply_param(param, val_a, val_b):
        kind = param[0]
        if kind == 'and':
            _, sa, sb, dir_b = param
            cond_a = val_a >= sa
            cond_b = (val_b >= sb) if dir_b == 'ge' else (val_b <= sb)
            return int(cond_a and cond_b)
        elif kind == 'weighted':
            _, w1, w2, sthr, dir_b, minmax_a, minmax_b = param
            a_n = scale_with_fixed_minmax(np.array([val_a]), *minmax_a)[0]
            b_n = scale_with_fixed_minmax(np.array([val_b]), *minmax_b)[0]
            if dir_b == 'le':
                b_n = 1.0 - b_n
            score = w1 * a_n + w2 * b_n
            return int(score >= sthr)
        return None

    value_arrays = {'t_test': t_vals_full, 'bdpm': bdpm_vals_full, 'burst': burst_vals_full, 'eos': eos_vals_full}
    value_field_names = {'t_test': 't_test_val', 'bdpm': 'bdpm_val', 'burst': 'burst_moyenne_val', 'eos': 'eos_raster_max_val'}

    method_configs = {
        't_test_seul': ['t_test'],
        'bdpm_seul': ['bdpm'],
        'fusion_coevent_ET': ['t_test', 'burst'],
        'fusion_coevent_pondere': ['t_test', 'burst'],
        'fusion_eos_ET': ['t_test', 'eos'],
        'fusion_eos_pondere': ['t_test', 'eos'],
    }

    drv = ogr.GetDriverByName('GPKG')
    if os.path.exists(OUT_GPKG):
        drv.DeleteDataSource(OUT_GPKG)
    ds_out = drv.CreateDataSource(OUT_GPKG)
    srs_out = osr.SpatialReference(); srs_out.ImportFromEPSG(4326)

    for method_key, val_names in method_configs.items():
        for scope in ('global', 'parzone'):
            layer_name = f"{method_key}_{scope}"
            print(f"  Couche : {layer_name}")
            lyr = ds_out.CreateLayer(layer_name, srs=srs_out, geom_type=ogr.wkbUnknown)
            lyr.CreateField(ogr.FieldDefn('overture_id', ogr.OFTString))
            lyr.CreateField(ogr.FieldDefn('zone', ogr.OFTString))
            lyr.CreateField(ogr.FieldDefn('damaged', ogr.OFTInteger))
            for vn in val_names:
                lyr.CreateField(ogr.FieldDefn(value_field_names[vn], ogr.OFTReal))

            # Champs de PARAMETRES — dependent du type de methode (solo/and/weighted)
            sample_param = params_global.get(method_key) if scope == 'global' else None
            if sample_param is None and scope == 'parzone':
                for pz in params_par_zone.values():
                    if method_key in pz:
                        sample_param = pz[method_key]
                        break
            if sample_param is None:
                print(f"    (aucun parametre trouve pour {method_key}/{scope} — couche vide ignoree)")
                continue
            kind = sample_param[0]
            if kind == 'solo':
                lyr.CreateField(ogr.FieldDefn('seuil', ogr.OFTReal))
            elif kind == 'and':
                lyr.CreateField(ogr.FieldDefn('seuil_a', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('seuil_b', ogr.OFTReal))
            elif kind == 'weighted':
                lyr.CreateField(ogr.FieldDefn('poids_a', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('poids_b', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('seuil_score', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('min_a', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('max_a', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('min_b', ogr.OFTReal))
                lyr.CreateField(ogr.FieldDefn('max_b', ogr.OFTReal))

            n_written = 0
            for i, oid in enumerate(all_ids):
                z = zone_of_building_full[i]

                if scope == 'global':
                    param = params_global.get(method_key)
                else:
                    if z is None or z not in params_par_zone:
                        continue
                    param = params_par_zone[z].get(method_key)
                if param is None:
                    continue

                vals = [value_arrays[vn][i] for vn in val_names]
                if not all(np.isfinite(v) for v in vals):
                    continue

                if len(vals) == 1:
                    seuil = param[1]
                    damaged = int(vals[0] >= seuil)
                else:
                    damaged = apply_param(param, vals[0], vals[1])
                if damaged is None:
                    continue

                of = ogr.Feature(lyr.GetLayerDefn())
                of.SetGeometry(all_geoms[i])
                of.SetField('overture_id', str(oid))
                if z is not None:
                    of.SetField('zone', str(z))
                of.SetField('damaged', damaged)
                for vn, v in zip(val_names, vals):
                    of.SetField(value_field_names[vn], float(v))

                if kind == 'solo':
                    of.SetField('seuil', float(param[1]))
                elif kind == 'and':
                    of.SetField('seuil_a', float(param[1]))
                    of.SetField('seuil_b', float(param[2]))
                elif kind == 'weighted':
                    _, w1, w2, sthr, dir_b, minmax_a, minmax_b = param
                    of.SetField('poids_a', float(w1))
                    of.SetField('poids_b', float(w2))
                    of.SetField('seuil_score', float(sthr))
                    of.SetField('min_a', float(minmax_a[0]))
                    of.SetField('max_a', float(minmax_a[1]))
                    of.SetField('min_b', float(minmax_b[0]))
                    of.SetField('max_b', float(minmax_b[1]))

                lyr.CreateFeature(of)
                n_written += 1
            print(f"    {n_written:,} batiment(s) ecrits")

    ds_out = None
    print(f"\n{SEP}\nEcrit : {OUT_GPKG} (12 couches)\n{SEP}")


if __name__ == '__main__':
    main()
