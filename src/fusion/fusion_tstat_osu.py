# -*- coding: utf-8 -*-
"""Fusion par conjonction du T-stat avec le produit de cohérence OSU, par inclusion progressive des niveaux de confiance et contre trois définitions du positif ; produit le meilleur kappa, le meilleur F1, et le seuil qui minimise les faux positifs à rappel garanti.

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

OSU_PATH = os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg")
OSU_ID_FIELD = "overture_id"
OSU_CONFIDENCE_FIELD = "damage_confidence"

CONFIDENCE_LEVELS = {
    'high_seul': ['high_confidence'],
    'high_et_probable': ['high_confidence', 'probable'],
    'high_probable_et_possible': ['high_confidence', 'probable', 'possible'],
    'toutes_confidences': ['high_confidence', 'probable', 'possible', 'below_floor'],
}

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.1)]

GT_VARIANTS = {
    'Destroyed_seul': lambda raw: (1 if raw == 'Destroyed'
                                     else (0 if raw in ('not_reported', 'Possibly damaged', 'Damaged') else None)),
    'Damaged_et_Destroyed': lambda raw: (1 if raw in ('Damaged', 'Destroyed')
                                           else (0 if raw in ('not_reported', 'Possibly damaged') else None)),
    'Tout_y_compris_Possibly': lambda raw: (1 if raw in ('Possibly damaged', 'Damaged', 'Destroyed')
                                              else (0 if raw == 'not_reported' else None)),
}

RECALL_TARGETS = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\fusion_tstat_osu.csv")

SEP = "=" * 70

# =============================================================================
# HELPERS (communs, deja etablis dans le projet)
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


def compute_confusion_np(y_true, y_pred):
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


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(SEP)
    print("  Chargement AOI, batiments, verite terrain, OSU")
    print(SEP)
    aoi_geom = load_union_geom(AOI_PATH)
    aoi_bounds = get_aoi_bounds(aoi_geom)
    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)
    ems_gt = load_field_by_id(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)
    osu_conf = load_field_by_id(OSU_PATH, OSU_ID_FIELD, OSU_CONFIDENCE_FIELD, aoi_bounds)

    common_ids = list(set(overture.keys()) & set(ems_gt.keys()) & set(osu_conf.keys()))
    print(f"  {len(common_ids)} batiment(s) en commun (Overture + EMS + OSU)")
    geoms = [overture[oid] for oid in common_ids]
    raw_classes = [ems_gt[oid] for oid in common_ids]
    osu_confidences = [osu_conf[oid] for oid in common_ids]

    print(f"\n{SEP}\n  Calcul T-stat par batiment\n{SEP}")
    t_vals = np.array([v if v is not None else np.nan for v in compute_max_per_building(T_TEST_RASTER, geoms)])

    rows = []

    for conf_level_name, included_confidences in CONFIDENCE_LEVELS.items():
        print(f"\n{SEP}\n  Niveau de confiance OSU inclus : {conf_level_name} ({included_confidences})\n{SEP}")
        osu_flag = np.array([1 if c in included_confidences else 0 for c in osu_confidences])

        for gt_name, gt_fn in GT_VARIANTS.items():
            y_true_all = np.array([gt_fn(r) if gt_fn(r) is not None else np.nan for r in raw_classes])
            valid = np.isfinite(t_vals) & np.isfinite(y_true_all)
            yv = y_true_all[valid].astype(int)
            tv = t_vals[valid]
            ov = osu_flag[valid]
            n_pos = int(yv.sum())
            if n_pos == 0:
                continue
            print(f"\n  -- {gt_name} (n={valid.sum()}, positifs={n_pos}) --")

            # A. Meilleur kappa / F1
            best_kappa, best_f1 = None, None
            for tt in T_TEST_THRESHOLDS:
                pred = ((tv >= tt) & (ov == 1)).astype(int)
                m = compute_confusion_np(yv, pred)
                mm = compute_confusion_np(yv, pred)  # reutilise kappa/F1 via fonction dediee
                po = (mm['tp'] + mm['tn']) / mm['n'] if mm['n'] > 0 else np.nan
                p_pred = (mm['tp'] + mm['fp']) / mm['n'] if mm['n'] > 0 else 0
                p_true = (mm['tp'] + mm['fn']) / mm['n'] if mm['n'] > 0 else 0
                pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
                kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
                f1 = (2 * mm['precision'] * mm['recall'] / (mm['precision'] + mm['recall'])
                      if (mm['precision'] == mm['precision'] and mm['recall'] == mm['recall']
                          and (mm['precision'] + mm['recall']) > 0) else np.nan)
                row = {'niveau_confiance_osu': conf_level_name, 'gt_variant': gt_name, 'type_resultat': 'balayage',
                       'rappel_cible': None, 'seuil_tstat': tt, 'tp': mm['tp'], 'fp': mm['fp'], 'fn': mm['fn'],
                       'tn': mm['tn'], 'precision': mm['precision'], 'recall': mm['recall'], 'f1': f1, 'kappa': kappa}
                if kappa == kappa and (best_kappa is None or kappa > best_kappa['kappa']):
                    best_kappa = row
                if f1 == f1 and (best_f1 is None or f1 > best_f1['f1']):
                    best_f1 = row
            if best_kappa:
                rows.append({**best_kappa, 'critere': 'meilleur_kappa'})
                print(f"    Meilleur kappa : seuil_T={best_kappa['seuil_tstat']}  "
                      f"P={best_kappa['precision']:.3f}  R={best_kappa['recall']:.3f}  kappa={best_kappa['kappa']:.3f}")
            if best_f1:
                rows.append({**best_f1, 'critere': 'meilleur_f1'})
                print(f"    Meilleur F1    : seuil_T={best_f1['seuil_tstat']}  "
                      f"P={best_f1['precision']:.3f}  R={best_f1['recall']:.3f}  F1={best_f1['f1']:.3f}")

            # B. Paliers de rappel fixes — minimise les FN (=faux negatifs, equivalent a maximiser
            # le rappel atteint >= cible ; parmi les seuils qui l'atteignent, minimise le nb de FP)
            for target in RECALL_TARGETS:
                best_target = None
                for tt in T_TEST_THRESHOLDS:
                    pred = ((tv >= tt) & (ov == 1)).astype(int)
                    m = compute_confusion_np(yv, pred)
                    if m['recall'] == m['recall'] and m['recall'] >= target:
                        if best_target is None or m['fp'] < best_target['fp']:
                            best_target = {'niveau_confiance_osu': conf_level_name, 'gt_variant': gt_name,
                                            'type_resultat': 'palier_rappel', 'critere': None,
                                            'rappel_cible': target, 'seuil_tstat': tt,
                                            'tp': m['tp'], 'fp': m['fp'], 'fn': m['fn'], 'tn': m['tn'],
                                            'precision': m['precision'], 'recall': m['recall'], 'f1': None, 'kappa': None}
                if best_target:
                    rows.append(best_target)
                    print(f"    Rappel>={target*100:.0f}% : seuil_T={best_target['seuil_tstat']}  "
                          f"FP={best_target['fp']}  rappel={best_target['recall']:.3f}")
                else:
                    print(f"    Rappel>={target*100:.0f}% : INATTEIGNABLE avec ce niveau de confiance")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['niveau_confiance_osu', 'gt_variant', 'type_resultat', 'critere', 'rappel_cible',
                  'seuil_tstat', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
