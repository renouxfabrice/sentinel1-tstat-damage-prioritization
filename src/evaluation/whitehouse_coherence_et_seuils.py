# -*- coding: utf-8 -*-
"""Accord entre deux vérités de référence indépendantes sur grille hexagonale, restreint à l'intersection de leurs emprises d'analyse, puis recherche du seuil optimal du T-stat contre chacune d'elles séparément.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import math
import numpy as np
from config import WHITEHOUSE

try:
    from osgeo import ogr, osr, gdal
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()
gdal.UseExceptions()

try:
    import h3
    _H3_V4 = hasattr(h3, 'polygon_to_cells')
except ImportError:
    h3 = None

AOI_ZONE1_TEST = os.path.join(WHITEHOUSE, r"test_appli\Rapid_Damage_Detection\Witehouse\creation sample test\Zone_1_AOI.shp")
UNOSAT_ANALYSIS_EXTENT = os.path.join(WHITEHOUSE, r"UNOSAT\_static_unosat_filesystem_4215_TC20251028JAM_SHP\TC20251028JAM_SHP\AP_20251031_AnalysisExtent_WhiteHouse.shp")
EMS_AOI = os.path.join(WHITEHOUSE, r"UNOSAT\EMSR847_AOI39_GRA_PRODUCT_v1\EMSR847_AOI39_GRA_PRODUCT_areaOfInterestA_v1.shp")

UNOSAT_POINTS = os.path.join(WHITEHOUSE, r"UNOSAT\_static_unosat_filesystem_4215_TC20251028JAM_SHP\TC20251028JAM_SHP\AP_20251031_Damagedbuilding_WhiteHouse.shp")
UNOSAT_FIELD = "Main_Damag"
UNOSAT_RULES = {'damaged': [13], 'destroyed': [1]}

EMS_POINTS = os.path.join(WHITEHOUSE, r"UNOSAT\EMSR847_AOI39_GRA_PRODUCT_v1\EMSR847_AOI39_GRA_PRODUCT_builtUpP_v1.shp")
EMS_FIELD = "damage_gra"
EMS_RULES = {'damaged': ['Damaged', 'Possibly damaged'], 'destroyed': ['Destroyed']}

BUILDING_SOURCES = {
    'open_buildings': os.path.join(WHITEHOUSE, r"Source Batis\open_bulding_whitehouse.gpkg"),
    'osm':            os.path.join(WHITEHOUSE, r"Source Batis\osm_whitehouse.gpkg"),
}

T_STAT_RASTER_PATH = os.path.join(WHITEHOUSE, r"Livrable\tstat_raster.tif")  # <-- A VERIFIER/COMPLETER

SNAP_DISTANCE_M = 20.0
H3_RESOLUTION = 12

T_THRESHOLDS = [round(x, 3) for x in np.arange(0.5, 6.01, 0.05)]

OUT_DIR = os.path.join(WHITEHOUSE, r"Livrable")
OUT_CSV_COHERENCE = os.path.join(OUT_DIR, "whitehouse_coherence_unosat_ems_h3.csv")
OUT_CSV_SEUILS = os.path.join(OUT_DIR, "whitehouse_seuils_tstat_unosat_ems.csv")

SEP = "=" * 70

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


def _ensure_ccw(latlng_ring):
    area = 0.0
    n = len(latlng_ring)
    for i in range(n):
        lat1, lng1 = latlng_ring[i]
        lat2, lng2 = latlng_ring[(i + 1) % n]
        area += (lng1 * lat2 - lng2 * lat1)
    return list(reversed(latlng_ring)) if area < 0 else latlng_ring


def ring_from_ogr_geom(geom):
    gt = geom.GetGeometryType()
    if gt in (ogr.wkbMultiPolygon, ogr.wkbMultiPolygon25D):
        best, best_area = None, -1
        for i in range(geom.GetGeometryCount()):
            sub = geom.GetGeometryRef(i)
            if sub.GetArea() > best_area:
                best_area = sub.GetArea(); best = sub
        geom = best
    ring = geom.GetGeometryRef(0)
    return [(ring.GetY(i), ring.GetX(i)) for i in range(ring.GetPointCount())]


def build_h3_grid(intersect_geom, res):
    latlng_ring = _ensure_ccw(ring_from_ogr_geom(intersect_geom))
    if _H3_V4:
        cells = list(h3.polygon_to_cells(h3.LatLngPoly(latlng_ring), res))
    else:
        cells = list(h3.polyfill({'type': 'Polygon', 'coordinates': [
            [[lng, lat] for lat, lng in latlng_ring]]}, res, geo_json_conformant=True))
    return cells


def latlng_to_cell(lat, lng, res):
    return h3.latlng_to_cell(lat, lng, res) if _H3_V4 else h3.geo_to_h3(lat, lng, res)


def classify_points_to_h3(points, valid_cells, res):
    cell_severity = {}
    for lat, lon, sev in points:
        cid = latlng_to_cell(lat, lon, res)
        if cid not in valid_cells:
            continue
        if cell_severity.get(cid, -1) < sev:
            cell_severity[cid] = sev
    return cell_severity


def run_partie_a():
    print(f"{SEP}\n  PARTIE A — Coherence UNOSAT vs EMS sur grille H3\n{SEP}")
    if h3 is None:
        print("  h3-py non installe — partie A ignoree (pip install h3 --break-system-packages)")
        return

    unosat_extent = load_single_geom_wgs84(UNOSAT_ANALYSIS_EXTENT)
    ems_extent = load_single_geom_wgs84(EMS_AOI)
    if unosat_extent is None or ems_extent is None:
        print("  Emprise(s) manquante(s) — partie A ignoree")
        return

    intersect = unosat_extent.Intersection(ems_extent)
    if intersect is None or intersect.IsEmpty():
        print("  ATTENTION — les emprises UNOSAT et EMS ne se recouvrent pas — verifier les fichiers/projections")
        return
    print(f"  Intersection des emprises calculee (aire ~{intersect.GetArea():.6f} deg2)")

    bounds = get_bounds(intersect)
    valid_cells = set(build_h3_grid(intersect, H3_RESOLUTION))
    print(f"  {len(valid_cells):,} cellule(s) H3 (resolution {H3_RESOLUTION}) sur l'intersection")

    unosat_pts = load_points_classified(UNOSAT_POINTS, UNOSAT_FIELD, UNOSAT_RULES, bounds)
    ems_pts = load_points_classified(EMS_POINTS, EMS_FIELD, EMS_RULES, bounds)
    print(f"  UNOSAT : {len(unosat_pts):,} signalement(s) exploitable(s)")
    print(f"  EMS    : {len(ems_pts):,} signalement(s) exploitable(s)")

    unosat_h3 = classify_points_to_h3(unosat_pts, valid_cells, H3_RESOLUTION)
    ems_h3 = classify_points_to_h3(ems_pts, valid_cells, H3_RESOLUTION)

    common_cells = set(unosat_h3.keys()) & set(ems_h3.keys())
    print(f"  {len(common_cells):,} cellule(s) couvertes par LES DEUX sources")

    if not common_cells:
        print("  Aucune cellule commune — pas de tableau croise possible")
        return

    cross = {}
    rows = []
    for cid in common_cells:
        su, se = unosat_h3[cid], ems_h3[cid]
        rows.append({'h3': cid, 'unosat_severite': su, 'ems_severite': se,
                      'unosat_bin': 1 if su > 0 else 0, 'ems_bin': 1 if se > 0 else 0,
                      'accord_bin': (su > 0) == (se > 0)})
        key = (su, se)
        cross[key] = cross.get(key, 0) + 1

    n_agree_bin = sum(1 for r in rows if r['accord_bin'])
    print(f"\n  Accord binaire (endommage vs non) : {n_agree_bin}/{len(rows)} "
          f"({100*n_agree_bin/len(rows):.1f}%)")
    print(f"\n  Tableau croise (0=non endommage, 1=damaged, 2=destroyed) :")
    print(f"  {'UNOSAT \\ EMS':15s} {'0':>6s} {'1':>6s} {'2':>6s}")
    for su in (0, 1, 2):
        line = f"  {su:15d} "
        for se in (0, 1, 2):
            line += f"{cross.get((su, se), 0):>6d} "
        print(line)

    with open(OUT_CSV_COHERENCE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['h3', 'unosat_severite', 'ems_severite', 'unosat_bin', 'ems_bin', 'accord_bin'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\n  Ecrit : {OUT_CSV_COHERENCE}")


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
        mean_v = max_v = None
        if px0 <= px1 and py0 <= py1:
            sub = band.ReadAsArray(px0, py0, px1 - px0 + 1, py1 - py0 + 1)
            if sub is not None:
                sub = sub.astype(np.float64)
                if nd is not None:
                    sub[np.isclose(sub, nd)] = np.nan
                valid = sub[np.isfinite(sub)]
                if len(valid) > 0:
                    mean_v = float(np.mean(valid))
                    max_v = float(np.max(valid))
        out[bid] = {'mean': mean_v, 'max': max_v}
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
    pos = vals[y_true == 1]
    neg = vals[y_true == 0]
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


def run_partie_b():
    print(f"\n{SEP}\n  PARTIE B — Seuils T-test optimaux (Open Buildings / OSM x UNOSAT / EMS)\n{SEP}")
    if not os.path.exists(T_STAT_RASTER_PATH):
        print(f"  ATTENTION — raster T-stat introuvable : {T_STAT_RASTER_PATH}")
        print(f"  Completer T_STAT_RASTER_PATH en tete de script puis relancer. Partie B ignoree.")
        return

    zone1_geom = load_single_geom_wgs84(AOI_ZONE1_TEST)
    unosat_extent = load_single_geom_wgs84(UNOSAT_ANALYSIS_EXTENT)
    ems_extent = load_single_geom_wgs84(EMS_AOI)

    rows = []
    for bsrc_name, bsrc_path in BUILDING_SOURCES.items():
        print(f"\n{SEP}\n  Source de batiments : {bsrc_name}\n{SEP}")

        for gt_name, gt_extent, gt_points_path, gt_field, gt_rules in [
            ('UNOSAT', unosat_extent, UNOSAT_POINTS, UNOSAT_FIELD, UNOSAT_RULES),
            ('EMS', ems_extent, EMS_POINTS, EMS_FIELD, EMS_RULES),
        ]:
            if zone1_geom is not None and gt_extent is not None:
                scope_geom = zone1_geom.Intersection(gt_extent)
            else:
                scope_geom = gt_extent or zone1_geom
            if scope_geom is None or scope_geom.IsEmpty():
                print(f"  [{gt_name}] emprise vide (pas d'intersection Zone1/GT) — ignore")
                continue
            bounds = get_bounds(scope_geom)

            buildings = load_buildings_wgs84(bsrc_path, bounds)
            if not buildings:
                print(f"  [{gt_name}] aucun batiment charge — ignore")
                continue
            gt_points = load_points_classified(gt_points_path, gt_field, gt_rules, bounds)
            y_true_dict = snap_points_to_buildings(gt_points, buildings, SNAP_DISTANCE_M)

            stats = compute_stats_per_building(T_STAT_RASTER_PATH, buildings)

            common_ids = list(buildings.keys())
            y_true = np.array([y_true_dict.get(bid, 0) for bid in common_ids])

            print(f"\n  [{gt_name}] {bsrc_name} : {len(common_ids):,} batiment(s), "
                  f"{int(y_true.sum()):,} endommage(s) (accroches a {SNAP_DISTANCE_M:.0f}m)")

            for agg in ('mean', 'max'):
                vals = np.array([stats[bid][agg] if stats[bid][agg] is not None else np.nan for bid in common_ids])
                v = np.isfinite(vals)
                if v.sum() < 10 or y_true[v].sum() == 0:
                    print(f"    {agg:5s} : pas assez de donnees")
                    continue
                auc = compute_auc(y_true[v], vals[v])
                best = find_best_threshold(y_true[v].astype(int), vals[v], T_THRESHOLDS)
                print(f"    {agg:5s} : AUC={auc:.4f}  seuil_opt={best['seuil']:.2f}  "
                      f"kappa={best['kappa']:.4f}  tp={best['tp']}  fp={best['fp']}  n={best['n']}")
                rows.append({'source_batiments': bsrc_name, 'verite_terrain': gt_name,
                              'agregation': agg, 'auc': round(auc, 4), **best})

    fieldnames = ['source_batiments', 'verite_terrain', 'agregation', 'auc', 'seuil',
                  'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa']
    with open(OUT_CSV_SEUILS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV_SEUILS}\n{SEP}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    run_partie_a()
    run_partie_b()


if __name__ == '__main__':
    main()
