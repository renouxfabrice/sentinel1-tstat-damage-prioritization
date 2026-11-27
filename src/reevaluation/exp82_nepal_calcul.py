# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 73 — LES MEMES CONFIGURATIONS, SUR LE SEISME DU VENEZUELA
===============================================================================

POURQUOI

Tout ce qui a ete mesure jusqu'ici porte sur la Jamaique et le cyclone Melissa.
Un seul alea, un seul pays : rien ne garantit que les ecarts constates s'y
retrouvent ailleurs. Le seisme venezuelien du 24 juin 2026 est l'autre terrain
disponible, et il differe sur tout ce qui compte — alea, bati urbain dense au
lieu d'habitat diffus, autre geometrie d'acquisition, autre verite terrain.

LA DATE
-------
2026-06-24T16:04:00, celle de Copernicus EMS pour l'activation EMSR884. Ce
n'est PAS le 25 juin a minuit qu'employaient des experiences anterieures : ce
decalage avait ete identifie et corrige, et il fait choisir une mauvaise
premiere image.

LES DONNEES
-----------
    emprises   EMSR884_areOfinterestA_v3.gpkg, 6 zones
    empreintes EMSR884_Building_Overture.gpkg, 288 374 batiments
    verite     EMSR884_builtUpP.gpkg, 3 052 points
               (692 Destroyed, 828 Damaged, 1 532 Possibly damaged)

L'appariement des points aux empreintes emploie la MEME regle stricte que la
Jamaique reevaluee — module `appariement`. C'est tout l'objet de l'operation :
les deux campagnes deviennent comparables sur ce point.

Il reste une difference qu'on ne peut pas supprimer : la Jamaique est evaluee
sur OSM et Open Buildings, le Venezuela sur Overture. Il faut l'ecrire.
===============================================================================
"""
import csv
import os
import sys
import time
import types

if "geemap" not in sys.modules:
    sys.modules["geemap"] = types.ModuleType("geemap")

import ee
from osgeo import gdal, ogr, osr

gdal.UseExceptions(); ogr.UseExceptions()

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import DONNEES, TRAVAUX, REEVALUATION, MODULES_TSTAT  # noqa: E402,F401
BASE = REEVALUATION
from telechargement import telecharger

PROJET_GEE = "rapiddamagedetection"
MODULE = "pwtt_exp70.py"
D = os.path.join(TRAVAUX, "exp82_nepal")
# Chaque emprise de l'activation EMSR927 vit dans son propre geopackage.
AOI_GPKG = None
OUT = os.path.join(BASE, "cartes_nepal")
RES = os.path.join(BASE, "resultats")
os.makedirs(OUT, exist_ok=True)

# Lave torrentielle declenchee par une vidange de lac glaciaire.
DATE_EVENEMENT = "2026-08-26T00:00:00"
PRE_MOIS, POST_MOIS, ECHELLE_M = 12, 2, 10
JOURS_PAR_MOIS = 30.436875

LISSAGE_20M = dict(focal_radius=20, kernels=[50, 100, 150],
                   weights=[0.25, 0.25, 0.25, 0.25])

# Les six configurations multi-images, puis les trois formes a une image.
MULTI = {
    'outil': dict(ttest_type='pooled', method='max'),
}
UNE_IMAGE = {
    # La premiere image arrive a J+2,52 : c'est le cas reel sur cette
    # catastrophe, et celui qui interesse une cellule d'evaluation.
    'outil_1img': dict(ttest_type='pooled', method='max', valid_min_post=1),
}

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def log(m):
    print(m); sys.stdout.flush()


def emprises():
    """Une entree par emprise de l'activation EMSR927.

    Les produits de suivi remplacent les produits initiaux quand les deux
    existent : ils couvrent la meme emprise avec une interpretation plus
    complete.
    """
    import glob
    vus = {}
    for chemin in sorted(glob.glob(os.path.join(D, "*grading*.gpkg"))):
        base = os.path.basename(chemin)
        code = base.split("_")[3]            # aoi01, aoi02, ...
        suivi = "monitoring" in base
        if code in vus and not suivi:
            continue
        ds = ogr.Open(chemin)
        if ds is None:
            continue
        for k in range(ds.GetLayerCount()):
            ly = ds.GetLayer(k)
            if not ly.GetName().startswith("areaOfInterestA"):
                continue
            s = ly.GetSpatialRef(); tr = None
            if s is not None:
                s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                if not s.IsSame(WGS84):
                    tr = osr.CoordinateTransformation(s, WGS84)
            g = None
            for f in ly:
                gg = f.GetGeometryRef()
                if gg is None:
                    continue
                gg = gg.Clone()
                if tr is not None:
                    gg.Transform(tr)
                g = gg if g is None else g.Union(gg)
            if g is not None:
                e = g.GetEnvelope()      # xmin, xmax, ymin, ymax
                vus[code] = ("NEPAL_" + code, [e[0], e[2], e[1], e[3]])
        ds = None
    return [vus[k] for k in sorted(vus)]



ee.Initialize(project=PROJET_GEE)
import importlib.util
spec = importlib.util.spec_from_file_location("pwtt", os.path.join(MODULES_TSTAT, MODULE))
pwtt = importlib.util.module_from_spec(spec); spec.loader.exec_module(pwtt)
log("Module %s charge. Evenement : %s" % (MODULE, DATE_EVENEMENT))

EV_MS = ee.Date(DATE_EVENEMENT).millis().getInfo()


def premier_delai(aoi):
    col = (ee.ImageCollection("COPERNICUS/S1_GRD")
           .filterBounds(aoi)
           .filter(ee.Filter.eq("instrumentMode", "IW"))
           .filterDate(ee.Date(DATE_EVENEMENT),
                       ee.Date(DATE_EVENEMENT).advance(2, "month")))
    ms = col.aggregate_array("system:time_start").getInfo()
    return (min(ms) - EV_MS) / 86400000.0 if ms else None


cibles = emprises()
log("%d emprises : %s\n" % (len(cibles), ", ".join(n for n, _ in cibles)))

journal = []
for nom, b in cibles:
    aoi = ee.Geometry.Rectangle(b)
    delai = premier_delai(aoi)
    if delai is None:
        log("  %-16s aucune acquisition posterieure" % nom); continue
    fin_1img = delai + 0.5
    log("%-16s 1re image J%+.2f  (%.3f x %.3f deg)"
        % (nom, delai, b[2] - b[0], b[3] - b[1]))

    plans = [(e, s, POST_MOIS, 2) for e, s in MULTI.items()]
    plans += [(e, s, fin_1img / JOURS_PAR_MOIS, 1) for e, s in UNE_IMAGE.items()]

    for etiquette, surcharge, post, vmin in plans:
        dest = os.path.join(OUT, "%s__%s.tif" % (nom, etiquette))
        if os.path.exists(dest) and os.path.getsize(dest) > 5000:
            continue
        t0 = time.time()
        sur = dict(surcharge)
        pwtt.VALID_MIN_POST = sur.pop("valid_min_post", vmin)
        try:
            # Le module analyse les chaines au format « AAAA-MM-JJ » et bute
            # sur l'heure. On lui passe donc des objets ee.Date, comme le
            # faisait deja exp23 pour la meme raison.
            kw = dict(aoi=aoi, inference_start=ee.Date(DATE_EVENEMENT),
                      war_start=ee.Date(DATE_EVENEMENT), pre_interval=PRE_MOIS,
                      post_interval=post, viz=False, export=False, clip=True)
            kw.update(sur)
            img = pwtt.detect_damage(**kw)
            octets, requetes = telecharger(img.select("T_statistic"), b,
                                           dest, ECHELLE_M)
            log("    %-18s %5.1f Mo %5.0f s%s"
                % (etiquette, octets / 1e6, time.time() - t0,
                   "  (%d morceaux)" % requetes if requetes > 1 else ""))
            journal.append(dict(zone=nom, variante=etiquette, statut="ok",
                                valid_min_post=pwtt.VALID_MIN_POST,
                                octets=octets, morceaux=requetes,
                                secondes=round(time.time() - t0)))
        except Exception as exc:
            log("    %-18s ECHEC : %s" % (etiquette, str(exc)[:100]))
            journal.append(dict(zone=nom, variante=etiquette, statut="echec",
                                valid_min_post=pwtt.VALID_MIN_POST, octets=0,
                                secondes=round(time.time() - t0),
                                erreur=str(exc)[:250]))
        finally:
            pwtt.VALID_MIN_POST = 2

if journal:
    f = os.path.join(RES, "journal_exp73.csv")
    cles = sorted({k for l in journal for k in l})
    with open(f, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        wr.writeheader(); wr.writerows(journal)
    ok = sum(1 for l in journal if l["statut"] == "ok")
    log("\nJournal : %s" % f)
    log("%d calculs reussis, %d echecs." % (ok, len(journal) - ok))
log("Termine.")
