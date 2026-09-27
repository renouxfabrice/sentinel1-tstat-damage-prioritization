# -*- coding: utf-8 -*-
"""Recherche de la meilleure combinaison de raster, de règle d'agrégation et de seuil contre la vérité issue du signalement participatif, sur les empreintes de la base collaborative.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
from config import DONNEES

try:
    from osgeo import ogr, osr, gdal
    import numpy as np
except ImportError:
    sys.exit("osgeo (gdal/ogr) et numpy requis.")

ogr.UseExceptions()
gdal.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Couche chatmap_on_buildings SUR OVERTURE (pas OSM — meme geometrie que
# nos propres resultats T_test/BDPM, pas de correspondance approximative
# en plus).
# OSM utilise ici — pas de souci methodologique pour CE script precis : on
# fait des statistiques de zone sur le raster a partir de n'importe quelle
# empreinte de batiment reelle, OSM convient aussi bien qu'Overture pour
# ca (la reserve Overture/OSM concernait la jointure ENTRE sources, pas ce
# calcul-la).
BUILDINGS_PATH = os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_OSM.gpkg")

GT_FIELD = "cm_matched"  # ancien binaire — conserve pour reference, plus utilise directement
                          # (voir CLASS_FIELD et GT_VARIANTS plus bas, qui le remplacent)

# Rasters a tester
RASTERS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\T_stat [Caraballeda].tif"),
    'bdpm':   os.path.join(DONNEES, r"VENEZUELA\MOI\BDPM\Caraballeda\coh_diff_fused.tif"),
}

# Gammes de seuils a tester — DIFFERENTES pour chaque raster (echelles
# physiques tres differentes : T-stat ~ 0 a 5, BDPM ~ -0.5 a 0.9)
THRESHOLD_RANGES = {
    't_test': [round(x, 2) for x in np.arange(1.0, 6.01, 0.1)],
    'bdpm':   [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)],
}

AGG_METHODS = ['mean', 'max', 'p75', 'p90']

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\seuil_balayage_chatmap.csv")

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


CLASS_FIELD = "cm_damaged"  # classe brute ChatMap : complete/significant/minimal/not_reported

# 3 definitions possibles de la verite terrain, a partir de la classe brute :
#   'all'    : complete+significant+minimal = endommage (ce qu'on a fait jusqu'ici)
#   'strict' : SEUL complete = endommage — le reste (significant/minimal/
#              not_reported) = non endommage
#   'large'  : complete+significant = endommage, not_reported = non
#              endommage, minimal EXCLU du calcul (ni positif ni negatif —
#              signal trop ambigu pour trancher, pas juge fiable a classer
#              d'un cote ou de l'autre)
GT_VARIANTS = {
    'all':    lambda raw: 1 if raw in ('complete', 'significant', 'minimal') else (0 if raw == 'not_reported' else None),
    'strict': lambda raw: 1 if raw == 'complete' else (0 if raw in ('significant', 'minimal', 'not_reported') else None),
    'large':  lambda raw: 1 if raw in ('complete', 'significant') else (0 if raw == 'not_reported' else None),
}


def load_buildings_with_gt(path, class_field):
    """Charge les batiments avec leur geometrie + la classe brute ChatMap.
    Retourne liste de (geom, classe_brute_ou_None)."""
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir : {path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                   for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if class_field not in field_names:
        sys.exit(f"Erreur: champ '{class_field}' introuvable. Champs disponibles: {field_names}")

    out = []
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        geom = geom.Clone()
        if tr is not None:
            geom.Transform(tr)
        raw = feat.GetField(class_field)
        out.append((geom, raw))
    ds = None
    from collections import Counter
    print(f"Batiments charges : {len(out)}  — repartition classe brute: {dict(Counter(r for _, r in out))}")
    return out


def compute_building_stats(raster_path, buildings):
    """Pour chaque batiment, calcule mean/max/p75/p90 des pixels sous son
    emprise. Retourne une liste parallele de dicts {stat: valeur_ou_None}."""
    ds = gdal.Open(raster_path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir le raster : {raster_path}")
    gt = ds.GetGeoTransform()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray().astype(np.float32)
    nd = band.GetNoDataValue()
    ds = None
    if nd is not None:
        arr[arr == nd] = np.nan

    results = []
    n_no_valid = 0
    for geom, gt_bin in buildings:
        env = geom.GetEnvelope()  # xmin,xmax,ymin,ymax
        px0 = max(0, int((env[0] - gt[0]) / gt[1]))
        px1 = min(nx - 1, int((env[1] - gt[0]) / gt[1]))
        py0 = max(0, int((env[3] - gt[3]) / gt[5]))
        py1 = min(ny - 1, int((env[2] - gt[3]) / gt[5]))
        stats = {'mean': None, 'max': None, 'p75': None, 'p90': None}
        if px0 <= px1 and py0 <= py1:
            sub = arr[py0:py1 + 1, px0:px1 + 1]
            valid = sub[np.isfinite(sub)]
            if len(valid) > 0:
                stats['mean'] = float(np.mean(valid))
                stats['max'] = float(np.max(valid))
                stats['p75'] = float(np.percentile(valid, 75))
                stats['p90'] = float(np.percentile(valid, 90))
            else:
                n_no_valid += 1
        else:
            n_no_valid += 1
        results.append(stats)
    print(f"  {len(results) - n_no_valid} / {len(results)} batiments avec pixel(s) valide(s)")
    return results


def compute_metrics(y_true_bin, y_pred_bin):
    """y_true_bin/y_pred_bin : listes de 0/1. Retourne dict de metriques."""
    tp = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 0 and p == 0)
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
    recall = tp / (tp + fn) if (tp + fn) > 0 else float('nan')
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else float('nan')
    po = (tp + tn) / n if n > 0 else float('nan')
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': precision, 'recall': recall, 'f1': f1, 'kappa': kappa}


# =============================================================================
# MAIN
# =============================================================================

def main():
    buildings = load_buildings_with_gt(BUILDINGS_PATH, CLASS_FIELD)

    all_results = []
    for raster_key, raster_path in RASTERS.items():
        if not raster_path or not os.path.exists(raster_path):
            print(f"Attention: raster '{raster_key}' introuvable — ignore")
            continue
        print(f"\n{SEP}")
        print(f"  Raster : {raster_key}")
        print(SEP)
        stats_list = compute_building_stats(raster_path, buildings)
        has_raster = [s['mean'] is not None for s in stats_list]
        n_covered = sum(has_raster)
        print(f"  Attention: {len(buildings) - n_covered} batiment(s) hors couverture raster "
              f"exclus du calcul (pas de donnee, pas '0 endommage')")

        for variant_name, variant_fn in GT_VARIANTS.items():
            y_true_full = [variant_fn(raw) for _, raw in buildings]
            # Un batiment n'entre dans le calcul QUE s'il est couvert par le
            # raster ET pas exclu par cette variante de verite terrain
            # (ex: 'minimal' est exclu — ni positif ni negatif — dans 'large').
            valid_idx = [i for i in range(len(buildings))
                         if has_raster[i] and y_true_full[i] is not None]
            y_true_valid = [y_true_full[i] for i in valid_idx]
            n_pos = sum(y_true_valid)
            print(f"    variante '{variant_name}': {len(valid_idx)} batiment(s) utilisables "
                  f"({n_pos} positifs)")

            for agg in AGG_METHODS:
                values = [stats_list[i][agg] for i in valid_idx]
                for thr in THRESHOLD_RANGES[raster_key]:
                    y_pred = [1 if (v is not None and v >= thr) else 0 for v in values]
                    m = compute_metrics(y_true_valid, y_pred)
                    all_results.append({
                        'raster': raster_key, 'gt_variant': variant_name,
                        'agg': agg, 'threshold': thr, **m
                    })

    all_results.sort(key=lambda r: (r['kappa'] if r['kappa'] == r['kappa'] else -999), reverse=True)

    print(f"\n{SEP}")
    print("  TOP 15 — meilleures combinaisons (raster, variante GT, agregation, seuil) par kappa")
    print(SEP)
    print(f"{'Raster':8s} {'Variante':8s} {'Agreg':6s} {'Seuil':>8s} {'Precision':>10s} {'Rappel':>8s} {'F1':>7s} {'Kappa':>7s}")
    for r in all_results[:15]:
        print(f"{r['raster']:8s} {r['gt_variant']:8s} {r['agg']:6s} {r['threshold']:8.3f} "
              f"{r['precision']:10.3f} {r['recall']:8.3f} {r['f1']:7.3f} {r['kappa']:7.3f}")

    print(f"\n{SEP}")
    print("  Meilleur seuil PAR (raster, variante GT, methode d'agregation)")
    print(SEP)
    best_per_combo = {}
    for r in all_results:
        key = (r['raster'], r['gt_variant'], r['agg'])
        if key not in best_per_combo or r['kappa'] > best_per_combo[key]['kappa']:
            best_per_combo[key] = r
    for (raster_key, variant, agg), r in sorted(best_per_combo.items(), key=lambda kv: -kv[1]['kappa']):
        rng = THRESHOLD_RANGES[raster_key]
        at_edge = r['threshold'] <= rng[0] + 1e-6 or r['threshold'] >= rng[-1] - 1e-6
        edge_warn = "  <-- ATTENTION: au bord de la plage testee, elargir THRESHOLD_RANGES !" if at_edge else ""
        print(f"  {raster_key:8s} / {variant:8s} / {agg:6s} : seuil={r['threshold']:.3f}  "
              f"kappa={r['kappa']:.3f}  F1={r['f1']:.3f}  "
              f"precision={r['precision']:.3f}  rappel={r['recall']:.3f}{edge_warn}")

    # Ecriture CSV complet
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['raster', 'gt_variant', 'agg', 'threshold', 'tp', 'fp', 'fn', 'tn',
                                           'precision', 'recall', 'f1', 'kappa'])
        w.writeheader()
        w.writerows(all_results)
    print(f"\nDetail complet ecrit : {OUT_CSV}  ({len(all_results)} combinaison(s) testee(s))")


if __name__ == '__main__':
    main()
