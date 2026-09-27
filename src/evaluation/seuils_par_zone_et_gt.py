# -*- coding: utf-8 -*-
"""Analyse des seuils du T-stat, de la cohérence et de leur conjonction, zone par zone et globalement, sous trois définitions du positif.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import gc
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

OVERTURE_BUILDINGS_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg")
OVERTURE_ID_FIELD = "id"

EMS_GT_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture_v3_AOI.gpkg")
EMS_ID_FIELD = "id"
EMS_CLASS_FIELD = "cm_damage_gra"

T_TEST_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif")
BDPM_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\BDPM.tif")
COEVENT_RASTER = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\Full scene 40m\VEN_Caraballeda_ASC33_S1A_20260729T1604\S1AD_20260618T224250_20260625T224209_VVP007_INT40_G_ueF_EE3A_corr.tif")
# Burst 20m — NE COUVRE PAS TOUTE L'AOI (emprise plus fine, une seule
# passe) — les batiments hors de son emprise sont EXCLUS de son
# evaluation (pas comptes comme "non endommage" par defaut).
COEVENT_BURST_RASTER = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\burst Cariballada_20m\S1_068790_IW3_20260618_20260625_VV_INT20_5C36\S1_068790_IW3_20260618_20260625_VV_INT20_5C36_corr.tif")

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(1.0, 6.01, 0.2)]
BDPM_THRESHOLDS = [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)]
COEVENT_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.01, 0.02)]

GT_VARIANTS = {
    'PD_endommage': lambda raw: (1 if raw in ('Possibly damaged', 'Damaged', 'Destroyed')
                                   else (0 if raw == 'not_reported' else None)),
    'PD_non_endommage': lambda raw: (1 if raw in ('Damaged', 'Destroyed')
                                       else (0 if raw in ('not_reported', 'Possibly damaged') else None)),
    'Destroyed_seul': lambda raw: (1 if raw == 'Destroyed'
                                     else (0 if raw in ('not_reported', 'Possibly damaged', 'Damaged') else None)),
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\seuils_par_zone_et_gt.csv")

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


def preflight_check():
    print(f"{SEP}\n  Verification prealable des schemas\n{SEP}")
    ok = True

    ds = ogr.Open(AOI_PATH)
    lyr = ds.GetLayer()
    fields = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if AOI_ZONE_FIELD not in fields:
        print(f"  AOI zone   : ERREUR champ '{AOI_ZONE_FIELD}' introuvable — champs: {fields}")
        ok = False
    else:
        print(f"  AOI zone   : OK (champ '{AOI_ZONE_FIELD}' present)")
    ds = None

    ds = ogr.Open(OVERTURE_BUILDINGS_PATH)
    lyr = ds.GetLayer()
    fields = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    n = lyr.GetFeatureCount()
    if OVERTURE_ID_FIELD not in fields:
        print(f"  Overture   : ERREUR champ '{OVERTURE_ID_FIELD}' introuvable — champs: {fields}")
        ok = False
    else:
        print(f"  Overture   : OK ({n:,} batiments, champ '{OVERTURE_ID_FIELD}' present)")
    ds = None

    ds = ogr.Open(EMS_GT_PATH)
    lyr = ds.GetLayer()
    fields = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    n = lyr.GetFeatureCount()
    missing = [f for f in (EMS_ID_FIELD, EMS_CLASS_FIELD) if f not in fields]
    if missing:
        print(f"  EMS GT     : ERREUR champ(s) {missing} introuvable(s) — champs: {fields}")
        ok = False
    else:
        vals = {}
        for i, feat in enumerate(lyr):
            if i > 20000:
                break
            v = feat.GetField(EMS_CLASS_FIELD)
            vals[v] = vals.get(v, 0) + 1
        print(f"  EMS GT     : OK ({n:,} entites, champ '{EMS_CLASS_FIELD}' echantillon: {vals})")
    ds = None

    for name, path in [('T-stat', T_TEST_RASTER), ('BDPM', BDPM_RASTER), ('Co-event', COEVENT_RASTER),
                        ('Co-event burst', COEVENT_BURST_RASTER)]:
        if not os.path.exists(path):
            print(f"  {name:10s} : ERREUR fichier introuvable — {path}")
            ok = False
        else:
            ds_r = gdal.Open(path)
            if ds_r is None:
                print(f"  {name:10s} : ERREUR impossible d'ouvrir")
                ok = False
            else:
                print(f"  {name:10s} : OK ({ds_r.RasterXSize}x{ds_r.RasterYSize} px)")
            ds_r = None

    if not ok:
        sys.exit("\nCorrige la configuration ci-dessus avant de relancer.")
    print("  OK — tout est valide.\n")


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


def zone_for_geom(zones, geom):
    best_label, best_area = None, 0.0
    for zg, label in zones:
        if not zg.Intersects(geom):
            continue
        try:
            inter = zg.Intersection(geom)
            area = inter.Area() if inter else 0.0
        except Exception:
            area = 1e-12
        if area >= best_area:
            best_area = area
            best_label = label
    return best_label


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
        oid = feat.GetField(id_field)
        out[oid] = g2
    ds = None
    print(f"  {len(out):,} batiment(s) Overture charge(s) dans l'emprise AOI")
    return out


def load_ems_gt(path, id_field, class_field, aoi_bounds):
    ds = ogr.Open(path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for feat in lyr:
        oid = feat.GetField(id_field)
        raw = feat.GetField(class_field)
        out[oid] = raw
    ds = None
    print(f"  {len(out):,} classification(s) EMS chargee(s)")
    return out


def compute_max_per_building(raster_path, building_geoms_ordered):
    """Reprojette chaque emprise de batiment, exprimee en WGS84, vers le
    systeme de coordonnees natif du raster avant d'en lire les pixels. Sans
    cette etape, un raster qui n'est pas deja en WGS84 — cas courant d'un
    produit interferometrique brut jamais reprojete — donne des indices de
    pixel hors limites, et aucun batiment ne recoit de valeur."""
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
    n_no_crs_match = 0
    for geom in building_geoms_ordered:
        env = geom.GetEnvelope()  # xmin, xmax, ymin, ymax — EN WGS84
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
        else:
            n_no_crs_match += 1
        out.append(val)
    ds = None
    if n_no_crs_match == len(building_geoms_ordered):
        print(f"    ATTENTION — 0 pixel valide trouve pour TOUS les batiments sur {raster_path} "
              f"— verifie le CRS/l'emprise de ce raster (probleme deja rencontre avec d'autres rasters).")
    return out


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
    recall = tp / (tp + fn) if (tp + fn) > 0 else float('nan')
    f1 = (2 * precision * recall / (precision + recall)
          if (precision == precision and recall == recall and (precision + recall) > 0) else float('nan'))
    po = (tp + tn) / n if n > 0 else float('nan')
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return {'n': n, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': precision, 'recall': recall, 'f1': f1, 'kappa': kappa}


def sweep_solo(y_true, vals, thresholds, direction='ge'):
    """direction='ge' -> endommage si valeur >= seuil (T-stat, BDPM coh_diff
    — plus haut = plus de changement/decorrelation).
    direction='le' -> endommage si valeur <= seuil (cohereence BRUTE —
    plus BAS = decorrelation = dommage potentiel, sens INVERSE)."""
    results = []
    for thr in thresholds:
        if direction == 'ge':
            y_pred = [1 if (v is not None and v >= thr) else 0 for v in vals]
        else:
            y_pred = [1 if (v is not None and v <= thr) else 0 for v in vals]
        m = compute_metrics(y_true, y_pred)
        results.append({'seuil': thr, **m})
    valid_kappa = [r for r in results if r['kappa'] == r['kappa']]
    valid_f1 = [r for r in results if r['f1'] == r['f1']]
    best_kappa = max(valid_kappa, key=lambda r: r['kappa']) if valid_kappa else None
    best_f1 = max(valid_f1, key=lambda r: r['f1']) if valid_f1 else None
    return best_kappa, best_f1


def sweep_and_fusion(y_true, vals_a, thresholds_a, vals_b, thresholds_b, direction_b='ge'):
    """vals_a (T-stat) reste toujours 'ge'. direction_b s'applique a
    vals_b (BDPM='ge', coherence brute='le')."""
    results = []
    for ta in thresholds_a:
        for tb in thresholds_b:
            if direction_b == 'ge':
                y_pred = [1 if (a is not None and b is not None and a >= ta and b >= tb) else 0
                          for a, b in zip(vals_a, vals_b)]
            else:
                y_pred = [1 if (a is not None and b is not None and a >= ta and b <= tb) else 0
                          for a, b in zip(vals_a, vals_b)]
            m = compute_metrics(y_true, y_pred)
            results.append({'seuil_a': ta, 'seuil_b': tb, **m})
    valid_kappa = [r for r in results if r['kappa'] == r['kappa']]
    valid_f1 = [r for r in results if r['f1'] == r['f1']]
    best_kappa = max(valid_kappa, key=lambda r: r['kappa']) if valid_kappa else None
    best_f1 = max(valid_f1, key=lambda r: r['f1']) if valid_f1 else None
    return best_kappa, best_f1


def get_aoi_bounds(zones):
    xmin = ymin = xmax = ymax = None
    for g, _ in zones:
        env = g.GetEnvelope()
        xmin = env[0] if xmin is None else min(xmin, env[0])
        xmax = env[1] if xmax is None else max(xmax, env[1])
        ymin = env[2] if ymin is None else min(ymin, env[2])
        ymax = env[3] if ymax is None else max(ymax, env[3])
    return (xmin, ymin, xmax, ymax)


# =============================================================================
# MAIN
# =============================================================================

def main():
    preflight_check()

    print(f"{SEP}\n  Chargement des zones AOI\n{SEP}")
    zones = load_aoi_zones(AOI_PATH, AOI_ZONE_FIELD)
    aoi_bounds = get_aoi_bounds(zones)
    print(f"  {len(zones)} zone(s) AOI")

    print(f"\n{SEP}\n  Chargement des batiments Overture\n{SEP}")
    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)

    print(f"\n{SEP}\n  Chargement de la verite terrain EMS\n{SEP}")
    ems_gt = load_ems_gt(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)

    common_ids = list(set(overture.keys()) & set(ems_gt.keys()))
    print(f"\n  {len(common_ids)} batiment(s) en commun (Overture + verite terrain EMS)")
    geoms = [overture[oid] for oid in common_ids]
    raw_classes = [ems_gt[oid] for oid in common_ids]

    print(f"\n  Attribution de la zone AOI par batiment...")
    zone_labels = [zone_for_geom(zones, g) for g in geoms]

    print(f"\n{SEP}\n  Calcul T-stat (max) par batiment\n{SEP}")
    t_vals = compute_max_per_building(T_TEST_RASTER, geoms)
    gc.collect()
    print(f"{SEP}\n  Calcul BDPM (max) par batiment\n{SEP}")
    b_vals = compute_max_per_building(BDPM_RASTER, geoms)
    gc.collect()
    print(f"{SEP}\n  Calcul Co-event (max) par batiment\n{SEP}")
    c_vals = compute_max_per_building(COEVENT_RASTER, geoms)
    gc.collect()
    print(f"{SEP}\n  Calcul Co-event BURST 20m (max) par batiment\n{SEP}")
    cb_vals = compute_max_per_building(COEVENT_BURST_RASTER, geoms)
    n_burst_valid = sum(1 for v in cb_vals if v is not None)
    print(f"  {n_burst_valid:,} / {len(cb_vals):,} batiment(s) dans l'emprise du burst "
          f"(le reste sera EXCLU de l'evaluation burst, pas compte 'non endommage')")
    gc.collect()

    zone_groups = {'GLOBAL': list(range(len(common_ids)))}
    for i, z in enumerate(zone_labels):
        if z is not None:
            zone_groups.setdefault(z, []).append(i)

    rows = []
    for gt_name, gt_fn in GT_VARIANTS.items():
        print(f"\n{SEP}\n  Verite terrain : {gt_name}\n{SEP}")
        y_true_all = [gt_fn(r) for r in raw_classes]

        for zone_name, idx_list in zone_groups.items():
            idx_valid = [i for i in idx_list if y_true_all[i] is not None]
            if not idx_valid:
                continue
            y_true = [y_true_all[i] for i in idx_valid]
            n_pos = sum(y_true)
            if n_pos == 0:
                continue

            tv = [t_vals[i] for i in idx_valid]
            bv = [b_vals[i] for i in idx_valid]
            cv = [c_vals[i] for i in idx_valid]
            cbv = [cb_vals[i] for i in idx_valid]

            print(f"\n  -- Zone: {zone_name} (n={len(idx_valid)}, positifs={n_pos}) --")

            # T-stat/BDPM : direction 'ge' (plus haut = plus endommage).
            # Co-event/burst : COHERENCE BRUTE — direction 'le' (plus BAS
            # = decorrelation = dommage potentiel, sens INVERSE).
            for method_name, vals, thresholds, direction in [
                ('t_test', tv, T_TEST_THRESHOLDS, 'ge'),
                ('bdpm', bv, BDPM_THRESHOLDS, 'ge'),
                ('coevent', cv, COEVENT_THRESHOLDS, 'le'),
            ]:
                bk, bf1 = sweep_solo(y_true, vals, thresholds, direction=direction)
                if bk:
                    rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': method_name,
                                 'critere': 'kappa', 'seuil_a': bk['seuil'], 'seuil_b': None,
                                 **{k: v for k, v in bk.items() if k != 'seuil'}})
                    print(f"    {method_name:8s} (meilleur kappa) : seuil={bk['seuil']}  "
                          f"P={bk['precision']:.3f} R={bk['recall']:.3f} F1={bk['f1']:.3f} kappa={bk['kappa']:.3f}")
                if bf1:
                    rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': method_name,
                                 'critere': 'f1', 'seuil_a': bf1['seuil'], 'seuil_b': None,
                                 **{k: v for k, v in bf1.items() if k != 'seuil'}})
                    print(f"    {method_name:8s} (meilleur F1)    : seuil={bf1['seuil']}  "
                          f"P={bf1['precision']:.3f} R={bf1['recall']:.3f} F1={bf1['f1']:.3f} kappa={bf1['kappa']:.3f}")

            # Burst 20m — RESTREINT aux batiments ayant une vraie valeur
            # (pas dans l'emprise = EXCLU, pas compte "non endommage").
            idx_burst = [j for j, v in enumerate(cbv) if v is not None]
            if idx_burst:
                y_true_burst = [y_true[j] for j in idx_burst]
                cbv_burst = [cbv[j] for j in idx_burst]
                tv_burst = [tv[j] for j in idx_burst]
                n_pos_burst = sum(y_true_burst)
                if n_pos_burst > 0:
                    print(f"    (burst 20m : {len(idx_burst)} batiment(s) dans son emprise, "
                          f"{n_pos_burst} positif(s))")
                    bk, bf1 = sweep_solo(y_true_burst, cbv_burst, COEVENT_THRESHOLDS, direction='le')
                    if bk:
                        rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': 'coevent_burst',
                                     'critere': 'kappa', 'seuil_a': bk['seuil'], 'seuil_b': None,
                                     **{k: v for k, v in bk.items() if k != 'seuil'}})
                        print(f"    coevent_burst (meilleur kappa) : seuil={bk['seuil']}  "
                              f"P={bk['precision']:.3f} R={bk['recall']:.3f} F1={bk['f1']:.3f} kappa={bk['kappa']:.3f}")
                    if bf1:
                        rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': 'coevent_burst',
                                     'critere': 'f1', 'seuil_a': bf1['seuil'], 'seuil_b': None,
                                     **{k: v for k, v in bf1.items() if k != 'seuil'}})
                        print(f"    coevent_burst (meilleur F1)    : seuil={bf1['seuil']}  "
                              f"P={bf1['precision']:.3f} R={bf1['recall']:.3f} F1={bf1['f1']:.3f} kappa={bf1['kappa']:.3f}")

                    bk, bf1 = sweep_and_fusion(y_true_burst, tv_burst, T_TEST_THRESHOLDS,
                                                cbv_burst, COEVENT_THRESHOLDS, direction_b='le')
                    if bk:
                        rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': 'fusion_ET_tstat_burst',
                                     'critere': 'kappa', **{k: v for k, v in bk.items()}})
                        print(f"    fusion_ET_tstat_burst   (meilleur kappa) : seuil_a={bk['seuil_a']} "
                              f"seuil_b={bk['seuil_b']}  P={bk['precision']:.3f} R={bk['recall']:.3f} "
                              f"F1={bk['f1']:.3f} kappa={bk['kappa']:.3f}")
                    if bf1:
                        rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': 'fusion_ET_tstat_burst',
                                     'critere': 'f1', **{k: v for k, v in bf1.items()}})
                        print(f"    fusion_ET_tstat_burst   (meilleur F1)    : seuil_a={bf1['seuil_a']} "
                              f"seuil_b={bf1['seuil_b']}  P={bf1['precision']:.3f} R={bf1['recall']:.3f} "
                              f"F1={bf1['f1']:.3f} kappa={bf1['kappa']:.3f}")
                else:
                    print(f"    (burst 20m : aucun positif dans son emprise pour cette zone/GT — ignore)")
            else:
                print(f"    (burst 20m : aucun batiment dans son emprise pour cette zone — ignore)")

            for fusion_name, vals_a, thr_a, vals_b, thr_b, dir_b in [
                ('fusion_ET_tstat_bdpm', tv, T_TEST_THRESHOLDS, bv, BDPM_THRESHOLDS, 'ge'),
                ('fusion_ET_tstat_coevent', tv, T_TEST_THRESHOLDS, cv, COEVENT_THRESHOLDS, 'le'),
            ]:
                bk, bf1 = sweep_and_fusion(y_true, vals_a, thr_a, vals_b, thr_b, direction_b=dir_b)
                if bk:
                    rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': fusion_name,
                                 'critere': 'kappa', **{k: v for k, v in bk.items()}})
                    print(f"    {fusion_name:24s} (meilleur kappa) : seuil_a={bk['seuil_a']} seuil_b={bk['seuil_b']}  "
                          f"P={bk['precision']:.3f} R={bk['recall']:.3f} F1={bk['f1']:.3f} kappa={bk['kappa']:.3f}")
                if bf1:
                    rows.append({'gt_variant': gt_name, 'zone': zone_name, 'methode': fusion_name,
                                 'critere': 'f1', **{k: v for k, v in bf1.items()}})
                    print(f"    {fusion_name:24s} (meilleur F1)    : seuil_a={bf1['seuil_a']} seuil_b={bf1['seuil_b']}  "
                          f"P={bf1['precision']:.3f} R={bf1['recall']:.3f} F1={bf1['f1']:.3f} kappa={bf1['kappa']:.3f}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['gt_variant', 'zone', 'methode', 'critere', 'seuil_a', 'seuil_b',
                  'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
