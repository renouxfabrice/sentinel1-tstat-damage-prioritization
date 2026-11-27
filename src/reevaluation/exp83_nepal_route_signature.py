# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 83 — TROUVER LA ROUTE NEPALAISE A LA SIGNATURE RADAR LA PLUS NETTE
===============================================================================

POURQUOI

La figure 2.6 du memoire rapproche deux batiments detruits par deux aleas
differents, et montre que la retrodiffusion peut baisser ou monter. Il s'agit
d'y ajouter un troisieme cas : une ROUTE emportee par la lave torrentielle
nepalaise, troisieme mode de destruction.

Pour que le panneau vaille quelque chose, il faut choisir le segment ou l'ecart
entre la moyenne anterieure et la moyenne posterieure est le plus marque — et
le choisir sur une mesure, non a l'oeil.

CE QUE FAIT CE PROGRAMME

Pour chaque segment note « Destroyed » par Copernicus dans l'activation
EMSR927, il calcule la retrodiffusion VV moyenne avant et apres l'evenement,
trace orbitale par trace orbitale, et classe les segments par amplitude de
l'ecart en decibels.

Il ne produit aucune figure : il designe le cas a illustrer.
===============================================================================
"""
import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ee
from osgeo import ogr, osr
ogr.UseExceptions()

ee.Initialize(project="rapiddamagedetection")

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
from config import TRAVAUX  # noqa: E402

EMS = os.path.join(TRAVAUX, "exp82_nepal")
EVENEMENT = ee.Date("2026-08-26T00:00:00")
PRE_MOIS = 12
POST_JOURS = 30
RAYON_M = 25          # le segment est echantillonne dans un disque de 25 m

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def log(m):
    print(m); sys.stdout.flush()


# ── les segments detruits, et leur point median ─────────────────────────────
points = []
for chemin in sorted(glob.glob(os.path.join(EMS, "*grading*.gpkg"))):
    base = os.path.basename(chemin)
    code = base.split("_")[3]
    autre = base.replace("initial", "monitoring1")
    if "monitoring" not in base and os.path.exists(os.path.join(EMS, autre)):
        continue
    d = ogr.Open(chemin)
    for i in range(d.GetLayerCount()):
        ly = d.GetLayer(i)
        if not ly.GetName().startswith("transportationL"):
            continue
        s = ly.GetSpatialRef(); tr = None
        if s is not None:
            s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            if not s.IsSame(WGS84):
                tr = osr.CoordinateTransformation(s, WGS84)
        for f in ly:
            if f.GetField("damage_gra") != "Destroyed":
                continue
            g = f.GetGeometryRef()
            if g is None:
                continue
            g = g.Clone()
            if tr is not None:
                g.Transform(tr)
            c = g.Centroid()
            points.append(ee.Feature(
                ee.Geometry.Point([c.GetX(), c.GetY()]).buffer(RAYON_M),
                {"emprise": code, "id": len(points)}))
    d = None

log("%d segments détruits à examiner." % len(points))
if not points:
    sys.exit("aucun segment")

fc = ee.FeatureCollection(points)

s1 = (ee.ImageCollection("COPERNICUS/S1_GRD")
      .filterBounds(fc.geometry())
      .filter(ee.Filter.eq("instrumentMode", "IW"))
      .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
      .select("VV"))

traces = s1.filterDate(EVENEMENT, EVENEMENT.advance(POST_JOURS, "day")) \
           .aggregate_array("relativeOrbitNumber_start").distinct().getInfo()
log("traces orbitales disponibles : %s" % traces)

resultats = {}
for tr in traces:
    c = s1.filter(ee.Filter.eq("relativeOrbitNumber_start", tr))
    avant = c.filterDate(EVENEMENT.advance(-PRE_MOIS, "month"), EVENEMENT)
    apres = c.filterDate(EVENEMENT, EVENEMENT.advance(POST_JOURS, "day"))
    n_av, n_ap = avant.size().getInfo(), apres.size().getInfo()
    if n_av < 5 or n_ap < 1:
        log("   trace %-4s écartée (%d avant, %d après)" % (tr, n_av, n_ap))
        continue
    img = (avant.mean().rename("avant")
           .addBands(apres.mean().rename("apres"))
           .addBands(avant.reduce(ee.Reducer.stdDev()).rename("ecart_type")))
    stats = img.reduceRegions(collection=fc, reducer=ee.Reducer.mean(),
                              scale=10).getInfo()
    for f in stats["features"]:
        p = f["properties"]
        av, ap = p.get("avant"), p.get("apres")
        if av is None or ap is None:
            continue
        resultats.setdefault(p["id"], []).append(
            dict(trace=tr, emprise=p["emprise"], avant=av, apres=ap,
                 ecart=ap - av, sigma=p.get("ecart_type") or float("nan")))
    log("   trace %-4s : %d avant, %d après, %d segments mesurés"
        % (tr, n_av, n_ap, len(stats["features"])))

# ── le classement ───────────────────────────────────────────────────────────
meilleurs = []
for sid, lignes in resultats.items():
    best = max(lignes, key=lambda x: abs(x["ecart"]))
    meilleurs.append((sid, best))
meilleurs.sort(key=lambda x: -abs(x[1]["ecart"]))

log("\n%-6s %-9s %-7s %9s %9s %9s %8s"
    % ("id", "emprise", "trace", "avant dB", "après dB", "écart dB", "σ avant"))
log("-" * 66)
for sid, b in meilleurs[:14]:
    log("%-6d %-9s %-7s %9.2f %9.2f %+9.2f %8.2f"
        % (sid, b["emprise"], b["trace"], b["avant"], b["apres"],
           b["ecart"], b["sigma"]))

if meilleurs:
    sid, b = meilleurs[0]
    g = points[sid].geometry().centroid(1).coordinates().getInfo()
    log("\nLe cas le plus marqué : segment %d, emprise %s, trace %s"
        % (sid, b["emprise"], b["trace"]))
    log("   %+.2f dB  (%.2f → %.2f), écart-type antérieur %.2f dB"
        % (b["ecart"], b["avant"], b["apres"], b["sigma"]))
    log("   position : %.5f, %.5f  (longitude, latitude)" % (g[0], g[1]))
