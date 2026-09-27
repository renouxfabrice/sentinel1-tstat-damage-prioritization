# -*- coding: utf-8 -*-
"""Évaluation du raster T-stat sur le cas cyclonique : quatre règles d'agrégation par bâtiment, deux sources d'empreintes et deux vérités de référence, sans jamais recalculer le raster.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import math
import numpy as np
from config import DONNEES, WHITEHOUSE

try:
    from osgeo import ogr, osr, gdal
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()
gdal.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

T_STAT_RASTER = os.path.join(DONNEES, r"JAMAIQUE\AOI\T_test_aoi.tif")
T_STAT_AOI = os.path.join(DONNEES, r"JAMAIQUE\AOI\AOI_t_test.gpkg")

BUILDING_SOURCES = {
    'osm':           os.path.join(DONNEES, r"JAMAIQUE\AOI\OSM_AOI_ttest.gpkg"),
    'open_buildings': os.path.join(DONNEES, r"JAMAIQUE\AOI\Open_Building_AOI_t_test.gpkg"),
}

# Chaque entree = une verite terrain sur sa PROPRE emprise. Ajouter une
# entree ici pour tester une nouvelle zone/source sans toucher au reste.
GROUND_TRUTH_SOURCES = {
    'UNOSAT': dict(
        extent=os.path.join(WHITEHOUSE, r"UNOSAT\_static_unosat_filesystem_4215_TC20251028JAM_SHP\TC20251028JAM_SHP\AP_20251031_AnalysisExtent_WhiteHouse.shp"),
        points=os.path.join(WHITEHOUSE, r"UNOSAT\_static_unosat_filesystem_4215_TC20251028JAM_SHP\TC20251028JAM_SHP\AP_20251031_Damagedbuilding_WhiteHouse.shp"),
        field="Main_Damag",
        rules={'damaged': [13], 'destroyed': [1]},
    ),
    'EMS': dict(
        extent=os.path.join(WHITEHOUSE, r"UNOSAT\EMSR847_AOI39_GRA_PRODUCT_v1\EMSR847_AOI39_GRA_PRODUCT_areaOfInterestA_v1.shp"),
        points=os.path.join(WHITEHOUSE, r"UNOSAT\EMSR847_AOI39_GRA_PRODUCT_v1\EMSR847_AOI39_GRA_PRODUCT_builtUpP_v1.shp"),
        field="damage_gra",
        rules={'damaged': ['Damaged', 'Possibly damaged'], 'destroyed': ['Destroyed']},
    ),
}

# Portees testees en plus de l'emprise complete de chaque verite terrain —
# ajouter une entree ici pour tester une autre sous-zone sans rien
# recalculer (None = pas de restriction supplementaire).
ZONES = {
    'global':  None,
    'zone1':   os.path.join(WHITEHOUSE, r"test_appli\Rapid_Damage_Detection\Witehouse\creation sample test\Zone_1_AOI.shp"),
}

SNAP_DISTANCE_M = 20.0
T_THRESHOLDS = [round(x, 3) for x in np.arange(0.5, 6.01, 0.05)]
AGGREGATIONS = ['mean', 'max', 'median', 'p90']

OUT_DIR = os.path.join(DONNEES, r"JAMAIQUE\Livrable")
OUT_CSV = os.path.join(OUT_DIR, "jamaique_seuils_tstat_agregations.csv")

SEP = "=" * 70

WGS84 = osr.SpatialReference()
WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

# =============================================================================
# HELPERS
# =============================================================================

def get_transform_to_wgs84(lyr):
    src_srs = lyr.GetSpatialRef()
    if src_srs is None:
        return None
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if src_srs.IsSame(WGS84):
        return None
    return osr.CoordinateTransformation(src_srs, WGS84)


def load_single_geom_wgs84(path):
    if not os.path.exists(path):
        print(f"    ATTENTION — introuvable : {path}")
        return None
    ds = ogr.Open(path)
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


def get_bounds(geom):
    env = geom.GetEnvelope()
    return env[0], env[2], env[1], env[3]


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def classify_raw_value(rules, raw):
    if raw is None:
        return None
    if raw in (rules.get('excluded') or []):
        return None
    if raw in (rules.get('destroyed') or []):
        return 2
    if raw in (rules.get('damaged') or []):
        return 1
    return 0


def load_points_classified(path, field, rules, aoi_bounds):
    if not os.path.exists(path):
        print(f"    ATTENTION — introuvable : {path}")
        return []
    ds = ogr.Open(path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        pt = g if g.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else g.Centroid()
        if tr is not None:
            pt = pt.Clone(); pt.Transform(tr)
        raw = feat.GetField(field)
        sev = classify_raw_value(rules, raw)
        if sev is None:
            continue
        out.append((pt.GetY(), pt.GetX(), sev))
    ds = None
    return out


def load_buildings_wgs84(path, aoi_bounds):
    if not os.path.exists(path):
        print(f"    ATTENTION — introuvable : {path}")
        return {}
    ds = ogr.Open(path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for i, feat in enumerate(lyr):
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        out[i] = g2
    ds = None
    return out


def snap_points_to_buildings(points, buildings, snap_dist_m):
    bucket_size = 0.0015
    buckets = {}
    for idx, (lat, lon, sev) in enumerate(points):
        key = (int(lon / bucket_size), int(lat / bucket_size))
        buckets.setdefault(key, []).append(idx)
    out = {}
    for bid, geom in buildings.items():
        c = geom.Centroid()
        clat, clon = c.GetY(), c.GetX()
        bx, by = int(clon / bucket_size), int(clat / bucket_size)
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand.extend(buckets.get((bx + dx, by + dy), []))
        best_sev, best_dist = None, snap_dist_m
        for idx in cand:
            plat, plon, sev = points[idx]
            d = haversine_m(clat, clon, plat, plon)
            if d <= best_dist:
                if best_sev is None or sev > best_sev or (sev == best_sev and d < best_dist):
                    best_sev = 1 if sev > 0 else 0
                    best_dist = d
        out[bid] = best_sev if best_sev is not None else 0
    return out


def compute_stats_per_building(raster_path, buildings):
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

    out = {}
    for bid, geom in buildings.items():
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
        stats = {a: None for a in AGGREGATIONS}
        if px0 <= px1 and py0 <= py1:
            sub = band.ReadAsArray(px0, py0, px1 - px0 + 1, py1 - py0 + 1)
            if sub is not None:
                sub = sub.astype(np.float64)
                if nd is not None:
                    sub[np.isclose(sub, nd)] = np.nan
                valid = sub[np.isfinite(sub)]
                if len(valid) > 0:
                    stats['mean'] = float(np.mean(valid))
                    stats['max'] = float(np.max(valid))
                    stats['median'] = float(np.median(valid))
                    stats['p90'] = float(np.percentile(valid, 90))
        out[bid] = stats
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


def compute_auc(y_true, vals):
    pos = vals[y_true == 1]; neg = vals[y_true == 0]
    pos = pos[np.isfinite(pos)]; neg = neg[np.isfinite(neg)]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    count = 0
    for p in pos:
        count += np.sum(p > neg) + 0.5 * np.sum(p == neg)
    return count / (len(pos) * len(neg))


def find_best_threshold(y_true, vals, thresholds):
    best = None
    for thr in thresholds:
        pred = (vals >= thr).astype(int)
        m = compute_metrics_np(y_true, pred)
        if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
            best = {'seuil': thr, **m}
    return best


# =============================================================================
# MAIN
# =============================================================================

def get_raster_bounds_wgs84(raster_path):
    """Derive la boite englobante du raster directement depuis son
    geotransform + CRS — plus fiable qu'un fichier AOI separe (evite
    tout bug de projection non definie/mal geree sur ce dernier)."""
    ds = gdal.Open(raster_path)
    gt = ds.GetGeoTransform()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    xmin, ymax = gt[0], gt[3]
    xmax = xmin + nx * gt[1]
    ymin = ymax + ny * gt[5]
    prj = ds.GetProjection()
    if prj:
        raster_srs = osr.SpatialReference(); raster_srs.ImportFromWkt(prj)
        raster_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not raster_srs.IsSame(WGS84):
            tr = osr.CoordinateTransformation(raster_srs, WGS84)
            p1 = tr.TransformPoint(xmin, ymin)
            p2 = tr.TransformPoint(xmax, ymax)
            xmin, xmax = sorted([p1[0], p2[0]])
            ymin, ymax = sorted([p1[1], p2[1]])
    ds = None
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]:
        ring.AddPoint(x, y)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly, (xmin, ymin, xmax, ymax)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    if not os.path.exists(T_STAT_RASTER):
        sys.exit(f"ERREUR — raster T-stat introuvable : {T_STAT_RASTER}")

    print(f"{SEP}\n  Emprise du raster T-stat (lue directement dans le .tif)\n{SEP}")
    tstat_aoi_geom, tstat_bounds = get_raster_bounds_wgs84(T_STAT_RASTER)
    print(f"  Bornes WGS84 raster : xmin={tstat_bounds[0]:.4f} ymin={tstat_bounds[1]:.4f} "
          f"xmax={tstat_bounds[2]:.4f} ymax={tstat_bounds[3]:.4f}")

    print(f"\n{SEP}\n  DIAGNOSTIC — bornes de chaque verite terrain\n{SEP}")
    for gt_name, cfg in GROUND_TRUTH_SOURCES.items():
        g = load_single_geom_wgs84(cfg['extent'])
        if g is None:
            print(f"  [{gt_name}] emprise introuvable")
            continue
        b = get_bounds(g)
        print(f"  [{gt_name}] bornes WGS84 : xmin={b[0]:.4f} ymin={b[1]:.4f} xmax={b[2]:.4f} ymax={b[3]:.4f}")
        overlap = not (b[2] < tstat_bounds[0] or b[0] > tstat_bounds[2] or b[3] < tstat_bounds[1] or b[1] > tstat_bounds[3])
        print(f"    -> chevauchement avec le raster : {'OUI' if overlap else 'NON — CRS ou fichier suspect'}")

    zone_geoms = {}
    for zname, zpath in ZONES.items():
        zone_geoms[zname] = load_single_geom_wgs84(zpath) if zpath else None
        if zpath and zone_geoms[zname] is None:
            print(f"\n  ATTENTION — zone '{zname}' introuvable ({zpath}) — sera ignoree")

    rows = []
    for bsrc_name, bsrc_path in BUILDING_SOURCES.items():
        print(f"\n{SEP}\n  Source de batiments : {bsrc_name}\n{SEP}")

        for gt_name, cfg in GROUND_TRUTH_SOURCES.items():
            gt_extent = load_single_geom_wgs84(cfg['extent'])
            if gt_extent is None:
                print(f"  [{gt_name}] emprise introuvable — ignore")
                continue
            gt_scope_base = gt_extent.Intersection(tstat_aoi_geom) if tstat_aoi_geom is not None else gt_extent

            for zname, zgeom in zone_geoms.items():
                if ZONES.get(zname) and zgeom is None:
                    continue  # zone demandee mais fichier manquant
                scope_geom = gt_scope_base.Intersection(zgeom) if zgeom is not None else gt_scope_base
                if scope_geom is None or scope_geom.IsEmpty():
                    print(f"  [{gt_name}][{zname}] AUCUNE intersection — ignore")
                    continue
                bounds = get_bounds(scope_geom)

                buildings = load_buildings_wgs84(bsrc_path, bounds)
                if not buildings:
                    print(f"  [{gt_name}][{zname}] aucun batiment {bsrc_name} charge — ignore")
                    continue
                gt_points = load_points_classified(cfg['points'], cfg['field'], cfg['rules'], bounds)
                y_true_dict = snap_points_to_buildings(gt_points, buildings, SNAP_DISTANCE_M)

                stats = compute_stats_per_building(T_STAT_RASTER, buildings)

                common_ids = list(buildings.keys())
                y_true = np.array([y_true_dict.get(bid, 0) for bid in common_ids])

                print(f"\n  [{gt_name}][{zname}] {bsrc_name} : {len(common_ids):,} batiment(s), "
                      f"{int(y_true.sum()):,} endommage(s) (accroches a {SNAP_DISTANCE_M:.0f}m, "
                      f"{len(gt_points):,} signalement(s) source)")

                for agg in AGGREGATIONS:
                    vals = np.array([stats[bid][agg] if stats[bid][agg] is not None else np.nan for bid in common_ids])
                    v = np.isfinite(vals)
                    if v.sum() < 10 or y_true[v].sum() == 0:
                        print(f"    {agg:7s} : pas assez de donnees")
                        continue
                    auc = compute_auc(y_true[v], vals[v])
                    best = find_best_threshold(y_true[v].astype(int), vals[v], T_THRESHOLDS)
                    print(f"    {agg:7s} : AUC={auc:.4f}  seuil_opt={best['seuil']:.2f}  "
                          f"kappa={best['kappa']:.4f}  tp={best['tp']}  fp={best['fp']}  n={best['n']}")
                    rows.append({'source_batiments': bsrc_name, 'verite_terrain': gt_name, 'zone': zname,
                                  'agregation': agg, 'auc': round(auc, 4), **best})

    fieldnames = ['source_batiments', 'verite_terrain', 'zone', 'agregation', 'auc', 'seuil',
                  'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
