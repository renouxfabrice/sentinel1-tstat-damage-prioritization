# -*- coding: utf-8 -*-
"""Analyse des seuils avec mosaïquage automatique des rafales co-événement et trois règles de combinaison des orbites ascendantes et descendantes par bâtiment.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import glob
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

ASC_BURST_DIR = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\burst Cariballada_20m\ASC_tif")
DESC_BURST_DIR = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\burst Cariballada_20m\DESC_tif")
MOSAIC_CACHE_DIR = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst")

NOT_ANALYSED_PATHS = [
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI02_GRA_MONIT01_v2\EMSR884_AOI02_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI06_GRA_MONIT01_v2\EMSR884_AOI06_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI08_GRA_MONIT01_v2\EMSR884_AOI08_GRA_MONIT01_notAnalysedA_v1.shp"),
    os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_AOI12_GRA_MONIT01_v3\EMSR884_AOI12_GRA_MONIT01_notAnalysedA_v1.shp"),
]

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(1.0, 6.01, 0.2)]
BDPM_THRESHOLDS = [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)]
BURST_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.01, 0.02)]

GT_VARIANTS = {
    'PD_endommage': lambda raw: (1 if raw in ('Possibly damaged', 'Damaged', 'Destroyed')
                                   else (0 if raw == 'not_reported' else None)),
    'PD_non_endommage': lambda raw: (1 if raw in ('Damaged', 'Destroyed')
                                       else (0 if raw in ('not_reported', 'Possibly damaged') else None)),
    'Destroyed_seul': lambda raw: (1 if raw == 'Destroyed'
                                     else (0 if raw in ('not_reported', 'Possibly damaged', 'Damaged') else None)),
}

EXTRA_ZONE_GROUPS = {
    'Caraballeda_LaGuaira_CatiaLaMar': ['caraballeda', 'la_guaira', 'catia_la_mar'],
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\seuils_asc_desc_complet.csv")

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
        print(f"  AOI zone   : OK")
    ds = None

    ds = ogr.Open(OVERTURE_BUILDINGS_PATH)
    lyr = ds.GetLayer()
    fields = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    n = lyr.GetFeatureCount()
    if OVERTURE_ID_FIELD not in fields:
        print(f"  Overture   : ERREUR champ '{OVERTURE_ID_FIELD}' introuvable — champs: {fields}")
        ok = False
    else:
        print(f"  Overture   : OK ({n:,} batiments)")
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
        print(f"  EMS GT     : OK ({n:,} entites)")
    ds = None

    for name, path in [('T-stat', T_TEST_RASTER), ('BDPM', BDPM_RASTER)]:
        if not os.path.exists(path):
            print(f"  {name:10s} : ERREUR fichier introuvable — {path}")
            ok = False
        else:
            print(f"  {name:10s} : OK")

    for name, d in [('ASC bursts', ASC_BURST_DIR), ('DESC bursts', DESC_BURST_DIR)]:
        if not os.path.isdir(d):
            print(f"  {name:10s} : ERREUR dossier introuvable — {d}")
            ok = False
        else:
            n_tif = len(glob.glob(os.path.join(d, '**', '*.tif'), recursive=True))
            print(f"  {name:10s} : OK ({n_tif} fichier(s) .tif trouve(s))")

    for path in NOT_ANALYSED_PATHS:
        if not os.path.exists(path):
            print(f"  Attention: zone nuageuse introuvable — {path}")

    if not ok:
        sys.exit("\nCorrige la configuration ci-dessus avant de relancer.")
    print("  OK — configuration de base valide.\n")


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


def load_multi_union(paths):
    all_geoms = []
    for p in paths:
        if not os.path.exists(p):
            continue
        g = load_union_geom(p)
        if g is not None:
            all_geoms.append(g)
    if not all_geoms:
        return None
    union = all_geoms[0]
    for g in all_geoms[1:]:
        union = union.Union(g)
    return union


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


def compute_max_and_coverage_per_building(raster_path, building_geoms_ordered):
    if raster_path is None or not os.path.exists(raster_path):
        n = len(building_geoms_ordered)
        return [None] * n, [0] * n
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

    out_vals, out_cov = [], []
    for geom in building_geoms_ordered:
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
        val, n_valid = None, 0
        if px0 <= px1 and py0 <= py1:
            sub = band.ReadAsArray(px0, py0, px1 - px0 + 1, py1 - py0 + 1)
            if sub is not None:
                sub = sub.astype(np.float64)
                if nd is not None:
                    sub[np.isclose(sub, nd)] = np.nan
                valid = sub[np.isfinite(sub)]
                n_valid = int(len(valid))
                if n_valid > 0:
                    val = float(np.max(valid))
        out_vals.append(val)
        out_cov.append(n_valid)
    ds = None
    return out_vals, out_cov


def combine_asc_desc(asc_vals, asc_cov, desc_vals, desc_cov, mode):
    out = []
    for a, ac, d, dc in zip(asc_vals, asc_cov, desc_vals, desc_cov):
        if a is None and d is None:
            out.append(None); continue
        if a is None:
            out.append(d); continue
        if d is None:
            out.append(a); continue
        if mode == 'moyenne':
            out.append((a + d) / 2.0)
        elif mode == 'sensible':
            out.append(min(a, d))
        elif mode == 'meilleure_couverture':
            out.append(a if ac >= dc else d)
        else:
            raise ValueError(f"mode inconnu: {mode}")
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

    print(f"{SEP}\n  Mosaique des bursts co-event\n{SEP}")
    asc_mosaic_path, n_asc = build_mosaic_if_needed(ASC_BURST_DIR, MOSAIC_CACHE_DIR, 'mosaic_asc.tif')
    desc_mosaic_path, n_desc = build_mosaic_if_needed(DESC_BURST_DIR, MOSAIC_CACHE_DIR, 'mosaic_desc.tif')
    print(f"  ASC : {n_asc} tuile(s) -> {asc_mosaic_path}")
    print(f"  DESC: {n_desc} tuile(s) -> {desc_mosaic_path}")

    print(f"\n{SEP}\n  Chargement des zones AOI\n{SEP}")
    zones = load_aoi_zones(AOI_PATH, AOI_ZONE_FIELD)
    aoi_bounds = get_aoi_bounds(zones)
    print(f"  {len(zones)} zone(s) AOI")

    print(f"\n{SEP}\n  Chargement des zones nuageuses (non analysees EMS)\n{SEP}")
    cloud_geom = load_multi_union(NOT_ANALYSED_PATHS)
    print(f"  Zones nuageuses : {'chargees' if cloud_geom is not None else 'AUCUNE (ignoree)'}")

    print(f"\n{SEP}\n  Chargement des batiments Overture\n{SEP}")
    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)

    print(f"\n{SEP}\n  Chargement de la verite terrain EMS\n{SEP}")
    ems_gt = load_ems_gt(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)

    common_ids = list(set(overture.keys()) & set(ems_gt.keys()))
    print(f"\n  {len(common_ids)} batiment(s) en commun")
    geoms = [overture[oid] for oid in common_ids]
    raw_classes = [ems_gt[oid] for oid in common_ids]

    print(f"\n  Attribution zone AOI + statut nuageux par batiment...")
    zone_labels = [zone_for_geom(zones, g) for g in geoms]
    is_cloudy = [bool(cloud_geom is not None and cloud_geom.Contains(g.Centroid())) for g in geoms]
    n_cloudy = sum(is_cloudy)
    print(f"  {n_cloudy} / {len(geoms)} batiment(s) en zone nuageuse (non analysee EMS)")

    print(f"\n{SEP}\n  Calcul T-stat (max) par batiment\n{SEP}")
    t_vals = compute_max_and_coverage_per_building(T_TEST_RASTER, geoms)[0]
    gc.collect()
    print(f"{SEP}\n  Calcul BDPM (max) par batiment\n{SEP}")
    b_vals = compute_max_and_coverage_per_building(BDPM_RASTER, geoms)[0]
    gc.collect()
    print(f"{SEP}\n  Calcul burst ASC (mosaique, max+couverture) par batiment\n{SEP}")
    asc_vals, asc_cov = compute_max_and_coverage_per_building(asc_mosaic_path, geoms)
    gc.collect()
    print(f"{SEP}\n  Calcul burst DESC (mosaique, max+couverture) par batiment\n{SEP}")
    desc_vals, desc_cov = compute_max_and_coverage_per_building(desc_mosaic_path, geoms)
    gc.collect()

    print(f"\n{SEP}\n  Combinaison ASC+DESC (3 methodologies)\n{SEP}")
    combined = {}
    for mode in ('moyenne', 'sensible', 'meilleure_couverture'):
        combined[mode] = combine_asc_desc(asc_vals, asc_cov, desc_vals, desc_cov, mode)
        n_valid = sum(1 for v in combined[mode] if v is not None)
        print(f"  {mode:22s} : {n_valid:,} batiment(s) avec valeur combinee")

    zone_groups = {'GLOBAL': list(range(len(common_ids)))}
    for i, z in enumerate(zone_labels):
        if z is not None:
            zone_groups.setdefault(z, []).append(i)
    for group_name, member_zones in EXTRA_ZONE_GROUPS.items():
        zone_groups[group_name] = [i for i, z in enumerate(zone_labels) if z in member_zones]

    rows = []
    for cloud_scope in ('sans_zones_nuageuses', 'aoi_complete'):
        print(f"\n{SEP}\n  PORTEE : {cloud_scope}\n{SEP}")
        for gt_name, gt_fn in GT_VARIANTS.items():
            print(f"\n{SEP}\n  Verite terrain : {gt_name}\n{SEP}")
            y_true_all = [gt_fn(r) for r in raw_classes]

            for zone_name, idx_list_raw in zone_groups.items():
                if cloud_scope == 'sans_zones_nuageuses':
                    idx_list = [i for i in idx_list_raw if not is_cloudy[i]]
                else:
                    idx_list = idx_list_raw

                idx_valid = [i for i in idx_list if y_true_all[i] is not None]
                if not idx_valid:
                    continue
                y_true = [y_true_all[i] for i in idx_valid]
                n_pos = sum(y_true)
                if n_pos == 0:
                    continue

                tv = [t_vals[i] for i in idx_valid]
                bv = [b_vals[i] for i in idx_valid]
                av = [asc_vals[i] for i in idx_valid]
                dv = [desc_vals[i] for i in idx_valid]
                cmb = {mode: [combined[mode][i] for i in idx_valid] for mode in combined}

                print(f"\n  -- Zone: {zone_name} (n={len(idx_valid)}, positifs={n_pos}) --")

                for method_name, vals, thresholds, direction in [
                    ('t_test', tv, T_TEST_THRESHOLDS, 'ge'),
                    ('bdpm', bv, BDPM_THRESHOLDS, 'ge'),
                    ('burst_asc', av, BURST_THRESHOLDS, 'le'),
                    ('burst_desc', dv, BURST_THRESHOLDS, 'le'),
                ] + [(f'burst_{mode}', cmb[mode], BURST_THRESHOLDS, 'le') for mode in combined]:
                    bk, bf1 = sweep_solo(y_true, vals, thresholds, direction=direction)
                    if bk:
                        rows.append({'portee': cloud_scope, 'gt_variant': gt_name, 'zone': zone_name,
                                     'methode': method_name, 'critere': 'kappa',
                                     'seuil_a': bk['seuil'], 'seuil_b': None,
                                     **{k: v for k, v in bk.items() if k != 'seuil'}})
                    if bf1:
                        rows.append({'portee': cloud_scope, 'gt_variant': gt_name, 'zone': zone_name,
                                     'methode': method_name, 'critere': 'f1',
                                     'seuil_a': bf1['seuil'], 'seuil_b': None,
                                     **{k: v for k, v in bf1.items() if k != 'seuil'}})
                    if bk:
                        print(f"    {method_name:20s} (kappa) : seuil={bk['seuil']}  "
                              f"P={bk['precision']:.3f} R={bk['recall']:.3f} kappa={bk['kappa']:.3f}")

                for fusion_name, vals_b, thr_b, dir_b in [
                    ('fusion_ET_tstat_bdpm', bv, BDPM_THRESHOLDS, 'ge'),
                    ('fusion_ET_tstat_asc', av, BURST_THRESHOLDS, 'le'),
                    ('fusion_ET_tstat_desc', dv, BURST_THRESHOLDS, 'le'),
                ] + [(f'fusion_ET_tstat_{mode}', cmb[mode], BURST_THRESHOLDS, 'le') for mode in combined]:
                    bk, bf1 = sweep_and_fusion(y_true, tv, T_TEST_THRESHOLDS, vals_b, thr_b, direction_b=dir_b)
                    if bk:
                        rows.append({'portee': cloud_scope, 'gt_variant': gt_name, 'zone': zone_name,
                                     'methode': fusion_name, 'critere': 'kappa', **{k: v for k, v in bk.items()}})
                    if bf1:
                        rows.append({'portee': cloud_scope, 'gt_variant': gt_name, 'zone': zone_name,
                                     'methode': fusion_name, 'critere': 'f1', **{k: v for k, v in bf1.items()}})
                    if bk:
                        print(f"    {fusion_name:26s} (kappa) : seuil_a={bk['seuil_a']} seuil_b={bk['seuil_b']}  "
                              f"P={bk['precision']:.3f} R={bk['recall']:.3f} kappa={bk['kappa']:.3f}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['portee', 'gt_variant', 'zone', 'methode', 'critere', 'seuil_a', 'seuil_b',
                  'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
