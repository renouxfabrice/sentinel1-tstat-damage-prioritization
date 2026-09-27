# -*- coding: utf-8 -*-
"""Balayage seuil par règle d'agrégation, zone par zone et sur deux sources d'empreintes en un seul passage, la zone de chaque bâtiment étant déterminée par jointure spatiale réelle avec la couche d'emprise.

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

BUILDINGS_PATHS = {
    #'osm':      os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_OSM.gpkg"),
    'overture': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture_v3_AOI.gpkg")
}

CLASS_FIELD = "cm_damage_gra"  # complete/significant/minimal/not_reported

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v3.gpkg")
AOI_NAME_FIELD = "area"

RASTERS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif"),
    'bdpm':   os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\coh_diff_fused.tif"),
}

THRESHOLD_RANGES = {
    't_test': [round(x, 2) for x in np.arange(1.0, 6.01, 0.1)],
    'bdpm':   [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)],
}

AGG_METHODS = ['mean', 'max', 'p75', 'p90']

GT_VARIANTS = {
    'all': lambda raw: 1 if raw in ('complete', 'significant', 'minimal') else (0 if raw == 'not_reported' else None),
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\seuil_balayage_par_zone_multisource.csv")

MIN_BUILDINGS_PER_ZONE = 10  # en dessous, zone ignoree (pas assez fiable)

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


def load_aoi_zones(path, name_field):
    """Charge les polygones AOI. Retourne liste de (nom, geometrie)."""
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir l'AOI : {path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                   for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if name_field not in field_names:
        sys.exit(f"Erreur: champ '{name_field}' introuvable dans l'AOI. Champs: {field_names}")
    zones = []
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        geom = geom.Clone()
        if tr is not None:
            geom.Transform(tr)
        zones.append((feat.GetField(name_field), geom))
    ds = None
    print(f"AOI chargee : {len(zones)} zone(s) — {[n for n, _ in zones]}")
    return zones


def find_zone(centroid, aoi_zones):
    for name, geom in aoi_zones:
        if geom.Contains(centroid):
            return name
    return 'hors_aoi'


def load_buildings(path, class_field, aoi_zones):
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
        zone = find_zone(geom.Centroid(), aoi_zones)
        out.append((geom, raw, zone))
    ds = None
    print(f"  {len(out)} batiment(s) charge(s) — repartition par zone AOI: "
          f"{dict(Counter(z for _, _, z in out))}")
    print(f"  repartition classe brute: {dict(Counter(r for _, r, _ in out))}")
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
    for geom, raw, zone in buildings:
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
    print(f"    {len(results) - n_no_valid} / {len(results)} batiments avec pixel(s) valide(s)")
    return results


def compute_metrics(y_true_bin, y_pred_bin):
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
    aoi_zones = load_aoi_zones(AOI_PATH, AOI_NAME_FIELD)
    zone_names = [n for n, _ in aoi_zones]

    all_results = []
    for source_key, buildings_path in BUILDINGS_PATHS.items():
        if not buildings_path or not os.path.exists(buildings_path):
            print(f"Attention: source '{source_key}' introuvable — ignoree")
            continue
        print(f"\n{SEP}")
        print(f"  SOURCE : {source_key}")
        print(SEP)
        buildings = load_buildings(buildings_path, CLASS_FIELD, aoi_zones)

        for raster_key, raster_path in RASTERS.items():
            if not raster_path or not os.path.exists(raster_path):
                print(f"Attention: raster '{raster_key}' introuvable — ignore")
                continue
            print(f"\n  Raster : {raster_key}")
            stats_list = compute_building_stats(raster_path, buildings)
            has_raster = [s['mean'] is not None for s in stats_list]
            print(f"    {len(buildings) - sum(has_raster)} batiment(s) hors couverture raster exclus")

            for variant_name, variant_fn in GT_VARIANTS.items():
                y_true_full = [variant_fn(raw) for _, raw, _ in buildings]

                # GLOBAL
                valid_idx = [i for i in range(len(buildings))
                             if has_raster[i] and y_true_full[i] is not None]
                y_true_valid = [y_true_full[i] for i in valid_idx]
                for agg in AGG_METHODS:
                    values = [stats_list[i][agg] for i in valid_idx]
                    for thr in THRESHOLD_RANGES[raster_key]:
                        y_pred = [1 if (v is not None and v >= thr) else 0 for v in values]
                        m = compute_metrics(y_true_valid, y_pred)
                        all_results.append({'source': source_key, 'scope': 'GLOBAL',
                                             'raster': raster_key, 'gt_variant': variant_name,
                                             'agg': agg, 'threshold': thr, **m})

                # PAR ZONE
                for zone in zone_names:
                    zone_idx = [i for i in range(len(buildings))
                                if has_raster[i] and y_true_full[i] is not None
                                and buildings[i][2] == zone]
                    if len(zone_idx) < MIN_BUILDINGS_PER_ZONE:
                        continue
                    y_true_zone = [y_true_full[i] for i in zone_idx]
                    for agg in AGG_METHODS:
                        values = [stats_list[i][agg] for i in zone_idx]
                        for thr in THRESHOLD_RANGES[raster_key]:
                            y_pred = [1 if (v is not None and v >= thr) else 0 for v in values]
                            m = compute_metrics(y_true_zone, y_pred)
                            all_results.append({'source': source_key, 'scope': zone,
                                                 'raster': raster_key, 'gt_variant': variant_name,
                                                 'agg': agg, 'threshold': thr, **m})

    all_results.sort(key=lambda r: (r['kappa'] if r['kappa'] == r['kappa'] else -999), reverse=True)

    print(f"\n{SEP}")
    print("  TOP 15 GLOBAL — les deux sources confondues, classees par kappa")
    print(SEP)
    global_results = [r for r in all_results if r['scope'] == 'GLOBAL']
    print(f"{'Source':10s} {'Raster':8s} {'Agreg':6s} {'Seuil':>8s} {'Precision':>10s} {'Rappel':>8s} {'F1':>7s} {'Kappa':>7s}")
    for r in global_results[:15]:
        print(f"{r['source']:10s} {r['raster']:8s} {r['agg']:6s} {r['threshold']:8.3f} "
              f"{r['precision']:10.3f} {r['recall']:8.3f} {r['f1']:7.3f} {r['kappa']:7.3f}")

    print(f"\n{SEP}")
    print("  Meilleure combinaison PAR (source, zone)")
    print(SEP)
    best_per_combo = {}
    for r in all_results:
        if r['scope'] == 'GLOBAL':
            continue
        key = (r['source'], r['scope'])
        if key not in best_per_combo or r['kappa'] > best_per_combo[key]['kappa']:
            best_per_combo[key] = r
    for (source, zone), r in sorted(best_per_combo.items(), key=lambda kv: -kv[1]['kappa']):
        print(f"  {source:10s} / {zone:20s} : {r['raster']:8s}/{r['agg']:6s} seuil={r['threshold']:.3f}  "
              f"kappa={r['kappa']:.3f}  F1={r['f1']:.3f}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'scope', 'raster', 'gt_variant', 'agg', 'threshold',
                                           'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'f1', 'kappa'])
        w.writeheader()
        w.writerows(all_results)
    print(f"\nDetail complet ecrit : {OUT_CSV}  ({len(all_results)} combinaison(s))")


if __name__ == '__main__':
    main()
