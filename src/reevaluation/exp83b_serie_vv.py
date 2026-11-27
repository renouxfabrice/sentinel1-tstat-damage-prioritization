# -*- coding: utf-8 -*-
r"""
===============================================================================
LA SERIE TEMPORELLE VV DE LA ROUTE EMPORTEE — BIDUR, NEPAL
===============================================================================

Le segment retenu par l'experience 83 : emprise AOI03 (Bidur), trace orbitale
85, position 85,16374 / 27,95575. La retrodiffusion y passe de −4,04 dB a
−14,27 dB, soit 4,6 fois l'ecart-type de la periode anterieure.

Ce programme extrait la serie complete — une valeur par acquisition — pour que
la figure puisse montrer, comme les deux autres panneaux du memoire, la bande
d'un ecart-type autour de la moyenne anterieure et le trait de la moyenne
posterieure.

On mesure dans un disque de vingt-cinq metres autour du point : c'est l'ordre
de grandeur d'un troncon routier sur une grille de dix metres, et cela evite de
faire reposer la courbe sur un seul pixel.
===============================================================================
"""
import csv
import datetime
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ee

ee.Initialize(project="rapiddamagedetection")

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
from config import TRAVAUX, REEVALUATION  # noqa: E402,F401
RES = os.path.join(REEVALUATION, "resultats")

LON, LAT = 85.16374, 27.95575
TRACE = 85
RAYON_M = 25
EVENEMENT = ee.Date("2026-08-26T00:00:00")
PRE_MOIS, POST_JOURS = 12, 60

zone = ee.Geometry.Point([LON, LAT]).buffer(RAYON_M)

s1 = (ee.ImageCollection("COPERNICUS/S1_GRD")
      .filterBounds(zone)
      .filter(ee.Filter.eq("instrumentMode", "IW"))
      .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
      .filter(ee.Filter.eq("relativeOrbitNumber_start", TRACE))
      .filterDate(EVENEMENT.advance(-PRE_MOIS, "month"),
                  EVENEMENT.advance(POST_JOURS, "day"))
      .select("VV")
      .sort("system:time_start"))


def mesurer(img):
    v = img.reduceRegion(ee.Reducer.mean(), zone, 10).get("VV")
    return ee.Feature(None, {"t": img.date().millis(), "vv": v})


mesures = s1.map(mesurer).getInfo()["features"]
t0 = datetime.datetime(2026, 8, 26)

lignes = []
for f in mesures:
    p = f["properties"]
    if p.get("vv") is None:
        continue
    d = datetime.datetime.utcfromtimestamp(p["t"] / 1000.0)
    lignes.append(dict(
        date=d.strftime("%Y-%m-%d"),
        jours=round((d - t0).total_seconds() / 86400.0, 2),
        vv_db=round(float(p["vv"]), 3),
        periode="après" if d >= t0 else "avant"))

if not lignes:
    sys.exit("aucune mesure")

dest = os.path.join(RES, "exp83_serie_vv_bidur.csv")
with io.open(dest, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(lignes[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(lignes)

avant = [l["vv_db"] for l in lignes if l["periode"] == "avant"]
apres = [l["vv_db"] for l in lignes if l["periode"] == "après"]
moy_av = sum(avant) / len(avant)
sigma = (sum((x - moy_av) ** 2 for x in avant) / (len(avant) - 1)) ** 0.5
moy_ap = sum(apres) / len(apres)

print("%d acquisitions : %d avant, %d après" % (len(lignes), len(avant),
                                                len(apres)))
print("moyenne antérieure : %.2f dB, écart-type %.2f dB" % (moy_av, sigma))
print("moyenne postérieure : %.2f dB" % moy_ap)
print("écart : %+.2f dB, soit %.1f écarts-types"
      % (moy_ap - moy_av, abs(moy_ap - moy_av) / sigma))
print("\nÉcrit : %s" % dest)
