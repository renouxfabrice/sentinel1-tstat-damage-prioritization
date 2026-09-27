# -*- coding: utf-8 -*-
"""Accord entre deux vérités de référence sur grille hexagonale, l'univers de référence étant l'ensemble des empreintes de bâtiments et non les seuls points de dommage, ce qui rend possible l'existence de cellules non endommagées.

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
    sys.exit("h3-py manquant. python -m pip install h3 --break-system-packages")

OPEN_BUILDINGS = os.path.join(WHITEHOUSE, r"Source Batis\open_bulding_whitehouse.gpkg")

UNOSAT_ANALYSIS_EXTENT = os.path.join(WHITEHOUSE, r"UNOSAT\_static_unosat_filesystem_4215_TC20251028JAM_SHP\TC20251028JAM_SHP\AP_20251031_AnalysisExtent_WhiteHouse.shp")
UNOSAT_POINTS = os.path.join(WHITEHOUSE, r"UNOSAT\_static_unosat_filesystem_4215_TC20251028JAM_SHP\TC20251028JAM_SHP\AP_20251031_Damagedbuilding_WhiteHouse.shp")
UNOSAT_FIELD = "Main_Damag"
UNOSAT_RULES = {'damaged': [13], 'destroyed': [1]}

EMS_AOI = os.path.join(WHITEHOUSE, r"UNOSAT\EMSR847_AOI39_GRA_PRODUCT_v1\EMSR847_AOI39_GRA_PRODUCT_areaOfInterestA_v1.shp")
EMS_POINTS = os.path.join(WHITEHOUSE, r"UNOSAT\EMSR847_AOI39_GRA_PRODUCT_v1\EMSR847_AOI39_GRA_PRODUCT_builtUpP_v1.shp")
EMS_FIELD = "damage_gra"
EMS_RULES = {'damaged': ['Damaged', 'Possibly damaged'], 'destroyed': ['Destroyed']}

SNAP_DISTANCE_M = 20.0
H3_RESOLUTION = 12

OUT_DIR = os.path.join(WHITEHOUSE, r"Livrable")
OUT_CSV = os.path.join(OUT_DIR, "whitehouse_coherence_unosat_ems_h3_via_batiments.csv")

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
    if raw in (rules.get('destroyed') or []):
        return 2
    if raw in (rules.get('damaged') or []):
        return 1
    return 0


def load_points_classified(path, field, rules, aoi_bounds):
    if not os.path.exists(path):
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


def classify_buildings_by_snap(points, buildings, snap_dist_m):
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
        best_sev, best_dist = 0, snap_dist_m
        for idx in cand:
            plat, plon, sev = points[idx]
            d = haversine_m(clat, clon, plat, plon)
            if d <= best_dist:
                if sev > best_sev or (sev == best_sev and d < best_dist):
                    best_sev = sev
                    best_dist = d
        out[bid] = best_sev
    return out


def buildings_to_h3(building_severity, buildings, res):
    cell_severity = {}
    for bid, sev in building_severity.items():
        geom = buildings.get(bid)
        if geom is None:
            continue
        c = geom.Centroid()
        cid = h3.latlng_to_cell(c.GetY(), c.GetX(), res) if _H3_V4 else h3.geo_to_h3(c.GetY(), c.GetX(), res)
        if cell_severity.get(cid, -1) < sev:
            cell_severity[cid] = sev
    return cell_severity


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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"{SEP}\n  Emprises et intersection UNOSAT / EMS\n{SEP}")
    unosat_extent = load_single_geom_wgs84(UNOSAT_ANALYSIS_EXTENT)
    ems_extent = load_single_geom_wgs84(EMS_AOI)
    if unosat_extent is None or ems_extent is None:
        sys.exit("ERREUR — emprise(s) manquante(s)")
    intersect = unosat_extent.Intersection(ems_extent)
    if intersect is None or intersect.IsEmpty():
        sys.exit("ERREUR — aucune intersection UNOSAT/EMS")
    bounds = get_bounds(intersect)
    print(f"  Intersection calculee, aire ~{intersect.GetArea():.6f} deg2")

    print(f"\n{SEP}\n  Chargement des batiments Open Building (univers de reference)\n{SEP}")
    buildings = load_buildings_wgs84(OPEN_BUILDINGS, bounds)
    print(f"  {len(buildings):,} batiment(s) Open Building dans l'intersection")
    if not buildings:
        sys.exit("ERREUR — aucun batiment charge")

    print(f"\n{SEP}\n  Classification par accrochage (UNOSAT, puis EMS)\n{SEP}")
    unosat_pts = load_points_classified(UNOSAT_POINTS, UNOSAT_FIELD, UNOSAT_RULES, bounds)
    ems_pts = load_points_classified(EMS_POINTS, EMS_FIELD, EMS_RULES, bounds)
    print(f"  UNOSAT : {len(unosat_pts):,} signalement(s)")
    print(f"  EMS    : {len(ems_pts):,} signalement(s)")

    unosat_bldg_sev = classify_buildings_by_snap(unosat_pts, buildings, SNAP_DISTANCE_M)
    ems_bldg_sev = classify_buildings_by_snap(ems_pts, buildings, SNAP_DISTANCE_M)

    n_unosat_dmg = sum(1 for s in unosat_bldg_sev.values() if s > 0)
    n_ems_dmg = sum(1 for s in ems_bldg_sev.values() if s > 0)
    print(f"  UNOSAT : {n_unosat_dmg:,}/{len(buildings):,} batiments endommages")
    print(f"  EMS    : {n_ems_dmg:,}/{len(buildings):,} batiments endommages")

    print(f"\n{SEP}\n  Agregation vers H3 (resolution {H3_RESOLUTION}, max par cellule)\n{SEP}")
    unosat_h3 = buildings_to_h3(unosat_bldg_sev, buildings, H3_RESOLUTION)
    ems_h3 = buildings_to_h3(ems_bldg_sev, buildings, H3_RESOLUTION)
    common_cells = set(unosat_h3.keys()) & set(ems_h3.keys())
    print(f"  {len(unosat_h3):,} cellule(s) H3 (UNOSAT), {len(ems_h3):,} (EMS), "
          f"{len(common_cells):,} en commun")

    rows = []
    cross = {}
    for cid in common_cells:
        su, se = unosat_h3[cid], ems_h3[cid]
        rows.append({'h3': cid, 'unosat_severite': su, 'ems_severite': se})
        cross[(su, se)] = cross.get((su, se), 0) + 1

    print(f"\n  Tableau croise complet (0=non endommage, 1=damaged, 2=destroyed) :")
    print(f"  {'UNOSAT \\ EMS':15s} {'0':>6s} {'1':>6s} {'2':>6s}  {'Total':>7s}")
    for su in (0, 1, 2):
        line = f"  {su:15d} "
        rowtot = 0
        for se in (0, 1, 2):
            v = cross.get((su, se), 0)
            line += f"{v:>6d} "
            rowtot += v
        line += f"  {rowtot:>7d}"
        print(line)

    y_unosat = np.array([1 if unosat_h3[c] > 0 else 0 for c in common_cells])
    y_ems = np.array([1 if ems_h3[c] > 0 else 0 for c in common_cells])
    m = compute_metrics_np(y_unosat, y_ems)
    print(f"\n  Accord binaire reel (endommage vs non, avec vrais negatifs) : "
          f"{m['tp']+m['tn']}/{m['n']} ({100*(m['tp']+m['tn'])/m['n']:.1f}%)")
    print(f"  Kappa (endommage/non, EMS vs UNOSAT) : {m['kappa']:.4f}")
    print(f"    TP={m['tp']}  FP={m['fp']}  FN={m['fn']}  TN={m['tn']}")

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['h3', 'unosat_severite', 'ems_severite'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
