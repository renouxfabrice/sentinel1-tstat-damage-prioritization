# -*- coding: utf-8 -*-
"""Balayage des seuils de 0 à 6 et de toutes les règles d'agrégation du pixel au bâtiment, contre la vérité Copernicus EMS, à trois niveaux de portée : global, zones côtières, et zone par zone.

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
    'osm':      os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_OSM.gpkg"),
    'overture': os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_Overture.gpkg"),
}

CLASS_FIELD = "cm_damaged"

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\MOI\BDPM\ALL_AOI_HOTOSM\aoi.geojson")
AOI_NAME_FIELD = "area"

COASTAL4_ZONES = ['caraballeda', 'catia_la_mar', 'la_guaira', 'el_junquito']

RASTERS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\ALL_AOI_HOTOSM\T_stat_all_zones.tif"),
    'bdpm':   os.path.join(DONNEES, r"VENEZUELA\MOI\BDPM\ALL_AOI_HOTOSM\coh_diff_fused.tif"),
}

THRESHOLD_RANGE = [round(x, 2) for x in np.arange(0.0, 6.01, 0.1)]

AGG_METHODS = ['mean', 'max', 'p75', 'p90', 'frac50']

GT_FN = lambda raw: 1 if raw in ('complete', 'significant', 'minimal') else (0 if raw == 'not_reported' else None)

MIN_BUILDINGS_PER_ZONE = 10

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\analyse_complete_seuils.csv")

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
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir l'AOI : {path}")
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
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
        sys.exit(f"Erreur: champ '{class_field}' introuvable. Champs: {field_names}")

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
        out.append({'geom': geom, 'raw': raw, 'zone': zone})
    ds = None
    print(f"  {len(out)} batiment(s) charge(s) — zones: {dict(Counter(b['zone'] for b in out))}")
    return out


def compute_building_pixel_arrays(raster_path, buildings):
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

    n_no_valid = 0
    for b in buildings:
        env = b['geom'].GetEnvelope()
        px0 = max(0, int((env[0] - gt[0]) / gt[1]))
        px1 = min(nx - 1, int((env[1] - gt[0]) / gt[1]))
        py0 = max(0, int((env[3] - gt[3]) / gt[5]))
        py1 = min(ny - 1, int((env[2] - gt[3]) / gt[5]))
        b['pixels'] = None
        if px0 <= px1 and py0 <= py1:
            sub = arr[py0:py1 + 1, px0:px1 + 1]
            valid = sub[np.isfinite(sub)]
            if len(valid) > 0:
                b['pixels'] = valid
            else:
                n_no_valid += 1
        else:
            n_no_valid += 1
    print(f"    {len(buildings) - n_no_valid} / {len(buildings)} batiments avec pixel(s) valide(s)")
    return n_no_valid


def classify(building, agg, threshold):
    px = building['pixels']
    if px is None:
        return None
    if agg == 'mean':
        return 1 if float(np.mean(px)) >= threshold else 0
    if agg == 'max':
        return 1 if float(np.max(px)) >= threshold else 0
    if agg == 'p75':
        return 1 if float(np.percentile(px, 75)) >= threshold else 0
    if agg == 'p90':
        return 1 if float(np.percentile(px, 90)) >= threshold else 0
    if agg == 'frac50':
        frac = float(np.mean(px >= threshold))
        return 1 if frac >= 0.5 else 0
    raise ValueError(agg)


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
    recall = tp / (tp + fn) if (tp + fn) > 0 else float('nan')
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 and precision == precision and recall == recall else float('nan'))
    po = (tp + tn) / n if n > 0 else float('nan')
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'n': n,
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
        y_true_all = [GT_FN(b['raw']) for b in buildings]

        for raster_key, raster_path in RASTERS.items():
            if not raster_path or not os.path.exists(raster_path):
                print(f"Attention: raster '{raster_key}' introuvable — ignore")
                continue
            print(f"\n  Raster : {raster_key}")
            compute_building_pixel_arrays(raster_path, buildings)

            def valid_indices(zone_filter=None):
                out = []
                for i, b in enumerate(buildings):
                    if b['pixels'] is None or y_true_all[i] is None:
                        continue
                    if zone_filter is not None and b['zone'] not in zone_filter:
                        continue
                    out.append(i)
                return out

            scopes = {'GLOBAL': valid_indices(None),
                      'COASTAL4': valid_indices(COASTAL4_ZONES)}
            for zn in zone_names:
                idx = valid_indices([zn])
                if len(idx) >= MIN_BUILDINGS_PER_ZONE:
                    scopes[zn] = idx

            for scope_name, idx_list in scopes.items():
                y_true_scope = [y_true_all[i] for i in idx_list]
                buildings_scope = [buildings[i] for i in idx_list]
                for agg in AGG_METHODS:
                    for thr in THRESHOLD_RANGE:
                        y_pred = [classify(b, agg, thr) for b in buildings_scope]
                        m = compute_metrics(y_true_scope, y_pred)
                        all_results.append({'source': source_key, 'scope': scope_name,
                                             'raster': raster_key, 'agg': agg,
                                             'threshold': thr, **m})

    print(f"\n{SEP}")
    print(f"  {len(all_results)} combinaison(s) calculee(s) — ecriture du CSV complet")
    print(SEP)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['source', 'scope', 'raster', 'agg', 'threshold',
                  'tp', 'fp', 'fn', 'tn', 'n', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_results)
    print(f"Ecrit : {OUT_CSV}")

    def top_by_kappa(rows, n=10):
        return sorted(rows, key=lambda r: (r['kappa'] if r['kappa'] == r['kappa'] else -999), reverse=True)[:n]

    for scope_wanted in ('GLOBAL', 'COASTAL4'):
        print(f"\n{SEP}")
        print(f"  TOP 10 — scope={scope_wanted}, tries par kappa")
        print(SEP)
        rows = [r for r in all_results if r['scope'] == scope_wanted]
        print(f"{'Source':10s} {'Raster':8s} {'Agreg':7s} {'Seuil':>6s} {'Prec':>6s} {'Rappel':>7s} {'F1':>6s} {'Kappa':>7s}")
        for r in top_by_kappa(rows):
            print(f"{r['source']:10s} {r['raster']:8s} {r['agg']:7s} {r['threshold']:6.2f} "
                  f"{r['precision']:6.3f} {r['recall']:7.3f} {r['f1']:6.3f} {r['kappa']:7.3f}")


if __name__ == '__main__':
    main()
