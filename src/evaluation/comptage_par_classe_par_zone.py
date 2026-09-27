# -*- coding: utf-8 -*-
"""Comptage par classe de dommage dans le vocabulaire natif de chaque produit, sur ses géométries d'origine et non reprojetées, réparti par zone d'analyse.

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
    sys.exit("osgeo (ogr/gdal) et numpy requis.")

ogr.UseExceptions()
gdal.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\HOTOSM\hdx\aoi.geojson")
AOI_NAME_FIELD = "area"

# (chemin, champ_classe_ou_None) — champ_classe=None pour les sources qui
# ne listent que des batiments deja "endommages" sans distinction de
# gravite (le compte de lignes = le compte d'endommages, tel quel).
SOURCES = {
    'microsoft': (os.path.join(DONNEES, r"VENEZUELA\Microsoft AI for Good Lab\from_huggingFace\venezuela_microsoft_damage_points.geojson"), 'severity'),
    'impact':    (os.path.join(DONNEES, r"VENEZUELA\IMPACT Initiatives S1 DPM\impact_ven_earthquake_sentinel1_damaged_20260625_v3.geojson"), None),
    'osu':       (os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"), 'label'),
    'uhsail':    (os.path.join(DONNEES, r"VENEZUELA\UH SAIL\Building damaged.gpkg"), 'grade'),
    'unep':      (os.path.join(DONNEES, r"VENEZUELA\UNEP\debris_buildings.gpkg"), None),
    'fair':      (os.path.join(DONNEES, r"VENEZUELA\Fair\venezuela_fair_damage_points.geojson"), 'severity'),
    'ems':       (os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP.gpkg"), 'damage_gra'),
    'disha':     (os.path.join(DONNEES, r"VENEZUELA\DISHA\Caracas\nwcaracas_final_inference_result.csv"), 'damaged'),
    'Chatmap':     (os.path.join(DONNEES, r"VENEZUELA\HOTOSM\chatmap\damage_validation_buildings_venezuela_points.geojson"), 'damaged'),
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\comptage_par_classe_par_zone.csv")

# Couche de batiments Overture COMPLETE (toutes zones) — reutilisee pour
# les 3 sources raster ci-dessous (EOS, NASA S1, NASA S2), qui n'ont pas
# leur propre fichier de batiments (juste un raster de score/couleur a
# agreger). On reutilise le fichier ChatMap-sur-Overture deja construit —
# ses champs cm_* sont simplement ignores ici, seule sa geometrie sert.
BUILDINGS_FOR_RASTERS_PATH = os.path.join(DONNEES, r"VENEZUELA\Building\hot_eq_overture_ven_buildings_overture_gpkg\buildings.gpkg")

RASTER_SOURCES = {
    'nasa_s1': os.path.join(DONNEES, r"VENEZUELA\NASA DRCSAmes S1 Urban Backscatter Change Detection\NASA S1 backscatterChangeDetection.tif"),
    'nasa_s2': os.path.join(DONNEES, r"VENEZUELA\NASA DRCSAmes S2 Urban Change Analysis\NASA S2 Urban Change Anal.tif"),
    'eos':     os.path.join(DONNEES, r"VENEZUELA\EOS S1 DPM\EOSRS_2026_005_VEN_EQ_20260625_DPM_S1_Caracas_v0.8.tif"),
}

EOS_COLOR_REFS = {
    'yellow':   (255, 255, 0),
    'orange':   (255, 120, 0),
    'dark_red': (124, 0, 0),
}

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


def load_source(path, class_field, aoi_zones):
    """Charge une source (points ou polygones), attribue sa zone par
    jointure spatiale, retourne un Counter[(zone, classe_brute)].
    Cas special : un .csv brut avec colonnes longitude/latitude (comme
    DISHA) — ogr.Open() ne detecte pas automatiquement la geometrie dans
    ce cas, donc on le lit directement avec le module csv standard."""
    if path.lower().endswith('.csv'):
        return load_source_csv_lonlat(path, class_field, aoi_zones)

    ds = ogr.Open(path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir {path}")
        return Counter()
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    field_names = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                   for i in range(lyr.GetLayerDefn().GetFieldCount())]
    if class_field is not None and class_field not in field_names:
        print(f"  Attention: champ '{class_field}' introuvable. Champs: {field_names}")
        class_field = None

    counts = Counter()
    n_total = 0
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        geom = geom.Clone()
        if tr is not None:
            geom.Transform(tr)
        gt = geom.GetGeometryType()
        pt = geom if gt in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid()
        zone = find_zone(pt, aoi_zones)
        raw_class = str(feat.GetField(class_field)) if class_field else 'damaged (liste = deja endommage)'
        counts[(zone, raw_class)] += 1
        n_total += 1
    ds = None
    print(f"  {n_total} entite(s) chargee(s)")
    return counts


def load_source_csv_lonlat(path, class_field, aoi_zones, lon_field='longitude', lat_field='latitude'):
    """Lit un CSV brut avec colonnes longitude/latitude (DISHA), construit
    les points a la main (pas de detection automatique OGR pour ce cas)."""
    import csv as csv_module
    counts = Counter()
    n_total = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv_module.DictReader(f)
        for row in reader:
            try:
                lon = float(row[lon_field])
                lat = float(row[lat_field])
            except (KeyError, ValueError, TypeError):
                continue
            pt = ogr.CreateGeometryFromWkt(f"POINT ({lon} {lat})")
            zone = find_zone(pt, aoi_zones)
            raw_class = str(row.get(class_field)) if class_field else 'damaged (liste = deja endommage)'
            counts[(zone, raw_class)] += 1
            n_total += 1
    print(f"  {n_total} entite(s) chargee(s) (CSV lon/lat)")
    return counts


def label_s1(val):
    """Etiquette 'Recommended Label' documentee par NASA pour le produit
    S1 — a but esthetique/lecture rapide, pas une regle validee."""
    if val is None:
        return None
    if val <= -8:
        return 'Very strong backscatter decrease (priority investigation)'
    if val <= -6:
        return 'Strong backscatter decrease (potential major structural change)'
    if val <= -4:
        return 'Moderate backscatter decrease (requires validation)'
    return 'Minor or no significant change'


def label_s2(val):
    """Etiquette 'Recommended Label' documentee par NASA pour le produit
    S2 — memes reserves que label_s1."""
    if val is None:
        return None
    if val < 0.05:
        return 'Low Probability'
    if val < 0.15:
        return 'Moderate Probability'
    return 'High Probability'


def raster_mean_per_building(raster_path, buildings_with_geom):
    """Moyenne des pixels valides sous chaque batiment. buildings_with_geom
    = liste de (geom, zone). Retourne liste parallele de valeurs (ou None)."""
    ds = gdal.Open(raster_path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir {raster_path}")
        return [None] * len(buildings_with_geom)
    gt = ds.GetGeoTransform()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray().astype(np.float32)
    nd = band.GetNoDataValue()
    ds = None
    if nd is not None:
        arr[arr == nd] = np.nan

    out = []
    for geom, zone in buildings_with_geom:
        env = geom.GetEnvelope()
        px0 = max(0, int((env[0] - gt[0]) / gt[1]))
        px1 = min(nx - 1, int((env[1] - gt[0]) / gt[1]))
        py0 = max(0, int((env[3] - gt[3]) / gt[5]))
        py1 = min(ny - 1, int((env[2] - gt[3]) / gt[5]))
        val = None
        if px0 <= px1 and py0 <= py1:
            sub = arr[py0:py1 + 1, px0:px1 + 1]
            valid = sub[np.isfinite(sub)]
            if len(valid) > 0:
                val = float(np.mean(valid))
        out.append(val)
    return out


def eos_dominant_per_building(raster_path, buildings_with_geom):
    """Categorie de couleur dominante (yellow/orange/dark_red) sous chaque
    batiment — l'image EOS est RVBA deja coloree, pas un score continu."""
    ds = gdal.Open(raster_path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir {raster_path}")
        return [None] * len(buildings_with_geom)
    gt = ds.GetGeoTransform()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    n_bands = ds.RasterCount
    if n_bands < 3:
        print(f"  Attention: EOS attendu en RVB(A), trouve {n_bands} bande(s)")
        return [None] * len(buildings_with_geom)
    r = ds.GetRasterBand(1).ReadAsArray().astype(np.int16)
    g = ds.GetRasterBand(2).ReadAsArray().astype(np.int16)
    b = ds.GetRasterBand(3).ReadAsArray().astype(np.int16)
    alpha = ds.GetRasterBand(4).ReadAsArray().astype(np.int16) if n_bands >= 4 else None
    ds = None

    cat_names = list(EOS_COLOR_REFS.keys())
    dists = {name: (r - rr) ** 2 + (g - gg) ** 2 + (b - bb) ** 2
             for name, (rr, gg, bb) in EOS_COLOR_REFS.items()}
    dist_stack = np.stack([dists[n] for n in cat_names], axis=0)
    nearest_idx = np.argmin(dist_stack, axis=0)
    valid_mask = (alpha > 10) if alpha is not None else np.ones((ny, nx), dtype=bool)

    out = []
    for geom, zone in buildings_with_geom:
        env = geom.GetEnvelope()
        px0 = max(0, int((env[0] - gt[0]) / gt[1]))
        px1 = min(nx - 1, int((env[1] - gt[0]) / gt[1]))
        py0 = max(0, int((env[3] - gt[3]) / gt[5]))
        py1 = min(ny - 1, int((env[2] - gt[3]) / gt[5]))
        dominant = None
        if px0 <= px1 and py0 <= py1:
            sub_idx = nearest_idx[py0:py1 + 1, px0:px1 + 1]
            sub_valid = valid_mask[py0:py1 + 1, px0:px1 + 1]
            if sub_valid.sum() > 0:
                counts = [((sub_idx == ci) & sub_valid).sum() for ci in range(len(cat_names))]
                dominant = cat_names[int(np.argmax(counts))]
        out.append(dominant)
    return out


def load_buildings_for_raster(path, raster_path, aoi_zones):
    """Charge les batiments Overture, filtres par l'emprise du raster
    (bbox — evite de charger des millions de batiments hors zone), avec
    leur zone AOI deja assignee. Retourne liste de (geom, zone)."""
    ds_r = gdal.Open(raster_path)
    if ds_r is None:
        return []
    gt = ds_r.GetGeoTransform()
    nx, ny = ds_r.RasterXSize, ds_r.RasterYSize
    ds_r = None
    xmin, xmax = gt[0], gt[0] + nx * gt[1]
    ymax, ymin = gt[3], gt[3] + ny * gt[5]

    ds_b = ogr.Open(path)
    if ds_b is None:
        print(f"  Attention: impossible d'ouvrir {path}")
        return []
    lyr_b = ds_b.GetLayer()
    tr = get_transform_to_wgs84(lyr_b)
    lyr_b.SetSpatialFilterRect(xmin, ymin, xmax, ymax)

    out = []
    for feat in lyr_b:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        geom = geom.Clone()
        if tr is not None:
            geom.Transform(tr)
        zone = find_zone(geom.Centroid(), aoi_zones)
        out.append((geom, zone))
    ds_b = None
    print(f"  {len(out)} batiment(s) Overture dans l'emprise du raster")
    return out


# =============================================================================
# MAIN
# =============================================================================

def main():
    aoi_zones = load_aoi_zones(AOI_PATH, AOI_NAME_FIELD)

    results = []
    for source_key, (path, class_field) in SOURCES.items():
        print(f"\n{SEP}")
        print(f"  Source : {source_key}")
        print(SEP)
        if not os.path.exists(path):
            print(f"  Attention: fichier introuvable — {path}")
            continue
        counts = load_source(path, class_field, aoi_zones)
        for (zone, raw_class), n in sorted(counts.items()):
            results.append({'source': source_key, 'zone': zone, 'classe_brute': raw_class, 'n': n})
            print(f"    {zone:15s} | {raw_class:30s} : {n}")

    # --- Sources raster (EOS, NASA S1, NASA S2) — sur toute leur emprise,
    # pas seulement Caraballeda comme avant ---
    for source_key, raster_path in RASTER_SOURCES.items():
        print(f"\n{SEP}")
        print(f"  Source (raster) : {source_key}")
        print(SEP)
        if not os.path.exists(raster_path):
            print(f"  Attention: raster introuvable — {raster_path}")
            continue
        buildings_geom = load_buildings_for_raster(BUILDINGS_FOR_RASTERS_PATH, raster_path, aoi_zones)
        if not buildings_geom:
            continue

        if source_key == 'eos':
            labels = eos_dominant_per_building(raster_path, buildings_geom)
        else:
            values = raster_mean_per_building(raster_path, buildings_geom)
            label_fn = label_s1 if source_key == 'nasa_s1' else label_s2
            labels = [label_fn(v) for v in values]

        counts = Counter()
        for (geom, zone), lab in zip(buildings_geom, labels):
            if lab is None:
                continue
            counts[(zone, lab)] += 1
        for (zone, raw_class), n in sorted(counts.items()):
            results.append({'source': source_key, 'zone': zone, 'classe_brute': raw_class, 'n': n})
            print(f"    {zone:15s} | {raw_class:55s} : {n}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'zone', 'classe_brute', 'n'])
        w.writeheader()
        w.writerows(results)
    print(f"\n{SEP}")
    print(f"  Ecrit : {OUT_CSV}  ({len(results)} ligne(s))")
    print(SEP)


if __name__ == '__main__':
    main()
