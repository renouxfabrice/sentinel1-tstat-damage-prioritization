# -*- coding: utf-8 -*-
"""Recouvrement réel de chaque zone de référence par l'emprise d'analyse de chaque produit, puis construction des emprises communes par inclusion progressive des produits, du mieux couvrant au moins couvrant.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import numpy as np
from config import DONNEES

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
ZONES_A_ETUDIER = ['caraballeda', 'catia_la_mar', 'la_guaira', 'Caracas', 'Moron', 'San Felipe' ]

OVERTURE_BUILDINGS_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_Building_Overture.gpkg")
OVERTURE_ID_FIELD = "id"

EMS_GT_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture_v3_AOI.gpkg")
EMS_ID_FIELD = "id"
EMS_CLASS_FIELD = "cm_damage_gra"

T_TEST_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif")
BDPM_RASTER = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\BDPM.tif")
BURST_MOSAIC_PATH_ASC = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst\mosaic_asc.tif")
BURST_MOSAIC_PATH_DESC = os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\mosaiques_burst\mosaic_desc.tif")
EOS_ON_OVERTURE_PATH = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg")
EOS_ID_FIELD = "overture_id"
EOS_VALUE_FIELD = "raster_max"

# AOI vecteur de chaque source — chemins VERIFIES au fil de ce projet.
# 'mapswipe' et 'ungsc' n'ont jamais eu de chemin AOI confirme dans ce
# projet — laisses a None (ignores, pas devines).
SOURCE_AOI_VECTOR_PATHS = {
    'chatmap':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\chatmap_aoi.gpkg"),
    'disha':     os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\disha_aoi.gpkg"),
    'ems':       os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\ems_aoi.gpkg"),
    'fair':      os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\fair_aoi.gpkg"),
    'impact':    os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\impact_aoi.gpkg"),
    'microsoft': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\microsoft_aoi.gpkg"),
    'osu':       os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\osu_aoi.gpkg"),
    'uhsail':    os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\uhsail_aoi.gpkg"),
    'unep':      os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\unep_aoi.gpkg"),
    'eos':       os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\eos_aoi.gpkg"),
    'nasa_s1':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\nasa_s1_aoi.gpkg"),
    'nasa_s2':   os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\nasa_s2_aoi.gpkg"),
    'ungsc':     os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\original\ungsc_aoi.gpkg"),
}
SOURCE_AOI_RASTER_PATHS = {
    't_test': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\T_Test.tif"),
    'bdpm': os.path.join(DONNEES, r"VENEZUELA\MOI\T_test\AOI_CEMS\BDPM.tif"),
}

T_TEST_THRESHOLDS = [round(x, 2) for x in np.arange(-1.0, 6.01, 0.15)]
BDPM_THRESHOLDS = [round(x, 3) for x in np.arange(-0.10, 0.91, 0.02)]
BURST_THRESHOLDS = [round(x, 3) for x in np.arange(0.0, 1.01, 0.03)]

OUT_CSV_COUVERTURE = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\aoi_couverture_reelle.csv")
OUT_CSV_ETAPES = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\aoi_communes_etapes.csv")

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


def load_zones(path, zone_field, keep_names):
    ds = ogr.Open(path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    out = {}
    for feat in lyr:
        name = feat.GetField(zone_field)
        if name not in keep_names:
            continue
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        if not g2.IsValid():
            g2 = g2.MakeValid()
        out[name] = g2
    ds = None
    return out


def load_union_geom(path):
    if path is None or not os.path.exists(path):
        return None
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


def raster_bbox_polygon(path):
    if path is None or not os.path.exists(path):
        return None
    ds = gdal.Open(path)
    if ds is None:
        return None
    gt = ds.GetGeoTransform()
    prj = ds.GetProjection()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    ds = None
    corners = [(gt[0], gt[3]), (gt[0] + nx * gt[1], gt[3]),
               (gt[0] + nx * gt[1], gt[3] + ny * gt[5]), (gt[0], gt[3] + ny * gt[5])]
    srs = osr.SpatialReference(); srs.ImportFromWkt(prj)
    tr = None
    if not srs.IsSame(WGS84):
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        tr = osr.CoordinateTransformation(srs, WGS84)
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in corners:
        if tr is not None:
            x, y, _ = tr.TransformPoint(x, y)
        ring.AddPoint(x, y)
    ring.CloseRings()
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def area_km2(geom):
    env = geom.GetEnvelope()
    lat_mid = (env[2] + env[3]) / 2
    deg_to_km_lon = 111.320 * np.cos(np.radians(lat_mid))
    deg_to_km_lat = 111.320
    return geom.GetArea() * deg_to_km_lon * deg_to_km_lat


def get_aoi_bounds(geom):
    env = geom.GetEnvelope()
    return env[0], env[2], env[1], env[3]


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
        out[feat.GetField(id_field)] = g2
    ds = None
    return out


def load_field_by_id(path, id_field, value_field, aoi_bounds):
    if not os.path.exists(path):
        return {}
    ds = ogr.Open(path)
    if ds is None:
        return {}
    lyr = ds.GetLayer()
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName() for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if id_field not in field_names or value_field not in field_names:
        print(f"    ERREUR champ manquant dans {path} — champs: {field_names}")
        ds = None
        return {}
    tr = get_transform_to_wgs84(lyr)
    lyr.SetSpatialFilterRect(*aoi_bounds)
    out = {}
    for feat in lyr:
        out[feat.GetField(id_field)] = feat.GetField(value_field)
    ds = None
    return out


def compute_max_per_building(raster_path, geoms):
    if raster_path is None or not os.path.exists(raster_path):
        return [None] * len(geoms)
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
    out = []
    for geom in geoms:
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
        out.append(val)
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


# =============================================================================
# VOLET A — Couverture reelle
# =============================================================================

def volet_a_couverture():
    print(f"{SEP}\n  VOLET A — Verification de la couverture reelle\n{SEP}")
    zones = load_zones(AOI_PATH, AOI_ZONE_FIELD, ZONES_A_ETUDIER)
    print(f"  Zones chargees : {list(zones.keys())}")

    all_source_names = list(SOURCE_AOI_VECTOR_PATHS.keys()) + list(SOURCE_AOI_RASTER_PATHS.keys())
    source_geoms = {}
    for name, path in SOURCE_AOI_VECTOR_PATHS.items():
        source_geoms[name] = load_union_geom(path) if path else None
    for name, path in SOURCE_AOI_RASTER_PATHS.items():
        source_geoms[name] = raster_bbox_polygon(path)

    rows = []
    for zone_name, zone_geom in zones.items():
        zone_area = area_km2(zone_geom)
        row = {'zone': zone_name, 'zone_area_km2': round(zone_area, 3)}
        print(f"\n  -- {zone_name} (aire={zone_area:.2f} km2) --")
        for src_name in all_source_names:
            g = source_geoms.get(src_name)
            if g is None:
                row[src_name] = None
                print(f"    {src_name:12s} : chemin indisponible")
                continue
            inter = g.Intersection(zone_geom) if g.Intersects(zone_geom) else None
            pct = 100 * area_km2(inter) / zone_area if inter is not None and not inter.IsEmpty() else 0.0
            row[src_name] = round(pct, 1)
            print(f"    {src_name:12s} : {pct:.1f}%")
        rows.append(row)

    os.makedirs(os.path.dirname(OUT_CSV_COUVERTURE), exist_ok=True)
    fieldnames = ['zone', 'zone_area_km2'] + all_source_names
    with open(OUT_CSV_COUVERTURE, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nEcrit : {OUT_CSV_COUVERTURE}")
    return rows, zones, source_geoms, all_source_names


# =============================================================================
# VOLET B — AOI communes par etape
# =============================================================================

def find_best_solo(y_true, vals, thresholds, direction):
    best = None
    for thr in thresholds:
        pred = ((vals >= thr) if direction == 'ge' else (vals <= thr)).astype(int)
        m = compute_metrics_np(y_true, pred)
        if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
            best = {'seuil_a': thr, 'seuil_b': None, **m}
    return best


def find_best_fusion(y_true, vals_a, thr_a, vals_b, thr_b, dir_b):
    best = None
    for ta in thr_a:
        for tb in thr_b:
            cond_b = (vals_b >= tb) if dir_b == 'ge' else (vals_b <= tb)
            pred = ((vals_a >= ta) & cond_b).astype(int)
            m = compute_metrics_np(y_true, pred)
            if m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
                best = {'seuil_a': ta, 'seuil_b': tb, **m}
    return best


def volet_b_etapes(couverture_rows, zones, source_geoms, all_source_names):
    print(f"\n{SEP}\n  VOLET B — AOI communes par etape progressive\n{SEP}")

    print("  Chargement Overture / EMS / T-stat / BDPM / burst / EOS (une fois, sur l'union des 3 zones)...")
    union_zones = None
    for z in zones.values():
        union_zones = z if union_zones is None else union_zones.Union(z)
    aoi_bounds = get_aoi_bounds(union_zones)

    overture = load_overture_buildings(OVERTURE_BUILDINGS_PATH, OVERTURE_ID_FIELD, aoi_bounds)
    ems_gt = load_field_by_id(EMS_GT_PATH, EMS_ID_FIELD, EMS_CLASS_FIELD, aoi_bounds)
    eos_raw = load_field_by_id(EOS_ON_OVERTURE_PATH, EOS_ID_FIELD, EOS_VALUE_FIELD, aoi_bounds)

    common_ids = list(set(overture.keys()) & set(ems_gt.keys()))
    geoms_all = [overture[oid] for oid in common_ids]
    raw_classes_all = {oid: ems_gt[oid] for oid in common_ids}
    y_true_full = {oid: (1 if ems_gt[oid] in ('Possibly damaged', 'Damaged', 'Destroyed')
                         else (0 if ems_gt[oid] == 'not_reported' else None)) for oid in common_ids}

    t_vals_all = dict(zip(common_ids, compute_max_per_building(T_TEST_RASTER, geoms_all)))
    bdpm_vals_all = dict(zip(common_ids, compute_max_per_building(BDPM_RASTER, geoms_all)))
    asc_vals_all = dict(zip(common_ids, compute_max_per_building(BURST_MOSAIC_PATH_ASC, geoms_all)))
    desc_vals_all = dict(zip(common_ids, compute_max_per_building(BURST_MOSAIC_PATH_DESC, geoms_all)))
    burst_vals_all = {oid: (np.nanmean([asc_vals_all[oid], desc_vals_all[oid]])
                             if (asc_vals_all[oid] is not None or desc_vals_all[oid] is not None) else None)
                       for oid in common_ids}
    eos_vals_all = {oid: eos_raw.get(oid) for oid in common_ids}
    oid_to_geom = dict(zip(common_ids, geoms_all))

    rows = []

    for row in couverture_rows:
        zone_name = row['zone']
        zone_geom = zones[zone_name]
        print(f"\n{SEP}\n  Zone : {zone_name}\n{SEP}")

        pcts = {s: row.get(s) for s in all_source_names if row.get(s) is not None}
        ordered_sources = sorted(pcts.keys(), key=lambda s: -pcts[s])
        print(f"  Ordre de couverture decroissante : {[(s, pcts[s]) for s in ordered_sources]}")

        included = []
        for step_i, src in enumerate(ordered_sources, start=1):
            included.append(src)
            common_geom = zone_geom
            for s in included:
                g = source_geoms.get(s)
                if g is None:
                    continue
                common_geom = common_geom.Intersection(g) if common_geom.Intersects(g) else None
                if common_geom is None or common_geom.IsEmpty():
                    break
            if common_geom is None or common_geom.IsEmpty():
                print(f"  Etape {step_i} ({src}) : intersection VIDE — arret de la progression pour cette zone")
                break

            ref_id = f"{zone_name}_etape{step_i}_+{src}"
            common_area = area_km2(common_geom)
            print(f"\n  -- Etape {step_i} : +{src} (sources incluses: {included}) — aire commune={common_area:.3f} km2 --")

            ids_in_common = [oid for oid, g in oid_to_geom.items() if common_geom.Contains(g.Centroid())]
            y_true = np.array([y_true_full[oid] for oid in ids_in_common if y_true_full[oid] is not None])
            valid_ids = [oid for oid in ids_in_common if y_true_full[oid] is not None]
            n_batiments = len(valid_ids)
            n_pos = int(y_true.sum()) if len(y_true) else 0
            taux_dommage = n_pos / n_batiments if n_batiments > 0 else None
            print(f"     {n_batiments} batiment(s) evalues, {n_pos} positif(s) EMS (taux={taux_dommage})")

            base_row = {'reference_etape': ref_id, 'zone': zone_name, 'etape': step_i,
                        'source_ajoutee': src, 'aire_commune_km2': round(common_area, 3),
                        'n_batiments_evalues': n_batiments, 'n_positifs_ems': n_pos,
                        'taux_dommage': round(taux_dommage, 4) if taux_dommage is not None else None}
            for s in all_source_names:
                base_row[f'inclus_{s}'] = (s in included)

            if n_batiments < 20 or n_pos == 0:
                print("     Trop peu de donnees — methodes ignorees pour cette etape")
                rows.append({**base_row, 'methode': None, 'seuil_a': None, 'seuil_b': None,
                             'tp': None, 'fp': None, 'kappa': None, 'recall': None})
                continue

            tv = np.array([t_vals_all[oid] if t_vals_all[oid] is not None else np.nan for oid in valid_ids])
            bv = np.array([bdpm_vals_all[oid] if bdpm_vals_all[oid] is not None else np.nan for oid in valid_ids])
            bu = np.array([burst_vals_all[oid] if burst_vals_all[oid] is not None else np.nan for oid in valid_ids])
            ev = np.array([eos_vals_all[oid] if eos_vals_all[oid] is not None else np.nan for oid in valid_ids])

            valid_t = np.isfinite(tv)
            if valid_t.sum() >= 20 and y_true[valid_t].sum() > 0:
                best = find_best_solo(y_true[valid_t], tv[valid_t], T_TEST_THRESHOLDS, 'ge')
                if best:
                    rows.append({**base_row, 'methode': 't_test_seul', **best})
                    print(f"     t_test_seul           : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

            valid_b = np.isfinite(bv)
            if valid_b.sum() >= 20 and y_true[valid_b].sum() > 0:
                best = find_best_solo(y_true[valid_b], bv[valid_b], BDPM_THRESHOLDS, 'ge')
                if best:
                    rows.append({**base_row, 'methode': 'bdpm_seul', **best})
                    print(f"     bdpm_seul              : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

            valid_tb = np.isfinite(tv) & np.isfinite(bu)
            if valid_tb.sum() >= 20 and y_true[valid_tb].sum() > 0:
                best = find_best_fusion(y_true[valid_tb], tv[valid_tb], T_TEST_THRESHOLDS,
                                         bu[valid_tb], BURST_THRESHOLDS, 'le')
                if best:
                    rows.append({**base_row, 'methode': 'fusion_tstat_coevent', **best})
                    print(f"     fusion_tstat_coevent   : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

            valid_te = np.isfinite(tv) & np.isfinite(ev)
            if valid_te.sum() >= 20 and y_true[valid_te].sum() > 0:
                eos_thr = [round(x, 3) for x in np.linspace(np.nanmin(ev[valid_te]), np.nanmax(ev[valid_te]), 30)]
                best = find_best_fusion(y_true[valid_te], tv[valid_te], T_TEST_THRESHOLDS,
                                         ev[valid_te], eos_thr, 'ge')
                if best:
                    rows.append({**base_row, 'methode': 'fusion_tstat_eos', **best})
                    print(f"     fusion_tstat_eos       : kappa={best['kappa']:.3f}  tp={best['tp']}  fp={best['fp']}")

    os.makedirs(os.path.dirname(OUT_CSV_ETAPES), exist_ok=True)
    fieldnames = (['reference_etape', 'zone', 'etape', 'source_ajoutee', 'aire_commune_km2',
                   'n_batiments_evalues', 'n_positifs_ems', 'taux_dommage']
                  + [f'inclus_{s}' for s in all_source_names]
                  + ['methode', 'seuil_a', 'seuil_b', 'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa'])
    with open(OUT_CSV_ETAPES, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"\n{SEP}\nEcrit : {OUT_CSV_ETAPES}\n{SEP}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    couverture_rows, zones, source_geoms, all_source_names = volet_a_couverture()
    volet_b_etapes(couverture_rows, zones, source_geoms, all_source_names)


if __name__ == '__main__':
    main()
