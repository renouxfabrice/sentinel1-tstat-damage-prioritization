# -*- coding: utf-8 -*-
"""Part de chaque zone de référence couverte par l'emprise d'analyse propre à chaque produit, en traitant les quatre formes sous lesquelles cette emprise est publiée.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
import zipfile
import urllib.request
from config import COHERENCE, DONNEES

try:
    from osgeo import ogr, osr, gdal
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()
gdal.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

REF_AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\HOTOSM\hdx\aoi.geojson")
REF_AOI_NAME_FIELD = "area"

# Masque terre (Natural Earth, 10 m) — retire la mer avant le calcul des
# pourcentages de recouvrement. Laisser a None pour que le script telecharge
# le masque au premier lancement et le mette en cache.
LAND_MASK_PATH = os.path.join(COHERENCE, r"VENEZ\SLC_OSU\_ne_10m_land_cache\ne_10m_land.shp")#None
LAND_MASK_CACHE_DIR = os.path.join(COHERENCE, r"VENEZ\SLC_OSU\_ne_10m_land_cache\ne_10m_land.shp")

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\recouvrement_aoi_par_source.csv")

SOURCES_AOI = {
    'mapswipe':  ('vector_aoi', REF_AOI_PATH, None),
    'disha':     ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\DISHA\Caracas\nwcaracas_aoi.geojson"), None),
    'ems':       ('vector_aoi',
                  os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v2.gpkg"),
                  None),
    'eos':       ('raster_extent', os.path.join(DONNEES, r"VENEZUELA\EOS S1 DPM\EOSRS_2026_005_VEN_EQ_20260625_DPM_S1_Caracas_v0.8.tif"), None),
    'fair':      ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\Fair\ALL\AOI_fair.gpkg"), None),
    'impact':    ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\IMPACT Initiatives S1 DPM\impact_ven_earthquake_analyzed_area_20260625_v2.gpkg"), None),
    'microsoft': ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\Microsoft AI for Good Lab\vantor_mask_all.gpkg"), None),
    'nasa_s1':   ('raster_extent', os.path.join(DONNEES, r"VENEZUELA\NASA DRCSAmes S1 Urban Backscatter Change Detection\NASA S1 backscatterChangeDetection.tif"), None),
    'nasa_s2':   ('raster_extent', os.path.join(DONNEES, r"VENEZUELA\NASA DRCSAmes S2 Urban Change Analysis\NASA S2 Urban Change Anal.tif"), None),
    'osu':       ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_analyzed_area_20260701_v1.gpkg"), None),
    'uhsail':    ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\UH SAIL\AOI_UHSAIL.gpkg"), None),
    'unep':      ('vector_aoi', os.path.join(DONNEES, r"VENEZUELA\UNEP\AOI_All.gpkg"), None),
    'ungsc':     ('raster_extent', os.path.join(DONNEES, r"VENEZUELA\UNGSC\UNGSC_Damage_UrbanOnly_Caracas_AOI.tif"), None),
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


def load_ref_zones(path, name_field):
    ds = ogr.Open(path)
    if ds is None:
        sys.exit(f"Impossible d'ouvrir l'AOI de reference : {path}")
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


def load_vector_union(path):
    ds = ogr.Open(path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir {path}")
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


def load_raster_extent_polygon(path):
    ds = gdal.Open(path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir le raster {path}")
        return None
    gt = ds.GetGeoTransform()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    proj = ds.GetProjection()
    ds = None
    xmin = gt[0]; xmax = gt[0] + nx * gt[1]
    ymax = gt[3]; ymin = gt[3] + ny * gt[5]
    ring_wkt = f"{xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}"
    poly = ogr.CreateGeometryFromWkt(f"POLYGON (({ring_wkt}))")
    if proj:
        src_srs = osr.SpatialReference(); src_srs.ImportFromWkt(proj)
        src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not src_srs.IsSame(WGS84):
            tr = osr.CoordinateTransformation(src_srs, WGS84)
            poly.Transform(tr)
    return poly


def load_building_hull(path):
    ds = ogr.Open(path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir {path}")
        return None
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    multi = ogr.Geometry(ogr.wkbGeometryCollection)
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        multi.AddGeometry(g)
    ds = None
    if multi.GetGeometryCount() == 0:
        return None
    return multi.ConvexHull()


def ensure_land_mask(configured_path, cache_dir, ref_bounds):
    """Retourne une geometrie terre (union), restreinte a la zone d'interet
    (ref_bounds = xmin,ymin,xmax,ymax) pour rester rapide. Utilise
    configured_path si fourni, sinon telecharge/mets en cache Natural
    Earth 10m automatiquement."""
    shp_path = configured_path
    if shp_path is None or not os.path.exists(shp_path):
        os.makedirs(cache_dir, exist_ok=True)
        shp_path = os.path.join(cache_dir, 'ne_10m_land.shp')
        if not os.path.exists(shp_path):
            print("  Masque terre non trouve — telechargement de Natural Earth 10m...")
            zip_path = os.path.join(cache_dir, 'ne_10m_land.zip')
            url = 'https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_land.zip'
            try:
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path) as z:
                    z.extractall(cache_dir)
                print(f"  Telecharge et extrait dans {cache_dir}")
            except Exception as e:
                print(f"  Attention: telechargement echoue ({e}) — la mer ne sera PAS retiree, "
                      f"donne LAND_MASK_PATH manuellement si tu as deja ce fichier.")
                return None
    if not os.path.exists(shp_path):
        return None

    ds = ogr.Open(shp_path)
    if ds is None:
        print(f"  Attention: impossible d'ouvrir le masque terre {shp_path}")
        return None
    lyr = ds.GetLayer()
    xmin, ymin, xmax, ymax = ref_bounds
    lyr.SetSpatialFilterRect(xmin, ymin, xmax, ymax)
    geoms = []
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if not g.IsValid():
            g = g.MakeValid()
        geoms.append(g)
    ds = None
    if not geoms:
        print("  Attention: aucun polygone terre trouve pres de la zone — la mer ne sera pas retiree.")
        return None
    union = geoms[0]
    for g in geoms[1:]:
        union = union.Union(g)
    print(f"  Masque terre charge : {len(geoms)} polygone(s) pres de la zone")
    return union


def get_source_geom(kind, path, minus_path):
    if kind == 'vector_aoi':
        return load_vector_union(path)
    if kind == 'vector_aoi_minus':
        g = load_vector_union(path)
        if g is None:
            return None
        m = load_vector_union(minus_path)
        if m is not None:
            g = g.Difference(m)
        return g
    if kind == 'raster_extent':
        return load_raster_extent_polygon(path)
    if kind == 'building_extent_hull':
        return load_building_hull(path)
    raise ValueError(kind)


# =============================================================================
# MAIN
# =============================================================================

def main():
    ref_zones = load_ref_zones(REF_AOI_PATH, REF_AOI_NAME_FIELD)

    # Calculer l'emprise globale de toutes les zones, pour ne charger le
    # masque terre que dans ce secteur (pas le monde entier)
    all_env = [g.GetEnvelope() for _, g in ref_zones]  # xmin,xmax,ymin,ymax
    ref_bounds = (min(e[0] for e in all_env), min(e[2] for e in all_env),
                  max(e[1] for e in all_env), max(e[3] for e in all_env))
    land_mask = ensure_land_mask(LAND_MASK_PATH, LAND_MASK_CACHE_DIR, ref_bounds)

    if land_mask is not None:
        print("\nDecoupage des zones de reference sur le masque terre (retrait de la mer)...")
        new_ref_zones = []
        for name, g in ref_zones:
            land_only = g.Intersection(land_mask) if g.Intersects(land_mask) else g
            new_ref_zones.append((name, land_only if land_only and not land_only.IsEmpty() else g))
        ref_zones = new_ref_zones

    results = []
    for source_key, (kind, path, minus_path) in SOURCES_AOI.items():
        print(f"\n{SEP}")
        print(f"  Source : {source_key}  (type: {kind})")
        print(SEP)
        if not os.path.exists(path):
            print(f"  Attention: fichier introuvable — {path}")
            continue
        src_geom = get_source_geom(kind, path, minus_path)
        if src_geom is None:
            print(f"  Attention: geometrie source vide/invalide — ignoree")
            continue

        for zone_name, zone_geom in ref_zones:
            zone_area = zone_geom.GetArea()
            if zone_area == 0:
                continue
            if src_geom.Intersects(zone_geom):
                inter = src_geom.Intersection(zone_geom)
                inter_area = inter.GetArea() if inter else 0.0
            else:
                inter_area = 0.0
            pct = 100.0 * inter_area / zone_area
            results.append({'source': source_key, 'zone': zone_name,
                             'kind': kind, 'pct_coverage': round(pct, 1)})
            print(f"  {zone_name:15s} : {pct:5.1f}% couvert")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'zone', 'kind', 'pct_coverage'])
        w.writeheader()
        w.writerows(results)
    print(f"\n{SEP}")
    print(f"  Ecrit : {OUT_CSV}  ({len(results)} ligne(s))")
    print(SEP)

    print("\nTableau recapitulatif (% de couverture) :\n")
    zone_names = [n for n, _ in ref_zones]
    header = f"{'Source':12s}" + "".join(f"{z[:10]:>12s}" for z in zone_names)
    print(header)
    for source_key in SOURCES_AOI:
        row_vals = {r['zone']: r['pct_coverage'] for r in results if r['source'] == source_key}
        line = f"{source_key:12s}" + "".join(f"{row_vals.get(z, '-'):>12}" for z in zone_names)
        print(line)


if __name__ == '__main__':
    main()
