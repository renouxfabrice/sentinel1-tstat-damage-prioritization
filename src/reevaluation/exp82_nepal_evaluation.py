# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 82 — LE T-STAT VOIT-IL LES PONTS ET LES ROUTES EMPORTES ?
===============================================================================

LA CATASTROPHE

Lave torrentielle des 26-27 aout 2026 dans les districts de Rasuwa et Nuwakot,
au Nepal, declenchee par une vidange brutale de lac glaciaire. Activation
Copernicus EMSR927. Premiere image Sentinel-1 a J+2,52.

CE QUE CETTE EXPERIENCE APPORTE DE NEUF

Jusqu'ici, toutes les evaluations du memoire portaient sur des BATIMENTS, et
leurs negatifs etaient deduits : un batiment non signale etait suppose intact,
ce qui confond « intact » et « non regarde ».

Ici, deux couches portent des NEGATIFS DECLARES :

  - les routes de Copernicus (`transportationL`), ou l'analyste a note
    explicitement « No visible damage » ;
  - les ponts de HOT, ou chaque ouvrage recoit « Standing » ou « Destroyed ».

C'est la premiere fois qu'une aire sous la courbe se calcule sur des negatifs
affirmes, et sur de l'infrastructure lineaire.

COMMENT UN OBJET LINEAIRE EST NOTE

Le greffon decoupe chaque ligne selon la grille de pixels du raster. On fait de
meme : on echantillonne le T-stat le long de l'objet et on retient le MAXIMUM,
puisque la statistique combine deja ses quatre vues par un maximum et qu'un pont
emporte sur une partie de sa longueur reste un pont emporte.
===============================================================================
"""
import glob
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import DONNEES, TRAVAUX, REEVALUATION  # noqa: E402,F401
BASE, ETUDE = REEVALUATION, TRAVAUX
import evaluation_commune as ev

from osgeo import gdal, ogr, osr
gdal.UseExceptions(); ogr.UseExceptions()

CARTES = os.path.join(BASE, "cartes_nepal")
# Les deux configurations comparees : la serie complete, et la premiere
# image seule — celle qui arrive a J+2,52.
CONFIGS = [("série complète", "outil"), ("une seule image", "outil_1img")]
# Les deux manieres de resumer les pixels d'un objet lineaire.
MANIERES = ["moyenne", "p75", "p90", "maximum"]
EMS = os.path.join(TRAVAUX, "exp82_nepal")
RES = os.path.join(BASE, "resultats")

# Les classes qui valent « endommage ». « No visible damage » est le negatif
# declare ; « Not Analysed » n'est ni l'un ni l'autre et sort de l'echantillon.
POSITIFS = {"Destroyed", "Damaged", "Possibly damaged", "Washed out"}
NEGATIFS = {"No visible damage", "Intact", "Standing"}
HORS = {"Not Analysed"}

PAS_M = 10.0          # pas d'echantillonnage le long d'une ligne, en metres
PREV_MIN, PREV_MAX = 5.0, 95.0

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def log(m):
    print(m); sys.stdout.flush()


def fr(x, n=4, signe=False):
    if x is None or not np.isfinite(x):
        return "—"
    s = ("%+.*f" if signe else "%.*f") % (n, float(x))
    return s.replace(".", ",").replace("-", "\u2212")


class Raster(object):
    """Lecture d'un raster en coordonnees geographiques."""

    def __init__(self, chemin):
        self.d = gdal.Open(chemin)
        self.gt = self.d.GetGeoTransform()
        self.b = self.d.GetRasterBand(1)
        self.nodata = self.b.GetNoDataValue()
        self.a = self.b.ReadAsArray().astype(np.float32)
        if self.nodata is not None:
            self.a[self.a == self.nodata] = np.nan
        self.ny, self.nx = self.a.shape
        s = osr.SpatialReference(wkt=self.d.GetProjection())
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        self.tr = None if s.IsSame(WGS84) else \
            osr.CoordinateTransformation(WGS84, s)

    def valeur(self, lon, lat):
        x, y = (lon, lat)
        if self.tr is not None:
            x, y, _ = self.tr.TransformPoint(lon, lat)
        c = int((x - self.gt[0]) / self.gt[1])
        l = int((y - self.gt[3]) / self.gt[5])
        if 0 <= l < self.ny and 0 <= c < self.nx:
            v = self.a[l, c]
            return None if not np.isfinite(v) else float(v)
        return None


def points_le_long(geom, pas_deg):
    """Echantillonne une geometrie : un point tous les `pas_deg` degres."""
    out = []
    t = geom.GetGeometryType()
    if t in (ogr.wkbPoint, ogr.wkbPoint25D):
        return [(geom.GetX(), geom.GetY())]
    if geom.GetGeometryCount() > 0 and t not in (ogr.wkbLineString,
                                                 ogr.wkbLineString25D):
        for i in range(geom.GetGeometryCount()):
            out += points_le_long(geom.GetGeometryRef(i), pas_deg)
        return out
    n = geom.GetPointCount()
    if n == 0:
        return out
    for i in range(n - 1):
        x1, y1 = geom.GetX(i), geom.GetY(i)
        x2, y2 = geom.GetX(i + 1), geom.GetY(i + 1)
        d = math.hypot(x2 - x1, y2 - y1)
        k = max(1, int(d / pas_deg))
        for j in range(k + 1):
            f = j / float(k)
            out.append((x1 + f * (x2 - x1), y1 + f * (y2 - y1)))
    return out


def note(geom, raster, pas_deg, maniere="moyenne"):
    """Resume le T-stat le long de l'objet.

    « moyenne » suit le greffon, qui prend la moyenne du T-stat sur un batiment
    ou un pont et qui, sur une route, donne a chaque troncon la valeur de son
    pixel. « maximum » repere un ouvrage emporte sur une partie seulement de sa
    longueur. Rend None si l'objet n'est couvert par aucun pixel valide.
    """
    vals = [raster.valeur(x, y) for x, y in points_le_long(geom, pas_deg)]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    if maniere == "maximum":
        return max(vals)
    if maniere == "moyenne":
        return sum(vals) / float(len(vals))
    if maniere == "p75":
        return float(np.percentile(vals, 75))
    if maniere == "p90":
        return float(np.percentile(vals, 90))
    raise ValueError("agregation inconnue : %s" % maniere)


def classe(v):
    if v in POSITIFS:
        return 1
    if v in NEGATIFS:
        return 0
    return None


def evaluer(nom_objet, couples):
    """couples : liste de (y, score). Rend la ligne de resultat."""
    y = np.array([c[0] for c in couples], np.int8)
    v = np.array([c[1] for c in couples], np.float32)
    n, nd = len(y), int(y.sum())
    prev = 100.0 * nd / n if n else float("nan")
    a = ev.auc(y, v) if 0 < nd < n else float("nan")
    return dict(objet=nom_objet, n=n, n_endommages=nd,
                prevalence_pct=round(prev, 2),
                auc=round(float(a), 4) if np.isfinite(a) else "",
                fiable="oui" if PREV_MIN <= prev <= PREV_MAX else "non")


# ─────────────────────────────────────────────────────────────────────────────
lignes = []
log("%-20s %-8s %-16s %-9s %6s %10s %9s"
    % ("emprise", "objet", "configuration", "résumé", "objets",
       "prévalence", "AUC"))
log("-" * 90)

for chemin in sorted(glob.glob(os.path.join(EMS, "*grading*.gpkg"))):
    base = os.path.basename(chemin)
    code = base.split("_")[3]
    suivi = "monitoring" in base
    cartes_ici = [(lib, os.path.join(CARTES, "NEPAL_%s__%s.tif" % (code, suf)))
                  for lib, suf in CONFIGS]
    cartes_ici = [(lib, p) for lib, p in cartes_ici if os.path.exists(p)]
    if not cartes_ici:
        continue
    # Le produit de suivi prime sur le produit initial.
    autre = base.replace("initial", "monitoring1")
    if not suivi and os.path.exists(os.path.join(EMS, autre)):
        continue

    pas_deg = PAS_M / 111320.0

    d = ogr.Open(chemin)
    for i in range(d.GetLayerCount()):
        ly = d.GetLayer(i)
        n_ly = ly.GetName()
        if not (n_ly.startswith("transportationL")
                or n_ly.startswith("transportationP")):
            continue
        s = ly.GetSpatialRef(); tr = None
        if s is not None:
            s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            if not s.IsSame(WGS84):
                tr = osr.CoordinateTransformation(s, WGS84)
        objet = "routes" if n_ly.startswith("transportationL") else "ponts"
        for lib, chemin_carte in cartes_ici:
          r = Raster(chemin_carte)
          for maniere in MANIERES:
            couples = []
            ly.ResetReading()
            for f in ly:
                c = classe(f.GetField("damage_gra"))
                if c is None:
                    continue
                g = f.GetGeometryRef()
                if g is None:
                    continue
                g = g.Clone()
                if tr is not None:
                    g.Transform(tr)
                v = note(g, r, pas_deg, maniere)
                if v is not None:
                    couples.append((c, v))
            if len(couples) < 10:
                continue
            res = evaluer(objet, couples)
            res["emprise"] = "NEPAL_" + code
            res["configuration"] = lib
            res["agregation"] = maniere
            res["source"] = "Copernicus EMSR927"
            lignes.append(res)
            log("%-20s %-8s %-16s %-9s %6d %8.1f %% %9s"
                % (res["emprise"], objet, lib, maniere, res["n"],
                   res["prevalence_pct"], fr(res["auc"] or float("nan"))))
    d = None

# ─────────────────────────────────────────────────────────────────────────────
# Les ponts de HOT, qui portent leurs propres negatifs.
# ─────────────────────────────────────────────────────────────────────────────
log("")
for nom, fichier in (("ponts HOT, aire",
                      "hot_aire__Bridges_(OSM)_GeoJSON.geojson"),
                     ("ponts HOT, corridor",
                      "hot_corridor__Bridges_(OSM)_GeoJSON.geojson"),
                     ("ponts HOT, évaluation",
                      "hot_aire__Bridge_Damage_Assessment_GeoJSON.geojson")):
    chemin = os.path.join(EMS, fichier)
    if not os.path.exists(chemin):
        continue
    d = ogr.Open(chemin)
    if d is None:
        continue
    ly = d.GetLayer()
    s = ly.GetSpatialRef(); tr = None
    if s is not None:
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not s.IsSame(WGS84):
            tr = osr.CoordinateTransformation(s, WGS84)

    # Chaque pont est note sur la carte de l'emprise qui le contient.
    for lib, suf in CONFIGS:
     for maniere in MANIERES:
      rasters = {}
      for c in ("aoi01", "aoi02", "aoi03", "aoi05"):
        p = os.path.join(CARTES, "NEPAL_%s__%s.tif" % (c, suf))
        if os.path.exists(p):
            rasters[c] = Raster(p)

      couples = []
      ly.ResetReading()
      for f in ly:
        c = classe(f.GetField("status"))
        if c is None:
            continue
        g = f.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        meilleur = None
        for r in rasters.values():
            v = note(g, r, PAS_M / 111320.0, maniere)
            if v is not None and (meilleur is None or v > meilleur):
                meilleur = v
        if meilleur is not None:
            couples.append((c, meilleur))
      if len(couples) < 10:
        continue
      res = evaluer(nom, couples)
      res["emprise"] = "ensemble"
      res["configuration"] = lib
      res["agregation"] = maniere
      res["source"] = "HOT"
      lignes.append(res)
      log("%-20s %-8s %-16s %-9s %6d %8.1f %% %9s"
          % ("ensemble", nom[10:18], lib, maniere, res["n"],
             res["prevalence_pct"], fr(res["auc"] or float("nan"))))
    d = None

if lignes:
    ev.ecrire_csv(os.path.join(RES, "exp82_nepal.csv"), lignes)
    log("\nÉcrit : exp82_nepal.csv (%d lignes)" % len(lignes))
log("\nTerminé.")
