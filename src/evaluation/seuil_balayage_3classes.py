# -*- coding: utf-8 -*-
"""Recherche du meilleur couple de seuils pour classer chaque bâtiment en trois niveaux — intact, endommagé, détruit — au lieu du partage binaire habituel.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
from collections import Counter
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

# Fichier OSM-joint-ChatMap (deja valide) — pas besoin d'Overture pour cette
# etape, on ne fait que des statistiques de zone sur le raster.
BUILDINGS_PATH = os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_OSM.gpkg")

CLASS_FIELD = "cm_damaged"  # complete/significant/minimal/not_reported

CLASS_MAP_3 = {
    'complete': 'destroyed',
    'significant': 'damaged',
    'minimal': 'damaged',
    'not_reported': 'no_damage',
}

RASTERS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\T_stat [Caraballeda].tif"),
    'bdpm':   os.path.join(DONNEES, r"VENEZUELA\MOI\BDPM\Caraballeda\coh_diff_fused.tif"),
}

# Gammes de seuils BAS (deja calibrees par le balayage binaire precedent —
# on resserre autour de l'optimum trouve plutot que de tout rebalayer)
LOW_THRESHOLD_RANGES = {
    't_test': [round(x, 2) for x in np.arange(2.5, 4.51, 0.1)],
    'bdpm':   [round(x, 3) for x in np.arange(0.40, 0.81, 0.02)],
}

# Gammes de seuils HAUT (destroyed) — a explorer plus largement, au-dessus
# du seuil bas
HIGH_THRESHOLD_RANGES = {
    't_test': [round(x, 2) for x in np.arange(3.0, 6.01, 0.2)],
    'bdpm':   [round(x, 3) for x in np.arange(0.50, 0.91, 0.04)],
}

AGG_METHODS = ['mean', 'max', 'p75', 'p90']

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\test_seuil\seuilOSM_balayage_3classes.csv")

SEP = "=" * 70

# =============================================================================
# HELPERS (repris de seuil_balayage_chatmap.py)
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


def load_buildings_with_class(path, class_field):
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
        gt3 = CLASS_MAP_3.get(raw, 'no_damage') if raw is not None else 'no_damage'
        out.append((geom, gt3))
    ds = None
    print(f"Batiments charges : {len(out)}  — repartition 3 classes: {dict(Counter(g for _, g in out))}")
    return out


def compute_building_stats(raster_path, buildings):
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
    for geom, gt3 in buildings:
        env = geom.GetEnvelope()
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


def classify_3(value, low, high):
    if value is None:
        return None
    if value >= high:
        return 'destroyed'
    if value >= low:
        return 'damaged'
    return 'no_damage'


def multiclass_kappa(y_true, y_pred, labels=('no_damage', 'damaged', 'destroyed')):
    """Kappa de Cohen generalise au cas multi-classe (meme formule, matrice
    de confusion NxN)."""
    idx = {l: i for i, l in enumerate(labels)}
    n = len(y_true)
    cm = np.zeros((len(labels), len(labels)))
    for t, p in zip(y_true, y_pred):
        cm[idx[t], idx[p]] += 1
    po = np.trace(cm) / n
    pe = sum((cm[i, :].sum() / n) * (cm[:, i].sum() / n) for i in range(len(labels)))
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return kappa, po, cm


# =============================================================================
# MAIN
# =============================================================================

def main():
    buildings = load_buildings_with_class(BUILDINGS_PATH, CLASS_FIELD)
    y_true_full = [g for _, g in buildings]

    all_results = []
    for raster_key, raster_path in RASTERS.items():
        if not raster_path or not os.path.exists(raster_path):
            print(f"Attention: raster '{raster_key}' introuvable — ignore")
            continue
        print(f"\n{SEP}")
        print(f"  Raster : {raster_key}")
        print(SEP)
        stats_list = compute_building_stats(raster_path, buildings)
        valid_idx = [i for i, s in enumerate(stats_list) if s['mean'] is not None]
        y_true_valid = [y_true_full[i] for i in valid_idx]
        print(f"  {len(valid_idx)} batiment(s) utilisables (hors couverture raster exclus)")

        for agg in AGG_METHODS:
            values = [stats_list[i][agg] for i in valid_idx]
            for low in LOW_THRESHOLD_RANGES[raster_key]:
                for high in HIGH_THRESHOLD_RANGES[raster_key]:
                    if high <= low:
                        continue  # seuil haut doit etre strictement au-dessus du bas
                    y_pred = [classify_3(v, low, high) for v in values]
                    kappa, po, cm = multiclass_kappa(y_true_valid, y_pred)
                    all_results.append({
                        'raster': raster_key, 'agg': agg,
                        'low': low, 'high': high, 'kappa': kappa, 'accord': po,
                        'n_no_damage_pred': sum(1 for p in y_pred if p == 'no_damage'),
                        'n_damaged_pred': sum(1 for p in y_pred if p == 'damaged'),
                        'n_destroyed_pred': sum(1 for p in y_pred if p == 'destroyed'),
                    })

    all_results.sort(key=lambda r: (r['kappa'] if r['kappa'] == r['kappa'] else -999), reverse=True)

    print(f"\n{SEP}")
    print("  TOP 15 — meilleures combinaisons (raster, agregation, seuil_bas, seuil_haut)")
    print(SEP)
    print(f"{'Raster':8s} {'Agreg':6s} {'Bas':>7s} {'Haut':>7s} {'Accord':>8s} {'Kappa':>7s}  "
          f"{'n_no_dmg':>9s} {'n_dmg':>7s} {'n_destr':>8s}")
    for r in all_results[:15]:
        print(f"{r['raster']:8s} {r['agg']:6s} {r['low']:7.3f} {r['high']:7.3f} "
              f"{100*r['accord']:7.1f}% {r['kappa']:7.3f}  "
              f"{r['n_no_damage_pred']:9d} {r['n_damaged_pred']:7d} {r['n_destroyed_pred']:8d}")

    print(f"\n{SEP}")
    print("  Meilleure paire de seuils PAR (raster, agregation)")
    print(SEP)
    best_per_combo = {}
    for r in all_results:
        key = (r['raster'], r['agg'])
        if key not in best_per_combo or r['kappa'] > best_per_combo[key]['kappa']:
            best_per_combo[key] = r
    for (raster_key, agg), r in sorted(best_per_combo.items(), key=lambda kv: -kv[1]['kappa']):
        low_rng, high_rng = LOW_THRESHOLD_RANGES[raster_key], HIGH_THRESHOLD_RANGES[raster_key]
        at_edge = (r['low'] <= low_rng[0]+1e-6 or r['low'] >= low_rng[-1]-1e-6 or
                   r['high'] <= high_rng[0]+1e-6 or r['high'] >= high_rng[-1]-1e-6)
        warn = "  <-- bord de plage, elargir !" if at_edge else ""
        print(f"  {raster_key:8s} / {agg:6s} : bas={r['low']:.3f}  haut={r['high']:.3f}  "
              f"kappa={r['kappa']:.3f}  accord={100*r['accord']:.1f}%{warn}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['raster', 'agg', 'low', 'high', 'kappa', 'accord',
                                           'n_no_damage_pred', 'n_damaged_pred', 'n_destroyed_pred'])
        w.writeheader()
        w.writerows(all_results)
    print(f"\nDetail complet ecrit : {OUT_CSV}  ({len(all_results)} combinaison(s) testee(s))")


if __name__ == '__main__':
    main()
