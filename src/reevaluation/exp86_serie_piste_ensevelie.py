# -*- coding: utf-8 -*-
r"""
===============================================================================
LA SERIE TEMPORELLE DE LA PISTE ENSEVELIE — LE CONTRE-EXEMPLE
===============================================================================

Ce troncon est note « Destroyed » par Copernicus, et l'imagerie optique ne
laisse aucun doute : en fevrier la piste serpente sous les arbres, en septembre
elle est sous une nappe de depots.

Le radar, lui, ne bouge presque pas. C'est precisement ce qui en fait un cas a
montrer : la destruction remplace un milieu rugueux — un couvert vegetal — par
un autre milieu rugueux — du sediment nu. Les deux renvoient autant l'un que
l'autre, et le critere de Rayleigh ne separe rien.

On extrait donc la serie complete, pour que la planche puisse opposer ce cas
plat a la chute de dix decibels du pont.
===============================================================================
"""
import csv
import datetime
import glob
import io
import math
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ee
from osgeo import ogr, osr
ogr.UseExceptions()
ee.Initialize(project="rapiddamagedetection")

EMS = os.path.join(TRAVAUX, "exp82_nepal")
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
from config import TRAVAUX, REEVALUATION  # noqa: E402,F401
RES = os.path.join(REEVALUATION, "resultats")
INDEX, TRACE, RAYON_M = 272, 85, 25
PRE_MOIS, POST_JOURS = 12, 60
EVENEMENT = ee.Date("2026-08-26T00:00:00")

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
CLASSES = ("Destroyed", "Damaged", "Possibly damaged", "No visible damage")


def sommets(g):
    t = g.GetGeometryType()
    if g.GetGeometryCount() > 0 and t not in (ogr.wkbLineString,
                                              ogr.wkbLineString25D):
        out = []
        for i in range(g.GetGeometryCount()):
            out += sommets(g.GetGeometryRef(i))
        return out
    return [[(g.GetX(i), g.GetY(i)) for i in range(g.GetPointCount())]]


troncons = []
for chemin in sorted(glob.glob(os.path.join(EMS, "*grading*.gpkg"))):
    base = os.path.basename(chemin)
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
            if f.GetField("damage_gra") not in CLASSES:
                continue
            g = f.GetGeometryRef()
            if g is None:
                continue
            g = g.Clone()
            if tr is not None:
                g.Transform(tr)
            troncons.append((f.GetField("damage_gra"), g))
    d = None

classe, geom = troncons[INDEX]
pts = max([l for l in sommets(geom) if len(l) > 1], key=len)
print("tronçon %d — « %s » — %d sommets" % (INDEX, classe, len(pts)))

zone = ee.Geometry.MultiPoint([list(p) for p in pts]).buffer(RAYON_M)
s1 = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(zone)
      .filter(ee.Filter.eq("instrumentMode", "IW"))
      .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
      .filter(ee.Filter.eq("relativeOrbitNumber_start", TRACE))
      .filterDate(EVENEMENT.advance(-PRE_MOIS, "month"),
                  EVENEMENT.advance(POST_JOURS, "day"))
      .select("VV").sort("system:time_start"))


def mesurer(img):
    return ee.Feature(None, {"t": img.date().millis(),
                             "vv": img.reduceRegion(ee.Reducer.mean(), zone,
                                                    10).get("VV")})


t0 = datetime.datetime(2026, 8, 26)
lignes = []
for f in s1.map(mesurer).getInfo()["features"]:
    p = f["properties"]
    if p.get("vv") is None:
        continue
    d_ = datetime.datetime.utcfromtimestamp(p["t"] / 1000.0)
    lignes.append(dict(date=d_.strftime("%Y-%m-%d"),
                       jours=round((d_ - t0).total_seconds() / 86400.0, 2),
                       vv_db=round(float(p["vv"]), 3),
                       periode="après" if d_ >= t0 else "avant"))

dest = os.path.join(RES, "exp86_serie_vv_piste.csv")
with io.open(dest, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(lignes[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(lignes)

av = [l["vv_db"] for l in lignes if l["periode"] == "avant"]
ap = [l["vv_db"] for l in lignes if l["periode"] == "après"]
m_av = sum(av) / len(av)
sg = (sum((x - m_av) ** 2 for x in av) / (len(av) - 1)) ** 0.5
m_ap = sum(ap) / len(ap)
print("%d acquisitions : %d avant, %d après" % (len(lignes), len(av), len(ap)))
print("moyenne avant %.2f dB (σ %.2f) · après %.2f dB" % (m_av, sg, m_ap))
print("écart %+.2f dB, soit %.1f σ" % (m_ap - m_av, abs(m_ap - m_av) / sg))
print("\nÉcrit : %s" % dest)
