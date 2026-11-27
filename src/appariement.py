# -*- coding: utf-8 -*-
r"""Apparier des points de verite terrain a des empreintes batimentaires.

POURQUOI CE MODULE

Les deux campagnes n'employaient pas la meme regle, et celle de la Jamaique
etait la plus lache des deux :

    `evaluation_commune.accrocher` marque un batiment des qu'un point de
    dommage se trouve a moins de 20 m de son CENTROIDE. Rien n'empeche un
    meme point de marquer plusieurs batiments voisins.

En tissu dense, un signalement se propage donc a ses voisins, ce qui gonfle la
classe positive. C'est vraisemblablement ce qui produisait des prevalences de
93, 97 et 99 % sur des zones qui ne sont pas rasees.

LA REGLE RETENUE, APPLIQUEE AUX DEUX CAMPAGNES

Celle employee au Venezuela, plus stricte, et proche de celle de Risso et al.
(2024) dont elle corrige deux points :

  1. un point qui tombe DANS une empreinte lui est assigne ;
  2. sinon, il va a l'empreinte NON DEJA PRISE la plus proche, la distance
     etant mesuree AU CONTOUR et non au centroide ;
  3. la recherche part de 100 m et double jusqu'a 2 km, puis abandonne ;
  4. une empreinte ne recoit qu'UN SEUL point.

La regle 4 est la difference decisive : le nombre de batiments positifs ne peut
plus depasser le nombre de points, ce qui interdit la propagation.

CE QUE CE MODULE NE FAIT PAS

Il ne choisit pas la couche d'empreintes. La Jamaique est evaluee sur OSM et
Open Buildings, le Venezuela sur Overture : aligner la regle d'appariement ne
supprime pas cette difference-la, et il faut le dire.
"""
import math
import sys

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions(); ogr.UseExceptions()

RAYON_DEPART = 100.0      # metres
RAYON_MAX = 2000.0        # metres
WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def _to_wgs84(ly):
    s = ly.GetSpatialRef()
    if s is None:
        return None
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if s.IsSame(WGS84):
        return None
    return osr.CoordinateTransformation(s, WGS84)


def batiments_et_valeurs(source_path, raster_path, emprise_geom):
    """Meme filtrage que evaluation_commune.stats_batiments, mais rend AUSSI
    les geometries — indispensable pour mesurer une distance au contour.

    ATTENTION : cette fonction doit rester en phase avec stats_batiments. Les
    deux appliquent le meme filtre (centroide dans l'emprise, au moins un pixel
    fini sous l'empreinte) et rendent donc les batiments dans le MEME ordre.
    """
    ds = gdal.Open(raster_path)
    gt = ds.GetGeoTransform(); nx, ny = ds.RasterXSize, ds.RasterYSize
    b = ds.GetRasterBand(1)
    arr = b.ReadAsArray().astype(np.float32)
    nd = b.GetNoDataValue()
    if nd is not None:
        arr[np.isclose(arr, nd)] = np.nan
    ds = None

    e = emprise_geom.GetEnvelope()
    d = ogr.Open(source_path); ly = d.GetLayer(); tr = _to_wgs84(ly)
    ly.SetSpatialFilterRect(e[0], e[2], e[1], e[3])

    lat, lon, vals, geoms = [], [], [], []
    for f in ly:
        g = f.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        c = g.Centroid()
        if not emprise_geom.Contains(c):
            continue
        env = g.GetEnvelope()
        px0 = max(0, min(nx - 1, int((env[0] - gt[0]) / gt[1])))
        px1 = max(0, min(nx - 1, int((env[1] - gt[0]) / gt[1])))
        py0 = max(0, min(ny - 1, int((env[3] - gt[3]) / gt[5])))
        py1 = max(0, min(ny - 1, int((env[2] - gt[3]) / gt[5])))
        sous = arr[py0:py1 + 1, px0:px1 + 1]
        fini = sous[np.isfinite(sous)]
        if fini.size == 0:
            continue
        lat.append(c.GetY()); lon.append(c.GetX())
        vals.append(float(fini.mean()))
        geoms.append(g)
    d = None
    return np.array(lat), np.array(lon), np.array(vals, np.float32), geoms


def lire_points(chemin, champ, positifs, emprise_geom=None):
    """Lire les points de verite. Rend [(lat, lon), ...] pour les positifs."""
    d = ogr.Open(chemin)
    if d is None:
        return []
    ly = d.GetLayer(); tr = _to_wgs84(ly)
    if emprise_geom is not None:
        e = emprise_geom.GetEnvelope()
        ly.SetSpatialFilterRect(e[0], e[2], e[1], e[3])
    pts = []
    for f in ly:
        if champ is not None:
            try:
                v = f.GetField(champ)
            except Exception:
                continue
            if v not in positifs:
                continue
        g = f.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        c = g if g.GetGeometryType() == ogr.wkbPoint else g.Centroid()
        y, x = c.GetY(), c.GetX()
        if abs(y) <= 90.0 and abs(x) <= 180.0:
            pts.append((y, x))
    d = None
    return pts


def apparier(geoms, lat, lon, points, journal=None):
    """Appliquer la regle stricte. Rend y (0/1) aligne sur `geoms`.

    Le cout est maitrise par un quadrillage sur les centroides : on ne calcule
    la distance au contour que pour les batiments des cases voisines, et l'on
    elargit progressivement.
    """
    n = len(geoms)
    y = np.zeros(n, np.int8)
    if n == 0 or not points:
        return y

    pris = np.zeros(n, bool)
    # quadrillage de 200 m
    pas = 200.0 / 111320.0
    seau = {}
    for j in range(n):
        seau.setdefault((int(lon[j] / pas), int(lat[j] / pas)), []).append(j)

    def voisins(plat, plon, anneaux):
        bx, by = int(plon / pas), int(plat / pas)
        out = []
        for dx in range(-anneaux, anneaux + 1):
            for dy in range(-anneaux, anneaux + 1):
                out.extend(seau.get((bx + dx, by + dy), []))
        return out

    dedans = hors = perdus = 0
    for plat, plon in points:
        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint(plon, plat)

        # 1. le point tombe-t-il dans une empreinte libre ?
        choisi = None
        for j in voisins(plat, plon, 1):
            if pris[j]:
                continue
            if geoms[j].Contains(pt):
                choisi = j
                break
        if choisi is not None:
            pris[choisi] = True; y[choisi] = 1; dedans += 1
            continue

        # 2. sinon, la plus proche non prise, au contour, rayon croissant
        rayon = RAYON_DEPART
        m_par_deg = 111320.0 * math.cos(math.radians(plat))
        while rayon <= RAYON_MAX and choisi is None:
            anneaux = max(1, int(rayon / 200.0) + 1)
            meilleure, dmin = None, None
            for j in voisins(plat, plon, anneaux):
                if pris[j]:
                    continue
                dd = geoms[j].Distance(pt)          # en degres
                dm = dd * m_par_deg
                if dm <= rayon and (dmin is None or dm < dmin):
                    meilleure, dmin = j, dm
            if meilleure is not None:
                choisi = meilleure
            else:
                rayon *= 2
        if choisi is not None:
            pris[choisi] = True; y[choisi] = 1; hors += 1
        else:
            perdus += 1

    if journal is not None:
        journal.update(points_total=len(points), assignes_dedans=dedans,
                       assignes_hors=hors, perdus=perdus,
                       batiments=n, positifs=int(y.sum()))
    return y
