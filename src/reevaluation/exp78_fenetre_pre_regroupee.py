# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 49 — QUELLE LONGUEUR DE LIGNE DE BASE ?
===============================================================================

CE QUI N'AVAIT JAMAIS ETE MESURE
---------------------------------
PRE_MOIS = 12 figure a l'identique dans les douze scripts de calcul du
projet, avec le commentaire « defaut de l'auteur ». La longueur de la ligne
de base n'a jamais ete balayee. Les experiences 35 et 36 ont compare des
TYPES de ligne de base — glissante contre saisonniere sur un, deux et quatre
ans — et trouve la glissante de douze mois meilleure (AUC mediane 0,7135
contre 0,677, 0,663 et 0,673). Elles n'ont pas compare des LONGUEURS.

CE QUE CETTE EXPERIENCE FAIT
-----------------------------
Elle reprend la chaine de l'experience 21 sans y toucher, et n'en change
qu'une variable :

    experience 21    pre_interval = 12 mois fixe, post = 1, 3, 5, 7, 9 images
    experience 49    pre_interval = 3, 6, 9, 12, 18, 24 mois
                     post = 3 images fixe, soit le reglage de reference

CE QUE LA COURBE DEVRAIT MONTRER, ET POURQUOI
----------------------------------------------
Allonger la ligne de base augmente le nombre d'images, donc la puissance du
test : la dispersion de reference est mieux estimee. Mais elle eloigne aussi
la reference dans le temps et importe la transformation reelle du bati —
constructions, demolitions, vegetation. C'est le mecanisme que l'experience
36 a isole sous le nom de derive seculaire, et qui multipliait le bruit de
fond par neuf sur quatre ans.

Les deux effets jouant en sens contraire, un OPTIMUM INTERMEDIAIRE est
attendu. Le situer est l'objet de l'experience. Un optimum a douze mois
confirmerait le defaut herite ; un optimum ailleurs le remettrait en cause.

CE QUI EST RAPPORTE
-------------------
Pour chaque zone et chaque fenetre : l'AUC, le nombre d'images de la ligne
de base effectivement trouvees, et la mediane de la statistique. Le nombre
d'images compte autant que la fenetre : une fenetre de trois mois peut ne
contenir que deux images, auquel cas le test n'est plus calculable.
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
OUT = os.path.join(TRAVAUX, "exp78_fenetre_pre")
RES = os.path.join(REEVALUATION, "resultats")
os.makedirs(OUT, exist_ok=True); os.makedirs(RES, exist_ok=True)

J = os.path.join(DONNEES, r"JAMAIQUE\_etude_p95")
V = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL")
C = os.path.join(DONNEES, r"COLOMBIE\CEMS\EMSR916")
COL_BATI = os.path.join(TRAVAUX, "exp17_colombie")
CUB_BATI = os.path.join(TRAVAUX, "exp14_cuba")

# Les fenetres de ligne de base balayees, en mois.
PRE_LISTE = [3, 6, 9, 12, 18, 24]
# La fenetre post reste au reglage de reference : trois images.
N_POST = 3
PRE_MOIS = 12          # conserve pour les appels qui ne balaient pas
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

log("%d zones x %d fenetres de ligne de base (%s mois), post fixe a %d images."
    % (len(cibles), len(PRE_LISTE),
       ", ".join(str(p) for p in PRE_LISTE), N_POST))
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
    # Une entree par fenetre de ligne de base ; la fenetre post ne bouge pas.
    if len(ts) < N_POST:
        log("  %-24s moins de %d images post" % (nom, N_POST)); continue
    fin_j = jours[N_POST - 1] + 0.5
    plans = [("poole", pm, fin_j) for pm in PRE_LISTE]

    for mode, pre_m, fin_j in plans:
        n_img = N_POST
        dest = os.path.join(OUT, "%s__pre%02dm.tif" % (nom, pre_m))
        if not (os.path.exists(dest) and os.path.getsize(dest) > 3000):
            t0 = time.time()
            try:
                img = pwtt.detect_damage(
                    aoi=aoi, inference_start=date, war_start=date,
                    pre_interval=pre_m,
                    post_interval=fin_j / JOURS_PAR_MOIS,
                    method=("ztest" if mode == "ztest" else "max"),
                    ttest_type="pooled",
                    viz=False, export=False, clip=True)
                _passageres = ("503", "502", "504", "429",
                               "service unavailable", "too many requests",
                               "timed out", "connection reset")
                _d, _ok, _essai = decoupe, False, 0
                while not _ok and _d <= 16:
                    try:
                        telecharger_image(img.select("T_statistic"), boite,
                                          dest, _d)
                        _ok = True
                    except Exception as _e:
                        _m = str(_e).lower()
                        if any(_p in _m for _p in _passageres) and _essai < 3:
                            # Rien a voir avec la taille : on repatiente.
                            _essai += 1
                            time.sleep(5 * _essai)
                            continue
                        _d *= 2
                        log("      decoupage porte a %d apres : %s"
                            % (_d, str(_e)[:70]))
                if not _ok:
                    raise RuntimeError("echec meme en 16 morceaux par cote")
            except Exception as exc:
                log("      pre=%2d m ECHEC : %s" % (pre_m, str(exc)[:90]))
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
        l = dict(zone=nom, pays=pays, alea=alea, mode=mode,
                 fenetre_pre_mois=pre_m, n_images_post=n_img,
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

ev.ecrire_csv(os.path.join(RES, "exp78_fenetre_pre_detail.csv"), lignes)

# --- Synthese : une ligne par fenetre de ligne de base ----------------------
par_zone = {}
for l in lignes:
    par_zone.setdefault(l["zone"], {})[l["fenetre_pre_mois"]] = l

# Pour chaque zone, la fenetre qui obtient la meilleure AUC.
meilleure = {}
for zone, d in par_zone.items():
    bons = [(v["auc"], pm) for pm, v in d.items() if v.get("auc") == v.get("auc")]
    if bons:
        meilleure[zone] = max(bons)[1]

synth = []
for pm in PRE_LISTE:
    aucs, n_pre = [], []
    for zone, d in par_zone.items():
        v = d.get(pm)
        if v and v.get("auc") == v.get("auc"):
            aucs.append(v["auc"])
            if v.get("n_images_pre"):
                n_pre.append(v["n_images_pre"])
    if not aucs:
        continue
    synth.append(dict(
        fenetre_pre_mois=pm,
        n_zones=len(aucs),
        auc_mediane=round(float(np.median(aucs)), 4),
        auc_moyenne=round(float(np.mean(aucs)), 4),
        auc_min=round(float(np.min(aucs)), 4),
        auc_max=round(float(np.max(aucs)), 4),
        n_images_pre_mediane=(round(float(np.median(n_pre)), 1) if n_pre else ""),
        zones_ou_cette_fenetre_est_la_meilleure=sum(
            1 for z, b in meilleure.items() if b == pm)))
ev.ecrire_csv(os.path.join(RES, "exp78_fenetre_pre.csv"), synth)

log("")
log("=" * 78)
log("QUELLE LONGUEUR DE LIGNE DE BASE ?")
log("=" * 78)
log("%-12s %7s %11s %11s %11s %11s %12s"
    % ("fenetre", "zones", "AUC med", "AUC moy", "min", "max", "meilleure"))
for r in synth:
    log("%-12s %7d %11.4f %11.4f %11.4f %11.4f %10d/%d"
        % ("%d mois" % r["fenetre_pre_mois"], r["n_zones"], r["auc_mediane"],
           r["auc_moyenne"], r["auc_min"], r["auc_max"],
           r["zones_ou_cette_fenetre_est_la_meilleure"], r["n_zones"]))
log("")
log("Resultats : exp78_fenetre_pre_detail.csv (%d lignes) et exp78_fenetre_pre.csv"
    % len(lignes))
