# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 77 — UNE IMAGE SUFFIT-ELLE ? DANS LA CONFIGURATION DU GREFFON
===============================================================================

CE QUI A CONDUIT ICI
--------------------
L'experience 20a a montre que la premiere acquisition Sentinel-1 arrive en
mediane 30,3 h apres l'evenement, et qu'une seule image est disponible a 48 h
dans 25 zones sur 29 — mais DEUX images dans 4 zones seulement. Or le test de
Welch de la methode publiee masque tout pixel ayant moins de deux images apres :

    valid_mask = pre_n.gte(3).And(post_n.gte(2))

La cible de 48 heures est donc, telle quelle, hors de portee du mode principal.

LA REPONSE EST DEJA DANS LE CODE PUBLIE
----------------------------------------
Le module de reference contient `method='ztest'`, qui compare UNE SEULE image
post a la ligne de base pre-evenement :

    z = |x - moyenne_pre| / ecart_type_pre,   valid_mask = pre_n.gte(3)

Aucune exigence sur le nombre d'images apres. Il n'y a donc pas de variante a
inventer : il y a une branche prevue pour ce cas, et la question est de savoir
ce qu'elle coute.

TROIS DIFFERENCES A GARDER EN TETE
-----------------------------------
1. C'est un z et non un t : la division se fait par l'ecart-type pre sans la
   correction sqrt(1 + 1/n_pre) qu'exigerait un intervalle de prediction. Avec
   28 images pre, cette correction vaut 1,8 %.
2. La combinaison des orbites passe par le MAXIMUM et non par Stouffer. Cette
   difference a ete mesuree en experience 6 : -0,0008 d'AUC, negligeable.
3. Le seuil de 3,30 a ete etabli sur le t, pas sur le z. Les deux n'ont pas la
   meme echelle, et le seuil optimal est donc recalcule ici pour chaque mode.

CE QUE LE SCRIPT COMPARE
------------------------
Pour chaque zone : le z-test a une image, puis le test de Welch a 2, 3, 5, 7 et
9 images. Les fenetres sont definies par le NOMBRE d'images, la duree en jours
etant rapportee a cote — la revisite differant d'un pays a l'autre, un axe en
jours melangerait des situations non comparables.

TROIS ISSUES POSSIBLES, ET ELLES N'APPELLENT PAS LA MEME RECOMMANDATION
------------------------------------------------------------------------
  - le z-test a 1 image se tient pres du Welch a 2 ou 3 images : la bascule
    « une image -> z-test » est justifiee, et attendre ne vaut pas le detour ;
  - il s'effondre : il faut annoncer que 48 h donne une indication, pas une
    carte ;
  - il est aussi bon partout : autant l'employer toujours, et se passer de
    toute bascule.
===============================================================================
"""
import csv
import glob
import io
import os
import sys
import time
import types
import urllib.request
import zipfile

if "geemap" not in sys.modules:
    sys.modules["geemap"] = types.ModuleType("geemap")

import numpy as np
import ee
from osgeo import gdal, ogr, osr

_ICI = os.path.dirname(os.path.abspath(__file__))
# `config` et `evaluation_commune` vivent dans `src/`, un niveau au-dessus.
sys.path.insert(0, _ICI)
sys.path.insert(0, os.path.dirname(_ICI))
from config import DONNEES, TRAVAUX, REEVALUATION, MODULES_TSTAT  # noqa: E402,F401
import evaluation_commune as ev

gdal.UseExceptions(); ogr.UseExceptions()

PROJET_GEE = "rapiddamagedetection"
REF = os.path.join(MODULES_TSTAT, "pwtt_masque_parametrable.py")
OUT = os.path.join(TRAVAUX, "exp77_une_image")
RES = os.path.join(REEVALUATION, "resultats")
os.makedirs(OUT, exist_ok=True); os.makedirs(RES, exist_ok=True)

J = os.path.join(DONNEES, r"JAMAIQUE\_etude_p95")
V = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL")
C = os.path.join(DONNEES, r"COLOMBIE\CEMS\EMSR916")
COL_BATI = os.path.join(TRAVAUX, "exp17_colombie")
CUB_BATI = os.path.join(TRAVAUX, "exp14_cuba")

N_IMAGES = [2, 3, 5, 7, 9]
PRE_MOIS = 12
ECHELLE_M = 10
MIN_DOMMAGE = 30
GRILLE = np.round(np.arange(0.5, 12.01, 0.05), 2)
JOURS_PAR_MOIS = 30.436875
# Au-dela, la requete depasse le plafond de 50 Mo : on decoupe.
SEUIL_DECOUPE_KM2 = 250.0

BATI_JAM = os.path.join(DONNEES, r"JAMAIQUE\AOI\OSM_AOI_ttest.gpkg")
BATI_VEN = os.path.join(V, "EMSR884_Building_Overture.gpkg")
POSITIFS = {'Damaged', 'Possibly damaged', 'Destroyed'}

U = os.path.join(J, "unosat", "TC20251028JAM_SHP")
ZONES = [
    ("UNOSAT_WhiteHouse", "Jamaique", "cyclone", "2025-10-28",
     os.path.join(U, 'AP_20251031_AnalysisExtent_WhiteHouse.shp'), None, None,
     os.path.join(U, 'AP_20251031_Damagedbuilding_WhiteHouse.shp'),
     "Main_Damag", {1, 13}, BATI_JAM),
    ("UNOSAT_BlackRiverVillage", "Jamaique", "cyclone", "2025-10-28",
     os.path.join(U, 'WV2_20251029_AnalysisExtent_BlackRiverVillage.shp'), None, None,
     os.path.join(U, 'WV2_20251029_DamagedBuildings_BlackRiverVillage.shp'),
     "Main_Damag", {1, 13}, BATI_JAM),
    ("EMS_AOI26", "Jamaique", "cyclone", "2025-10-28",
     (J, "emsr", 'EMSR847_AOI26_GRA_MONIT02_v1'), None, None, None,
     "damage_gra", POSITIFS, BATI_JAM),
    ("EMS_AOI29", "Jamaique", "cyclone", "2025-10-28",
     (J, "emsr", 'EMSR847_AOI29_GRA_MONIT01_v1'), None, None, None,
     "damage_gra", POSITIFS, BATI_JAM),
    ("EMS_AOI39", "Jamaique", "cyclone", "2025-10-28",
     (J, "emsr", 'EMSR847_AOI39_GRA_PRODUCT_v1'), None, None, None,
     "damage_gra", POSITIFS, BATI_JAM),
    ("CUBA_AOI25", "Cuba", "cyclone", "2025-10-29",
     (J, "emsr", 'EMSR847_AOI25_GRA_PRODUCT_v1'), None, None, None,
     "damage_gra", POSITIFS, os.path.join(CUB_BATI, "CUBA_AOI25_batiments.geojson")),
    ("COL_AOI02", "Colombie", "seisme", "2026-08-10",
     (C, "", 'EMSR916_AOI02_GRA_PRODUCT_v1'), None, None, None,
     "damage_gra", POSITIFS, os.path.join(COL_BATI, "COL_AOI02_batiments.geojson")),
]
VEN = ["caraballeda", "catia_la_mar", "la_guaira"]

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def log(m):
    print(m); sys.stdout.flush()


def emprise_et_boite(path, champ=None, valeur=None):
    d = ogr.Open(path); ly = d.GetLayer(); tr = ev.to_wgs84(ly)
    g = None
    for f in ly:
        if champ is not None and str(f.GetField(champ)).replace(" ", "_") != valeur:
            continue
        g = f.GetGeometryRef().Clone()
        if tr is not None:
            g.Transform(tr)
        if not g.IsValid():
            g = g.MakeValid()
        break
    d = None
    if g is None:
        return None, None
    e = g.GetEnvelope()
    return g, [e[0], e[2], e[1], e[3]]


def surface_km2(b):
    import math
    lat = (b[1] + b[3]) / 2.0
    return ((b[2] - b[0]) * 111.32 * math.cos(math.radians(lat))
            * (b[3] - b[1]) * 110.57)


def telecharger_image(img, boite, dest, decoupe=1):
    """Telechargement, avec decoupage en grille si l'emprise est trop grande."""
    if decoupe <= 1:
        url = img.getDownloadURL(
            {"scale": ECHELLE_M, "region": ee.Geometry.Rectangle(boite),
             "format": "GEO_TIFF", "crs": "EPSG:4326"})
        with urllib.request.urlopen(url, timeout=1800) as r:
            brut = r.read()
        if brut[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(brut))
            brut = z.read([n for n in z.namelist() if n.endswith(".tif")][0])
        io.open(dest, "wb").write(brut)
        return dest
    dx = (boite[2] - boite[0]) / decoupe
    dy = (boite[3] - boite[1]) / decoupe
    tuiles = []
    for i in range(decoupe):
        for j in range(decoupe):
            r4 = [boite[0] + i * dx, boite[1] + j * dy,
                  boite[0] + (i + 1) * dx, boite[1] + (j + 1) * dy]
            f = dest.replace(".tif", "_t%d%d.tif" % (i, j))
            try:
                url = img.getDownloadURL(
                    {"scale": ECHELLE_M, "region": ee.Geometry.Rectangle(r4),
                     "format": "GEO_TIFF", "crs": "EPSG:4326"})
                with urllib.request.urlopen(url, timeout=1800) as r:
                    brut = r.read()
                if brut[:2] == b"PK":
                    z = zipfile.ZipFile(io.BytesIO(brut))
                    brut = z.read([n for n in z.namelist() if n.endswith(".tif")][0])
                io.open(f, "wb").write(brut); tuiles.append(f)
            except Exception as exc:
                log("        tuile %d%d echec : %s" % (i, j, str(exc)[:70]))
    if not tuiles:
        raise RuntimeError("aucune tuile")
    if len(tuiles) == 1:
        os.replace(tuiles[0], dest)
    else:
        vrt = dest.replace(".tif", ".vrt")
        gdal.BuildVRT(vrt, tuiles)
        gdal.Translate(dest, vrt, creationOptions=["COMPRESS=DEFLATE"])
        for f in tuiles + [vrt]:
            try:
                os.remove(f)
            except OSError:
                pass
    return dest


def metriques_au_seuil(y, v, s):
    ok = np.isfinite(v)
    pred = np.zeros(len(y), np.int8)
    pred[ok] = (v[ok] >= s).astype(np.int8)
    m = ev.metriques(y, pred)
    if m is None:
        return None
    se = m['tp'] / (m['tp'] + m['fn']) if (m['tp'] + m['fn']) else float('nan')
    sp = m['tn'] / (m['tn'] + m['fp']) if (m['tn'] + m['fp']) else float('nan')
    m['sensibilite'] = se; m['specificite'] = sp; m['youden'] = se + sp - 1.0
    return m


# --- Inventaire ---------------------------------------------------------------
cibles = []
for (nom, pays, alea, date, loc, champ, valeur, pts_path,
     champ_dmg, positifs, bati) in ZONES:
    if isinstance(loc, tuple):
        racine, sous, dossier = loc
        a = glob.glob(os.path.join(racine, sous, dossier, "**",
                                   "*areaOfInterestA*.shp"), recursive=True)
        p = glob.glob(os.path.join(racine, sous, dossier, "**",
                                   "*builtUpP*.shp"), recursive=True)
        if not (a and p):
            log("  %s introuvable" % nom); continue
        cibles.append((nom, pays, alea, date, a[0], None, None, p[0],
                       champ_dmg, positifs, bati))
    else:
        cibles.append((nom, pays, alea, date, loc, champ, valeur, pts_path,
                       champ_dmg, positifs, bati))
AOI_VEN = os.path.join(V, "EMSR884_areOfinterestA_v3.gpkg")
for n in VEN:
    cibles.append(("VENEZ_" + n, "Venezuela", "seisme", "2026-06-25",
                   AOI_VEN, "area", n,
                   os.path.join(V, "EMSR884_builtUpPV2.gpkg"),
                   "damage_gra", POSITIFS, BATI_VEN))

log("%d zones, 1 z-test + %d fenetres multi-images." % (len(cibles), len(N_IMAGES)))
log("")

ee.Initialize(project=PROJET_GEE)
import importlib.util
spec = importlib.util.spec_from_file_location("pwtt_mp", REF)
pwtt = importlib.util.module_from_spec(spec); spec.loader.exec_module(pwtt)

lignes = []
for (nom, pays, alea, date, emprise_path, champ, valeur,
     points_path, champ_dmg, positifs, bati) in cibles:
    emp, boite = emprise_et_boite(emprise_path, champ, valeur)
    if emp is None or not os.path.exists(bati):
        log("  %-24s emprise ou bati absent" % nom); continue
    km2 = surface_km2(boite)
    decoupe = 1 if km2 < SEUIL_DECOUPE_KM2 else (2 if km2 < 900 else 3)
    aoi = ee.Geometry.Rectangle(boite)
    try:
        ts = sorted((ee.ImageCollection("COPERNICUS/S1_GRD")
                     .filter(ee.Filter.eq("instrumentMode", "IW"))
                     .filterBounds(aoi)
                     .filterDate(ee.Date(date), ee.Date(date).advance(200, 'day'))
                     .aggregate_array("system:time_start").getInfo()) or [])
    except Exception as exc:
        log("  %-24s acquisitions illisibles : %s" % (nom, str(exc)[:60])); continue
    if len(ts) < 2:
        log("  %-24s moins de deux acquisitions" % nom); continue
    t_ev = np.datetime64(date + "T00:00:00")
    jours = [float((np.datetime64(int(t), "ms") - t_ev) / np.timedelta64(1, "D"))
             for t in ts]
    log("  %-24s %-10s %6.0f km2, decoupe %d ; images post a %s j"
        % (nom, pays, km2, decoupe,
           ", ".join("%.1f" % d for d in jours[:6])))

    pts = ev.lire_points(points_path, champ_dmg, positifs)
    y = None
    plans = [("ztest", 1, jours[0] + 0.5)]
    plans += [("poole", n, jours[n - 1] + 0.5) for n in N_IMAGES if n <= len(ts)]

    for mode, n_img, fin_j in plans:
        dest = os.path.join(OUT, "%s__%s_n%02d.tif" % (nom, mode, n_img))
        if not (os.path.exists(dest) and os.path.getsize(dest) > 3000):
            t0 = time.time()
            try:
                img = pwtt.detect_damage(
                    aoi=aoi, inference_start=date, war_start=date,
                    pre_interval=PRE_MOIS,
                    post_interval=fin_j / JOURS_PAR_MOIS,
                    method=("ztest" if mode == "ztest" else "max"),
                    ttest_type="pooled",
                    viz=False, export=False, clip=True)
                telecharger_image(img.select("T_statistic"), boite, dest, decoupe)
            except Exception as exc:
                log("      %-6s n=%2d ECHEC : %s" % (mode, n_img, str(exc)[:90]))
                continue
        try:
            lat, lon, vals, npix, _o = ev.stats_batiments(
                bati, dest, emp, avec_orientation=False)
        except Exception as exc:
            log("      %-6s n=%2d illisible : %s" % (mode, n_img, str(exc)[:60]))
            continue
        if len(lat) < 50:
            log("      %-6s n=%2d %d batiments seulement" % (mode, n_img, len(lat)))
            continue
        if y is None or len(y) != len(lat):
            y = ev.accrocher(pts, np.asarray(lat), np.asarray(lon))
        if int(y.sum()) < MIN_DOMMAGE:
            log("      %-6s n=%2d %d dommages < %d"
                % (mode, n_img, int(y.sum()), MIN_DOMMAGE)); continue
        v = list(vals.values())[0]
        if not np.isfinite(v).any():
            log("      %-6s n=%2d raster entierement masque" % (mode, n_img)); continue
        a = ev.auc(y, v)
        best = None
        for s in GRILLE:
            m = metriques_au_seuil(y, v, s)
            if m and m["kappa"] == m["kappa"] and (
                    best is None or m["kappa"] > best[1]["kappa"]):
                best = (float(s), m)
        l = dict(zone=nom, pays=pays, alea=alea, mode=mode, n_images_post=n_img,
                 duree_post_jours=round(fin_j, 2),
                 delai_premiere_image_h=round(jours[0] * 24.0, 1),
                 n_batiments=len(lat), n_endommages=int(y.sum()),
                 prevalence_pct=round(100.0 * y.sum() / len(lat), 2),
                 auc=round(a, 4),
                 valeur_mediane=round(float(np.nanmedian(v)), 3))
        if best:
            l["kappa_max"] = round(best[1]["kappa"], 4)
            l["seuil_kappa"] = best[0]
            l["se_kappa"] = round(best[1]["sensibilite"], 4)
            l["sp_kappa"] = round(best[1]["specificite"], 4)
        lignes.append(l)
        log("      %-6s n=%2d (%5.1f j) : AUC %.4f  kappa_max %-7s seuil %s"
            % (mode, n_img, fin_j, a, l.get("kappa_max", "n/a"),
               l.get("seuil_kappa", "n/a")))

if not lignes:
    log("Aucune ligne produite."); sys.exit()

ev.ecrire_csv(os.path.join(RES, "exp77_une_image_regroupee.csv"), lignes)

# --- Synthese appariee : le z-test a une image contre n images --------------
par_zone = {}
for l in lignes:
    par_zone.setdefault(l["zone"], {})[(l["mode"], l["n_images_post"])] = l
synth = []
for n in N_IMAGES:
    d_auc, d_kap, gagne, paires = [], [], 0, 0
    for zone, d in par_zone.items():
        z = d.get(("ztest", 1)); w = d.get(("poole", n))
        if not z or not w:
            continue
        paires += 1
        d_auc.append(z["auc"] - w["auc"])
        if "kappa_max" in z and "kappa_max" in w:
            d_kap.append(z["kappa_max"] - w["kappa_max"])
        if z["auc"] >= w["auc"]:
            gagne += 1
    if paires:
        synth.append(dict(
            comparaison="z-test 1 image contre variance regroupee %d images" % n,
            n_paires=paires,
            delta_auc_moyen=round(float(np.mean(d_auc)), 4),
            delta_auc_median=round(float(np.median(d_auc)), 4),
            delta_kappa_median=round(float(np.median(d_kap)), 4) if d_kap else "",
            zones_ou_le_ztest_egale_ou_depasse=gagne))
ev.ecrire_csv(os.path.join(RES, "exp77_synthese.csv"), synth)

log("")
log("=" * 78)
log("LE Z-TEST A UNE IMAGE CONTRE LA VARIANCE REGROUPEE A N IMAGES")
log("=" * 78)
log("%-34s %8s %12s %12s %16s" % ("comparaison", "zones", "Δ AUC med",
                                   "Δ kappa med", "z-test >= multi"))
for s in synth:
    log("%-34s %8d %12.4f %12s %14d/%d"
        % (s["comparaison"][:34], s["n_paires"], s["delta_auc_median"],
           s["delta_kappa_median"], s["zones_ou_le_ztest_egale_ou_depasse"],
           s["n_paires"]))
log("")
log("Resultats : exp77_une_image_regroupee.csv (%d lignes) et exp77_synthese.csv"
    % len(lignes))
