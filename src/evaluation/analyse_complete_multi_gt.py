# -*- coding: utf-8 -*-
"""Balayage complet des seuils et des règles d'agrégation contre deux vérités de référence, chacune restreinte à sa propre emprise d'analyse : un bâtiment situé hors de l'emprise d'une source n'est pas un vrai négatif pour elle, c'est une absence de donnée.

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

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\HOTOSM\hdx\aoi.geojson")
AOI_NAME_FIELD = "area"
COASTAL4_ZONES = ['caraballeda', 'catia_la_mar', 'la_guaira', 'el_junquito']

RASTERS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\ALL_AOI_HOTOSM\T_stat_all_zones.tif"),
    'bdpm':   os.path.join(DONNEES, r"VENEZUELA\MOI\BDPM\ALL_AOI_HOTOSM\coh_diff_fused.tif"),
}

THRESHOLD_RANGE = [round(x, 2) for x in np.arange(0.0, 6.01, 0.1)]
AGG_METHODS = ['mean', 'max', 'p75', 'p90', 'frac50']
MIN_BUILDINGS_PER_ZONE = 10

# --- Sources de verite terrain — chacune avec :
#   (chemin_batiments_joints, champ_classe_brute, mapping_vers_binaire,
#    chemin_AOI_propre_ou_None)
# Le mapping_vers_binaire prend la classe brute et retourne 1 (endommage),
# 0 (confirme non endommage), ou None (a exclure du calcul).
GT_SOURCES = {
    'chatmap': {
        'buildings_osm':      os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_OSM.gpkg"),
        'buildings_overture':  os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_proj_Overture.gpkg"),
        'class_field': 'cm_damaged',
        'gt_fn': lambda raw: 1 if raw in ('complete', 'significant', 'minimal') else (0 if raw == 'not_reported' else None),
        'own_aoi_path': os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\AOI_Chatmap_fab.gpkg"),  # AJUSTE si nom different
    },
    'ems': {
        'buildings_osm':      os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_OSM.gpkg"),
        'buildings_overture':  os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture.gpkg"),
        'class_field': 'cm_damage_gra',  # AJUSTE si le nom differe dans ton fichier joint EMS
        'gt_fn': lambda raw: (1 if raw in ('Possibly damaged', 'Damaged', 'Destroyed')
                               else (0 if raw == 'not_reported' else None)),
        'own_aoi_path': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v2.gpkg"),
    },
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\analyse_complete_multi_gt.csv")

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
    print(f"AOI de reference : {len(zones)} zone(s) — {[n for n, _ in zones]}")
    return zones


def load_aoi_union(path):
    """Charge et fusionne toutes les entites d'un fichier AOI en une seule
    geometrie."""
    if path is None or not os.path.exists(path):
        return None
    ds = ogr.Open(path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir l'AOI propre {path}")
        return None
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    geoms = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        if not g.IsValid():
            g = g.MakeValid()
        geoms.append(g)
    ds = None
    if not geoms:
        return None
    union = geoms[0]
    for g in geoms[1:]:
        union = union.Union(g)
    return union


def find_zone(centroid, aoi_zones):
    for name, geom in aoi_zones:
        if geom.Contains(centroid):
            return name
    return 'hors_aoi'


def load_buildings_restricted(path, class_field, aoi_zones, own_aoi_geom):
    """Charge les batiments, filtres SPATIALEMENT (avant chargement) sur
    l'intersection de : emprise de own_aoi_geom (si fournie) — c'est cette
    restriction precoce qui evite de charger des millions de batiments
    inutiles."""
    ds = ogr.Open(path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir {path}")
        return []
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                   for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if class_field not in field_names:
        print(f"  Attention: champ '{class_field}' introuvable. Champs: {field_names}")
        return []

    if own_aoi_geom is not None:
        env = own_aoi_geom.GetEnvelope()  # xmin,xmax,ymin,ymax
        lyr.SetSpatialFilterRect(env[0], env[2], env[1], env[3])
        print(f"  Filtre spatial applique sur l'AOI propre de la source (avant chargement)")

    out = []
    n_outside_precise = 0
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        geom = geom.Clone()
        if tr is not None:
            geom.Transform(tr)
        centroid = geom.Centroid()
        if own_aoi_geom is not None and not own_aoi_geom.Contains(centroid):
            n_outside_precise += 1
            continue  # dans le rectangle englobant mais pas dans le vrai polygone AOI
        raw = feat.GetField(class_field)
        zone = find_zone(centroid, aoi_zones)
        out.append({'geom': geom, 'raw': raw, 'zone': zone})
    ds = None
    print(f"  {len(out)} batiment(s) charge(s) et dans l'AOI propre "
          f"({n_outside_precise} exclus car dans le rectangle mais hors du vrai polygone)")
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
        return 1 if float(np.mean(px >= threshold)) >= 0.5 else 0
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
    for gt_key, gt_cfg in GT_SOURCES.items():
        own_aoi = load_aoi_union(gt_cfg.get('own_aoi_path'))
        if gt_cfg.get('own_aoi_path') and own_aoi is None:
            print(f"Attention: AOI propre de '{gt_key}' introuvable/vide — "
                  f"aucune restriction supplementaire appliquee pour cette source.")

        for bldg_source_key in ('buildings_osm', 'buildings_overture'):
            buildings_path = gt_cfg.get(bldg_source_key)
            if not buildings_path or not os.path.exists(buildings_path):
                print(f"\nAttention: '{gt_key}' / '{bldg_source_key}' introuvable — ignore")
                continue
            source_label = bldg_source_key.replace('buildings_', '')

            print(f"\n{SEP}")
            print(f"  VERITE TERRAIN : {gt_key}  |  SOURCE BATIMENTS : {source_label}")
            print(SEP)
            buildings = load_buildings_restricted(buildings_path, gt_cfg['class_field'],
                                                    aoi_zones, own_aoi)
            if not buildings:
                continue
            y_true_all = [gt_cfg['gt_fn'](b['raw']) for b in buildings]

            for raster_key, raster_path in RASTERS.items():
                if not raster_path or not os.path.exists(raster_path):
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

                scopes = {'GLOBAL': valid_indices(None), 'COASTAL4': valid_indices(COASTAL4_ZONES)}
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
                            all_results.append({'gt_source': gt_key, 'building_source': source_label,
                                                 'scope': scope_name, 'raster': raster_key,
                                                 'agg': agg, 'threshold': thr, **m})

    print(f"\n{SEP}")
    print(f"  {len(all_results)} combinaison(s) calculee(s) — ecriture du CSV")
    print(SEP)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ['gt_source', 'building_source', 'scope', 'raster', 'agg', 'threshold',
                  'tp', 'fp', 'fn', 'tn', 'n', 'precision', 'recall', 'f1', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_results)
    print(f"Ecrit : {OUT_CSV}")

    def top_by_kappa(rows, n=8):
        return sorted(rows, key=lambda r: (r['kappa'] if r['kappa'] == r['kappa'] else -999), reverse=True)[:n]

    for gt_key in GT_SOURCES:
        for scope_wanted in ('GLOBAL', 'COASTAL4'):
            rows = [r for r in all_results if r['gt_source'] == gt_key and r['scope'] == scope_wanted]
            if not rows:
                continue
            print(f"\n{SEP}")
            print(f"  TOP — gt_source={gt_key}, scope={scope_wanted}")
            print(SEP)
            print(f"{'Bat.src':10s} {'Raster':8s} {'Agreg':7s} {'Seuil':>6s} {'Prec':>6s} {'Rappel':>7s} {'F1':>6s} {'Kappa':>7s}")
            for r in top_by_kappa(rows):
                print(f"{r['building_source']:10s} {r['raster']:8s} {r['agg']:7s} {r['threshold']:6.2f} "
                      f"{r['precision']:6.3f} {r['recall']:7.3f} {r['f1']:6.3f} {r['kappa']:7.3f}")


if __name__ == '__main__':
    main()
