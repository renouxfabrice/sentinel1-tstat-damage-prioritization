# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 81 — REEVALUER LES CARTES DE L'EXPERIENCE 78
===============================================================================

POURQUOI

L'experience 77 a refait les CALCULS dans la configuration du greffon, mais elle
a herite de l'EVALUATION de l'experience 21 : la Jamaique y est jugee sur
OpenStreetMap, et les points de signalement sont rattaches aux empreintes par
accrochage a vingt metres du centroide, sans interdiction de doublon.

Ce sont les deux defauts corriges par ailleurs. Les laisser ici reviendrait a
faire coexister deux conventions d'evaluation dans le meme memoire — ce que
l'annexe X interdit explicitement, puisqu'elle annonce une regle valable pour
toutes les comparaisons.

CE QUE FAIT CE PROGRAMME

Il ne recalcule aucune carte : elles existent toutes dans
`Etude\exp77_une_image`. Il les reevalue, avec

  couche batie    Open Buildings en Jamaique, Overture au Venezuela, et les
                  couches propres a Cuba et a la Colombie ;
  appariement     la regle stricte du module `appariement` ;
  fiabilite       prevalence bornee entre 5 et 95 %.

Il repond ensuite aux trois affirmations du memoire, comme le faisait le
controle precedent, mais sur la bonne base.
===============================================================================
"""
import csv
import glob
import io
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import DONNEES, TRAVAUX, REEVALUATION  # noqa: E402,F401
BASE, ETUDE = REEVALUATION, TRAVAUX
import evaluation_commune as ev
import appariement as ap

CARTES = os.path.join(ETUDE, "exp78_fenetre_pre")
RES = os.path.join(BASE, "resultats")

J = os.path.join(DONNEES, r"JAMAIQUE\_etude_p95")
U = os.path.join(J, "unosat", "TC20251028JAM_SHP")
V = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL")
COL = os.path.join(ETUDE, "exp17_colombie")
CUB = os.path.join(ETUDE, "exp14_cuba")

OPEN_BUILDINGS = os.path.join(DONNEES, r"JAMAIQUE\AOI\Open_Building_AOI_t_test.gpkg")
OVERTURE = os.path.join(V, "EMSR884_Building_Overture.gpkg")
POSITIFS = {"Damaged", "Possibly damaged", "Destroyed"}

PREV_MIN, PREV_MAX = 5.0, 95.0
MIN_DOMMAGE = 20
N_SEUILS = 100

NOMS = {
    "EMS_AOI26": "Arlington (AOI26)", "EMS_AOI29": "Bartons (AOI29)",
    "EMS_AOI39": "White House (AOI39)",
    "UNOSAT_WhiteHouse": "White House (UNOSAT)",
    "UNOSAT_BlackRiverVillage": "Black River Village (UNOSAT)",
    "CUBA_AOI25": "Jiguaní (AOI25)", "COL_AOI02": "Pereira (AOI02)",
    "VENEZ_caraballeda": "Caraballeda (AOI12)",
    "VENEZ_catia_la_mar": "Catia La Mar (AOI12)",
    "VENEZ_la_guaira": "La Guaira (AOI12)",
}


def log(m):
    print(m); sys.stdout.flush()


def fr(x, n=4, signe=False):
    s = ("%+.*f" if signe else "%.*f") % (n, float(x))
    return s.replace(".", ",").replace("-", "\u2212")


def emsr(dossier, motif):
    p = glob.glob(os.path.join(J, "emsr", dossier, motif))
    return p[0] if p else None


# zone -> (emprise, points, champ, positifs, couche batie, pays)
ZONES = {}
for code, dossier in (("EMS_AOI26", "EMSR847_AOI26_GRA_MONIT02_v1"),
                      ("EMS_AOI29", "EMSR847_AOI29_GRA_MONIT01_v1"),
                      ("EMS_AOI39", "EMSR847_AOI39_GRA_PRODUCT_v1")):
    a, p = emsr(dossier, "*areaOfInterestA*.shp"), emsr(dossier, "*builtUpP*.shp")
    if a and p:
        ZONES[code] = (a, p, "damage_gra", POSITIFS, OPEN_BUILDINGS, "Jamaique")

ZONES["UNOSAT_WhiteHouse"] = (
    os.path.join(U, "AP_20251031_AnalysisExtent_WhiteHouse.shp"),
    os.path.join(U, "AP_20251031_Damagedbuilding_WhiteHouse.shp"),
    "Main_Damag", {1, 13}, OPEN_BUILDINGS, "Jamaique")
ZONES["UNOSAT_BlackRiverVillage"] = (
    os.path.join(U, "WV2_20251029_AnalysisExtent_BlackRiverVillage.shp"),
    os.path.join(U, "WV2_20251029_DamagedBuildings_BlackRiverVillage.shp"),
    "Main_Damag", {1, 13}, OPEN_BUILDINGS, "Jamaique")

a, p = emsr("EMSR847_AOI25_GRA_PRODUCT_v1", "*areaOfInterestA*.shp"), \
       emsr("EMSR847_AOI25_GRA_PRODUCT_v1", "*builtUpP*.shp")
if a and p:
    ZONES["CUBA_AOI25"] = (a, p, "damage_gra", POSITIFS,
                           os.path.join(CUB, "CUBA_AOI25_batiments.geojson"), "Cuba")

for nom in os.listdir(COL) if os.path.isdir(COL) else []:
    if nom == "COL_AOI02_batiments.geojson":
        emp = glob.glob(os.path.join(
            os.path.join(DONNEES, "COLOMBIE"), "**",
            "EMSR916_AOI02*areaOfInterestA*.shp"), recursive=True)
        pts = glob.glob(os.path.join(
            os.path.join(DONNEES, "COLOMBIE"), "**",
            "EMSR916_AOI02*builtUpP*.shp"), recursive=True)
        if emp and pts:
            ZONES["COL_AOI02"] = (emp[0], pts[0], "damage_gra", POSITIFS,
                                  os.path.join(COL, nom), "Colombie")

AOI_VEN = os.path.join(V, "EMSR884_areOfinterestA_v3.gpkg")
PTS_VEN = os.path.join(V, "EMSR884_builtUpP.gpkg")
for code, aire in (("VENEZ_caraballeda", "caraballeda"),
                   ("VENEZ_catia_la_mar", "catia_la_mar"),
                   ("VENEZ_la_guaira", "la_guaira")):
    ZONES[code] = ((AOI_VEN, "area", aire), PTS_VEN, "damage_gra", POSITIFS,
                   OVERTURE, "Venezuela")

def emprise_filtree(chemin, champ, valeur):
    """Une seule emprise d'un fichier qui en contient plusieurs.

    Les trois emprises venezueliennes partagent un fichier et se distinguent par
    la valeur d'un champ. `lire_emprise` additionne toutes les geometries : il
    faut donc selectionner avant.
    """
    from osgeo import ogr, osr
    d = ogr.Open(chemin)
    if d is None:
        return None
    ly = d.GetLayer()
    wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    s = ly.GetSpatialRef(); tr = None
    if s is not None:
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not s.IsSame(wgs):
            tr = osr.CoordinateTransformation(s, wgs)
    for f in ly:
        if str(f.GetField(champ)).replace(" ", "_") != valeur:
            continue
        g = f.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        return g
    return None


lignes = []
t0 = time.time()
log("%-30s %9s %8s %9s %11s" % ("emprise", "bâtiments", "points", "positifs",
                                "prévalence"))
log("-" * 74)

for zone in sorted(ZONES):
    emp, pts, champ, positifs, couche, pays = ZONES[zone]
    cartes = sorted(glob.glob(os.path.join(CARTES, "%s__*.tif" % zone)))
    if not cartes:
        log("%-30s aucune carte" % NOMS.get(zone, zone)); continue
    if isinstance(emp, tuple):
        e = emprise_filtree(*emp)
    else:
        e = ev.lire_emprise(emp)
    if e is None:
        log("%-30s emprise illisible" % NOMS.get(zone, zone)); continue
    if not os.path.exists(couche):
        log("%-30s couche bâtie absente" % NOMS.get(zone, zone)); continue

    # La carte qui sert d'ancre doit etre une carte reellement calculee : le
    # cas n=2 echoue partout et laisse un raster vide, qui ne rendrait aucun
    # batiment. On prend donc la plus volumineuse.
    ancre = max(cartes, key=os.path.getsize)
    lat, lon, _v, geoms = ap.batiments_et_valeurs(couche, ancre, e)
    if len(lat) < 50:
        log("%-30s %9d bâtiments — trop peu" % (NOMS.get(zone, zone), len(lat)))
        continue
    p_ = ap.lire_points(pts, champ, positifs, e)
    y = ap.apparier(geoms, lat, lon, p_)
    nd = int(y.sum())
    prev = 100.0 * nd / len(lat)
    log("%-30s %9d %8d %9d %10.2f %%" % (NOMS.get(zone, zone), len(lat),
                                         len(p_), nd, prev))
    if nd < MIN_DOMMAGE or prev >= 100.0:
        log("      écartée"); continue

    for c in cartes:
        base = os.path.basename(c)[:-4]
        suffixe = base.split("__", 1)[1]
        # Le suffixe est de la forme « pre09m » : on en tire la duree de la
        # periode de reference, en mois.
        if not suffixe.startswith("pre"):
            continue
        try:
            mois = int(suffixe[3:].rstrip("m"))
        except ValueError:
            continue
        la2, lo2, vals, _n, _o = ev.stats_batiments(couche, c, e,
                                                    avec_orientation=False)
        v2 = list(vals.values())[0]
        if len(la2) == len(lat) and np.allclose(la2, lat, atol=1e-9):
            v = v2
        else:
            idx = {(round(float(la2[k]), 7), round(float(lo2[k]), 7)): v2[k]
                   for k in range(len(la2))}
            v = np.array([idx.get((round(float(lat[k]), 7),
                                   round(float(lon[k]), 7)), np.nan)
                          for k in range(len(lat))], np.float32)
        fini = v[np.isfinite(v)]
        if fini.size < 50:
            continue
        a_ = ev.auc(y, v)
        if not np.isfinite(a_):
            continue
        seuils = np.quantile(fini, np.linspace(0.01, 0.995, N_SEUILS))
        best = ev.meilleur_seuil(y, v, seuils)
        lignes.append(dict(
            zone=zone, emprise=NOMS.get(zone, zone), pays=pays,
            fenetre_pre_mois=mois, n_batiments=len(lat), n_endommages=nd,
            prevalence_pct=round(prev, 3), auc=round(a_, 4),
            kappa_max=round(best["kappa"], 4) if best else ""))

if not lignes:
    sys.exit("aucune évaluation produite")

dest = os.path.join(RES, "exp81_fenetre_pre_reevaluee.csv")
ev.ecrire_csv(dest, lignes)
log("\nDétail : exp81_fenetre_pre_reevaluee.csv (%d lignes, %.0f s)"
    % (len(lignes), time.time() - t0))

# ── la lecture du balayage ──────────────────────────────────────────
par = {}
for l in lignes:
    par.setdefault(l["fenetre_pre_mois"], []).append(l)

douze = [l for l in lignes if l["fenetre_pre_mois"] == 12
         and PREV_MIN <= l["prevalence_pct"] <= PREV_MAX]
ref = {l["zone"]: l["auc"] for l in douze}

log("")
log("%-12s %9s %14s %16s" % ("reference", "emprises", "AUC moyenne",
                             "ecart a 12 mois"))
log("-" * 56)
for mois in sorted(par):
    f = [l for l in par[mois]
         if PREV_MIN <= l["prevalence_pct"] <= PREV_MAX]
    if not f:
        log("%-12s %9d %14s %16s" % ("%d mois" % mois, len(par[mois]),
                                     "-", "-"))
        continue
    moy = float(np.mean([l["auc"] for l in f]))
    e = [l["auc"] - ref[l["zone"]] for l in f if l["zone"] in ref]
    if mois == 12:
        ecart = "reference"
    elif e:
        ecart = fr(float(np.mean(e)), 4, True)
    else:
        ecart = "-"
    log("%-12s %9d %14s %16s"
        % ("%d mois" % mois, len(f), fr(moy, 4), ecart))
log("")
log("Termine.")
