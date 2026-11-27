# -*- coding: utf-8 -*-
r"""Telecharger une image Earth Engine, en la coupant si la memoire manque.

POURQUOI CE MODULE

Earth Engine refuse une requete dont le calcul depasse sa limite de memoire, et
repond « User memory limit exceeded » sous un code HTTP 400. Cela s'est produit
sur EMS_AOI29 avec la distance de Mahalanobis, qui estime une matrice de
covariance par pixel — cinq reductions au lieu de deux pour un test t.

La parade est de demander l'image par morceaux et de les recoller. On ne decoupe
que si la requete entiere echoue, pour ne pas ralentir les cas qui passent.
"""
import io
import os
import time
import urllib.error
import urllib.request
import zipfile

import ee
from osgeo import gdal


PASSAGERES = ("503", "502", "504", "429", "service unavailable",
              "too many requests", "timed out", "connection reset")
REPRISES = 4


def _est_passagere(e):
    """Un refus temporaire du serveur, qu'il suffit de reessayer."""
    m = str(e).lower()
    if isinstance(e, urllib.error.HTTPError) and e.code in (429, 500, 502,
                                                            503, 504):
        return True
    return any(s in m for s in PASSAGERES)


def _un_morceau(img, boite, echelle):
    """Une requete, une image. Renvoie les octets du GeoTIFF.

    Les indisponibilites temporaires d'Earth Engine — 503 surtout, frequentes
    quand le projet est en mode restreint — sont reessayees. Sans cela, un seul
    morceau malchanceux fait echouer tout un decoupage et laisse des fragments
    orphelins derriere lui.
    """
    region = ee.Geometry.Rectangle(boite)
    derniere = None
    for essai in range(REPRISES):
        try:
            url = img.getDownloadURL({"scale": echelle, "region": region,
                                      "format": "GEO_TIFF", "crs": "EPSG:4326"})
            with urllib.request.urlopen(url, timeout=1800) as r:
                brut = r.read()
            if brut[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(brut))
                brut = z.read([n for n in z.namelist() if n.endswith(".tif")][0])
            return brut
        except Exception as e:
            derniere = e
            if not _est_passagere(e) or essai == REPRISES - 1:
                raise
            time.sleep(5 * (essai + 1))
    raise derniere


def telecharger(img, boite, dest, echelle, profondeur=0):
    """Telecharger l'image, en la coupant en quatre si la memoire manque.

    Renvoie (octets, nombre de requetes). On recommence jusqu'a trois niveaux de
    decoupe, soit soixante-quatre morceaux, puis on renonce. Les morceaux sont
    recolles par GDAL et effaces.
    """
    try:
        brut = _un_morceau(img, boite, echelle)
        open(dest, "wb").write(brut)
        return len(brut), (4 ** profondeur)
    except Exception as e:
        # Earth Engine refuse pour deux raisons distinctes, et le decoupage
        # resout les deux :
        #   - le CALCUL depasse sa limite de memoire. Le serveur repond alors
        #     un code HTTP 400 dont le corps porte « User memory limit
        #     exceeded » ;
        #   - l'IMAGE demandee depasse la taille maximale d'une requete, 50 Mo.
        #     Ce refus-la survient AVANT le telechargement, au moment de
        #     fabriquer l'adresse : ce n'est pas une erreur HTTP mais une
        #     ee.EEException, et il faut donc regarder le message de TOUTE
        #     exception, pas seulement celui d'une HTTPError.
        corps = str(e)
        if isinstance(e, urllib.error.HTTPError):
            try:
                corps += " " + e.read().decode("utf-8", "replace")
            except Exception:
                pass
        m = corps.lower()
        trop_gros = ("memory limit" in m or "request size" in m
                     or "must be less than or equal to" in m)
        if not (trop_gros and profondeur < 4):
            raise

    x0, y0, x1, y1 = boite
    xm, ym = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    quarts = [[x0, y0, xm, ym], [xm, y0, x1, ym],
              [x0, ym, xm, y1], [xm, ym, x1, y1]]
    morceaux, requetes = [], 0
    for i, q in enumerate(quarts):
        sous = dest.replace(".tif", "__q%d_%d.tif" % (profondeur, i))
        _o, r = telecharger(img, q, sous, echelle, profondeur + 1)
        morceaux.append(sous); requetes += r
    vrt = dest.replace(".tif", ".vrt")
    gdal.BuildVRT(vrt, morceaux)
    gdal.Translate(dest, vrt)
    for m in morceaux + [vrt]:
        try:
            os.remove(m)
        except OSError:
            pass
    return os.path.getsize(dest), requetes
