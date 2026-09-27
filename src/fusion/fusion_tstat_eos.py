# -*- coding: utf-8 -*-
"""Fusion du T-stat avec le produit EOS-RS continu, en faisant varier les deux seuils en conjonction et en testant une pondération continue entre les deux termes.

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

OVERTURE_BUILDINGS_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg")
OVERTURE_ID_FIELD = "id"

EMS_GT_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture_v3_AOI.gpkg")
EMS_ID_FIELD = "id"
EMS_CLASS_FIELD = "cm_damage_gra"

T_TEST_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif")

EOS_PATH = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg")
EOS_ID_FIELD = "overture_id"
EOS_VALUE_FIELD = "raster_max"

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.15)]

WEIGHT_STEPS = [round(x, 1) for x in np.arange(0.0, 1.01, 0.1)]
SCORE_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.001, 0.02)]

GT_VARIANTS = {
    'Destroyed_seul': lambda raw: (1 if raw == 'Destroyed'
                                     else (0 if raw in ('not_reported', 'Possibly damaged', 'Damaged') else None)),
    'Damaged_et_Destroyed': lambda raw: (1 if raw in ('Damaged', 'Destroyed')
                                           else (0 if raw in ('not_reported', 'Possibly damaged') else None)),
    'Tout_y_compris_Possibly': lambda raw: (1 if raw in ('Possibly damaged', 'Damaged', 'Destroyed')
                                              else (0 if raw == 'not_reported' else None)),
}

RECALL_TARGETS = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\fusion_tstat_eos.csv")

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
        print(f"  ATTENTION — impossible d'ouvrir : {path}")
        return {}
    lyr = ds.GetLayer()
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if id_field not in field_names or value_field not in field_names:
        print(f"  ERREUR — champ manquant — champs disponibles: {field_names}")
        ds = None
        return {}
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for feat in lyr:
        out[feat.GetField(id_field)] = feat.GetField(value_field)
    ds = None
    print(f"  {len(out):,} valeur(s) chargee(s) depuis {os.path.basename(path)}")
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
        raster_srs = osr.SpatialReference()
        raster_srs.ImportFromWkt(prj)
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


def minmax_norm(arr):
    valid = arr[np.isfinite(arr)]
    if len(valid) == 0:
        return arr
    lo, hi = np.min(valid), np.max(valid)
    if hi <= lo:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement AOI, batiments, verite terrain, EOS")
    print(SEP)
    aoi_geom = load_union_geom(AOI_PATH)
    aoi_bounds = get_aoi_bounds(aoi_geom)
    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)
    ems_gt = load_field_by_id(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)
    eos_raw = load_field_by_id(EOS_PATH, EOS_ID_FIELD, EOS_VALUE_FIELD, aoi_bounds)

    common_ids = list(set(overture.keys()) & set(ems_gt.keys()) & set(eos_raw.keys()))
    print(f"  {len(common_ids)} batiment(s) en commun (Overture + EMS + EOS)")
    geoms = [overture[oid] for oid in common_ids]
    raw_classes = [ems_gt[oid] for oid in common_ids]
    eos_vals = np.array([eos_raw[oid] if eos_raw[oid] is not None else np.nan for oid in common_ids])

    print(f"\n{SEP}\n  Calcul T-stat par batiment\n{SEP}")
    t_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(T_TEST_RASTER, geoms)])

    eos_finite = eos_vals[np.isfinite(eos_vals)]
    eos_thresholds = [round(x, 3) for x in np.linspace(np.min(eos_finite), np.max(eos_finite), 40)]
    print(f"  EOS raster_max — plage reelle: [{np.min(eos_finite):.3f}, {np.max(eos_finite):.3f}]")

    rows = []

    for gt_name, gt_fn in GT_VARIANTS.items():
        print(f"\n{SEP}\n  Verite terrain : {gt_name}\n{SEP}")
        y_true_all = np.array([gt_fn(r) if gt_fn(r) is not None else np.nan for r in raw_classes])
        valid = np.isfinite(t_vals) & np.isfinite(eos_vals) & np.isfinite(y_true_all)
        yv = y_true_all[valid].astype(int)
        tv = t_vals[valid]
        ev = eos_vals[valid]
        n_pos = int(yv.sum())
        print(f"  {valid.sum()} batiment(s) valides, {n_pos} positif(s)")
        if n_pos == 0:
            continue

        print("\n  -- Fusion ET (balayage 2D) --")
        best_kappa, best_f1 = None, None
        for tt in T_TEST_THRESHOLDS:
            for te in eos_thresholds:
                pred = ((tv >= tt) & (ev >= te)).astype(int)
                m = compute_metrics_np(yv, pred)
                if m['kappa'] == m['kappa'] and (best_kappa is None or m['kappa'] > best_kappa['kappa']):
                    best_kappa = {'methode': 'fusion_ET', 'seuil_tstat': tt, 'seuil_eos': te,
                                  'poids_tstat': None, 'poids_eos': None, **m}
                if m['f1'] == m['f1'] and (best_f1 is None or m['f1'] > best_f1['f1']):
                    best_f1 = {'methode': 'fusion_ET', 'seuil_tstat': tt, 'seuil_eos': te,
                               'poids_tstat': None, 'poids_eos': None, **m}
        if best_kappa:
            rows.append({'gt_variant': gt_name, 'type_resultat': 'meilleur_kappa', 'rappel_cible': None, **best_kappa})
            print(f"    Meilleur kappa : T-stat>={best_kappa['seuil_tstat']}  EOS>={best_kappa['seuil_eos']}  "
                  f"kappa={best_kappa['kappa']:.3f}")
        if best_f1:
            rows.append({'gt_variant': gt_name, 'type_resultat': 'meilleur_f1', 'rappel_cible': None, **best_f1})
            print(f"    Meilleur F1    : T-stat>={best_f1['seuil_tstat']}  EOS>={best_f1['seuil_eos']}  "
                  f"F1={best_f1['f1']:.3f}")

        print("\n  -- Ponderation continue --")
        t_norm = minmax_norm(tv); e_norm = minmax_norm(ev)
        best_kappa_w, best_f1_w = None, None
        for w1 in WEIGHT_STEPS:
            w2 = round(1.0 - w1, 1)
            if w2 < 0:
                continue
            score = w1 * t_norm + w2 * e_norm
            for thr in SCORE_THRESHOLDS:
                pred = (score >= thr).astype(int)
                m = compute_metrics_np(yv, pred)
                if m['kappa'] == m['kappa'] and (best_kappa_w is None or m['kappa'] > best_kappa_w['kappa']):
                    best_kappa_w = {'methode': 'ponderation', 'seuil_tstat': None, 'seuil_eos': thr,
                                    'poids_tstat': w1, 'poids_eos': w2, **m}
                if m['f1'] == m['f1'] and (best_f1_w is None or m['f1'] > best_f1_w['f1']):
                    best_f1_w = {'methode': 'ponderation', 'seuil_tstat': None, 'seuil_eos': thr,
                                 'poids_tstat': w1, 'poids_eos': w2, **m}
        if best_kappa_w:
            rows.append({'gt_variant': gt_name, 'type_resultat': 'meilleur_kappa', 'rappel_cible': None, **best_kappa_w})
            print(f"    Meilleur kappa (pondere) : poids_T={best_kappa_w['poids_tstat']}  "
                  f"poids_EOS={best_kappa_w['poids_eos']}  seuil={best_kappa_w['seuil_eos']}  "
                  f"kappa={best_kappa_w['kappa']:.3f}")
        if best_f1_w:
            rows.append({'gt_variant': gt_name, 'type_resultat': 'meilleur_f1', 'rappel_cible': None, **best_f1_w})

        print("\n  -- Paliers de rappel (fusion ET) --")
        for target in RECALL_TARGETS:
            best_target = None
            for tt in T_TEST_THRESHOLDS:
                for te in eos_thresholds:
                    pred = ((tv >= tt) & (ev >= te)).astype(int)
                    m = compute_metrics_np(yv, pred)
                    if m['recall'] == m['recall'] and m['recall'] >= target:
                        if best_target is None or m['fp'] < best_target['fp']:
                            best_target = {'methode': 'fusion_ET', 'seuil_tstat': tt, 'seuil_eos': te,
                                           'poids_tstat': None, 'poids_eos': None, **m}
            if best_target:
                rows.append({'gt_variant': gt_name, 'type_resultat': 'palier_rappel',
                             'rappel_cible': target, **best_target})
                print(f"    Rappel>={target*100:.0f}% : T-stat>={best_target['seuil_tstat']}  "
                      f"EOS>={best_target['seuil_eos']}  FP={best_target['fp']}")
            else:
                print(f"    Rappel>={target*100:.0f}% : INATTEIGNABLE")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['gt_variant', 'type_resultat', 'rappel_cible', 'methode', 'seuil_tstat', 'seuil_eos',
                  'poids_tstat', 'poids_eos', 'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
