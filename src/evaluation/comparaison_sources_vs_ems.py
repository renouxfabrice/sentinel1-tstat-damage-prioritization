# -*- coding: utf-8 -*-
"""Kappa, précision et rappel de chaque produit contre la vérité Copernicus EMS, bâtiment par bâtiment sur un identifiant d'empreinte partagé, et non par comptage indépendant dans une même zone.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys
import csv
from config import DONNEES

try:
    from osgeo import ogr, osr
except ImportError:
    sys.exit("osgeo (gdal/ogr) requis.")

ogr.UseExceptions()

# =============================================================================
# CONFIGURATION
# =============================================================================

AOI_PATH = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_areOfinterestA_v3.gpkg")

GROUND_TRUTH = {
    'path': os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL\EMSR884_builtUpP_proj_Overture_v3_AOI.gpkg"),
    'id_field': 'id',
    'class_field': 'cm_damage_gra',
    'damaged_values': ['Possibly damaged', 'Damaged'],
    'destroyed_values': ['Destroyed'],
    'excluded_values': [],
}

SOURCES_ON_OVERTURE = {
    # Toutes ces couches vivent dans le meme dossier de sources reprojetees
    # sur les empreintes de reference, avec la meme convention de champs :
    # 'overture_id', 'classe', 'damaged', 'destroyed'.
    'chatmap': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\chatmap_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'],
        'excluded_values': [],
    },
    'disha': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\disha_on_overture.gpkg"),
        'id_field': 'id', 'class_field': 'cm_damaged',
        'damaged_values': ['TRUE', 'True', True], 'destroyed_values': [],
        'excluded_values': [],
    },
    'fair': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\fair_on_overture.gpkg"),
        'id_field': 'id', 'class_field': 'cm_damage',
        'damaged_values': ['minor-damage', 'major-damage'], 'destroyed_values': ['destroyed'],
        'excluded_values': ['no-data (cloud)', 'no-data (no pre)'],
    },
    'impact': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\impact_on_overture.gpkg"),
        'id_field': 'id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'],
        'excluded_values': [],
    },
    'microsoft': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\microsoft_on_overture.gpkg"),
        'id_field': 'id', 'class_field': 'cm_severity',
        'damaged_values': ['damaged'], 'destroyed_values': [],
        'excluded_values': [],
    },
    # osu, unep et uhsail ne sont pas dans le dossier des sources
    # reprojetees : chacun garde son chemin et son schema de champs propres,
    # verifies au lancement par le controle prealable.
    'osu': {
        'path': os.path.join(DONNEES, r"VENEZUELA\OSU S1 InSAR CCD\EMSR884_all_buildings_damage_assessment_20260701_v1.gpkg"),
        'id_field': 'overture_id', 'class_field': 'label',
        'damaged_values': ['likely_damaged'], 'destroyed_values': [],
        'excluded_values': ['not_assessed'],
    },
    'uhsail': {
        'path': os.path.join(DONNEES, r"VENEZUELA\UH SAIL\uhsail_on_overture.gpkg"),
        'id_field': 'id', 'class_field': 'cm_grade',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'],
        'excluded_values': [],
    },
    # 'unep' EXCLUE TEMPORAIREMENT — bug confirme (scan complet des
    # 924668 entites : 0 correspondance partout pour 'cm_matched'), tres
    # probablement le meme genre de probleme de CRS deja rencontre et
    # fichier plutot qu'en WGS84). A investiguer separement dans
    # unep_points_to_overture.py avant de reactiver cette ligne.
    # 'unep': {
    #     'path': os.path.join(DONNEES, r"VENEZUELA\UNEP\debris_buildings_proj_Overture.gpkg"),
    #     'id_field': 'id', 'class_field': 'cm_matched',
    #     'damaged_values': [1, '1'], 'destroyed_values': [],
    #     'excluded_values': [],
    # },
    'eos': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\eos_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'],
        'excluded_values': [],
    },
    'nasa_s1': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s1_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'],
        'excluded_values': [],
    },
    'nasa_s2': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\nasa_s2_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': ['destroyed'],
        'excluded_values': [],
    },
    'ungsc': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\ungsc_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['damaged'], 'destroyed_values': [],
        'excluded_values': [],
    },
    't_test': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\t_test_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['Affected'], 'destroyed_values': [],
        'excluded_values': [],
    },
    'bdpm': {
        'path': os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\raster_sources_on_overture\bdpm_on_overture.gpkg"),
        'id_field': 'overture_id', 'class_field': 'classe',
        'damaged_values': ['Affected'], 'destroyed_values': [],
        'excluded_values': [],
    },
}

OUT_CSV = os.path.join(DONNEES, r"VENEZUELA\MOI\Source_AOI\analyse\comparaison_sources_vs_ems.csv")

SEP = "=" * 70


# =============================================================================
# HELPERS
# =============================================================================

def get_transform_to_wgs84(lyr):
    src_srs = lyr.GetSpatialRef()
    if src_srs is None:
        return None
    wgs84 = osr.SpatialReference(); wgs84.ImportFromEPSG(4326)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if src_srs.IsSame(wgs84):
        return None
    return osr.CoordinateTransformation(src_srs, wgs84)


def get_aoi_bounds(aoi_path):
    ds = ogr.Open(aoi_path)
    lyr = ds.GetLayer()
    tr = get_transform_to_wgs84(lyr)
    xmin = ymin = xmax = ymax = None
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g is None:
            continue
        g2 = g.Clone()
        if tr is not None:
            g2.Transform(tr)
        env = g2.GetEnvelope()
        xmin = env[0] if xmin is None else min(xmin, env[0])
        xmax = env[1] if xmax is None else max(xmax, env[1])
        ymin = env[2] if ymin is None else min(ymin, env[2])
        ymax = env[3] if ymax is None else max(ymax, env[3])
    ds = None
    return (xmin, ymin, xmax, ymax)


def load_classification(cfg, aoi_bounds=None):
    path = cfg['path']
    if not os.path.exists(path):
        return None, f"fichier introuvable : {path}"
    ds = ogr.Open(path)
    if ds is None:
        return None, f"impossible d'ouvrir : {path}"
    lyr = ds.GetLayer()
    defn = lyr.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
    if cfg['id_field'] not in field_names:
        ds = None
        return None, f"champ id '{cfg['id_field']}' introuvable — champs disponibles: {field_names}"
    if cfg['class_field'] not in field_names:
        ds = None
        return None, f"champ classe '{cfg['class_field']}' introuvable — champs disponibles: {field_names}"

    if aoi_bounds is not None:
        lyr.SetSpatialFilterRect(*aoi_bounds)

    out = {}
    for feat in lyr:
        oid = feat.GetField(cfg['id_field'])
        raw = feat.GetField(cfg['class_field'])
        if raw in (cfg.get('excluded_values') or []):
            continue
        if raw in cfg['destroyed_values']:
            out[oid] = 2
        elif raw in cfg['damaged_values']:
            out[oid] = 1
        else:
            out[oid] = 0
    ds = None
    return out, None


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t >= 1 and p >= 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p >= 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t >= 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else float('nan')
    recall = tp / (tp + fn) if (tp + fn) > 0 else float('nan')
    po = (tp + tn) / n if n > 0 else float('nan')
    p_pred = (tp + fp) / n if n > 0 else 0
    p_true = (tp + fn) / n if n > 0 else 0
    pe = p_pred * p_true + (1 - p_pred) * (1 - p_true)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return {'n': n, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': precision, 'recall': recall, 'kappa': kappa}


# =============================================================================
# PRE-FLIGHT CHECK
# =============================================================================

def preflight_check():
    print(f"{SEP}\n  Verification prealable de TOUS les fichiers (ID + classe)\n{SEP}")
    ok = True
    all_cfgs = {'EMS (reference)': GROUND_TRUTH, **SOURCES_ON_OVERTURE}
    for name, cfg in all_cfgs.items():
        path = cfg['path']
        if not os.path.exists(path):
            print(f"  {name:12s} : ATTENTION fichier introuvable — {path}")
            ok = False
            continue
        ds = ogr.Open(path)
        if ds is None:
            print(f"  {name:12s} : ATTENTION impossible d'ouvrir")
            ok = False
            continue
        lyr = ds.GetLayer()
        defn = lyr.GetLayerDefn()
        field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
        missing = [f for f in (cfg['id_field'], cfg['class_field']) if f not in field_names]
        if missing:
            print(f"  {name:12s} : ERREUR — champ(s) manquant(s) {missing}")
            print(f"               Champs disponibles: {field_names}")
            ok = False
            ds = None
            continue
        n_total = lyr.GetFeatureCount()
        vals = {}
        stride = max(1, n_total // 5000) if n_total > 0 else 1
        for i, feat in enumerate(lyr):
            if i % stride != 0:
                continue
            v = feat.GetField(cfg['class_field'])
            vals[v] = vals.get(v, 0) + 1
        matched = [v for v in vals if v in cfg['damaged_values'] or v in cfg['destroyed_values']]
        if not matched:
            # L'echantillon par pas regulier peut manquer une classe rare
            # mal repartie dans le fichier (deja constate sur BDPM) — un
            # scan COMPLET (pas juste un echantillon) confirme si c'est
            # vraiment absent ou juste mal echantillonne.
            lyr.ResetReading()
            vals_full = {}
            for feat in lyr:
                v = feat.GetField(cfg['class_field'])
                vals_full[v] = vals_full.get(v, 0) + 1
            matched_full = [v for v in vals_full if v in cfg['damaged_values'] or v in cfg['destroyed_values']]
            if matched_full:
                print(f"  {name:12s} : {n_total:,} entites — champ '{cfg['class_field']}' "
                      f"(echantillon vide, SCAN COMPLET): {vals_full} — OK")
            else:
                print(f"  {name:12s} : {n_total:,} entites — champ '{cfg['class_field']}' "
                      f"(SCAN COMPLET): {vals_full} — ATTENTION aucune valeur ne correspond")
                ok = False
        else:
            status = "OK"
            print(f"  {name:12s} : {n_total:,} entites — champ '{cfg['class_field']}' "
                  f"echantillon: {vals} — {status}")
        ds = None
    if not ok:
        sys.exit("\nCorrige la configuration ci-dessus avant de relancer.")
    print("  OK — tous les fichiers sont valides.\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    preflight_check()

    print(f"{SEP}\n  Chargement de la reference EMS\n{SEP}")
    aoi_bounds = get_aoi_bounds(AOI_PATH)
    gt, err = load_classification(GROUND_TRUTH, aoi_bounds)
    if gt is None:
        sys.exit(f"Erreur reference EMS: {err}")
    print(f"  {len(gt)} batiment(s) classes par EMS")

    rows = []
    for source_name, cfg in SOURCES_ON_OVERTURE.items():
        print(f"\n{SEP}\n  {source_name}\n{SEP}")
        src, err = load_classification(cfg, aoi_bounds)
        if src is None:
            print(f"  ERREUR: {err}")
            continue
        print(f"  {len(src)} batiment(s) classes")

        common_ids = set(gt.keys()) & set(src.keys())
        if not common_ids:
            print("  Aucun batiment en commun (IDs incompatibles ?) — ignore")
            continue
        y_true = [gt[oid] for oid in common_ids]
        y_pred = [src[oid] for oid in common_ids]
        m = compute_metrics(y_true, y_pred)
        print(f"  n={m['n']}  precision={m['precision']:.3f}  rappel={m['recall']:.3f}  kappa={m['kappa']:.3f}")
        rows.append({'source': source_name, **m})

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['source', 'n', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'kappa'])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{SEP}\nEcrit : {OUT_CSV}\n{SEP}")


if __name__ == '__main__':
    main()
