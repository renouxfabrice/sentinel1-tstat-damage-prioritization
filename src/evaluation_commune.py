# -*- coding: utf-8 -*-
r"""
===============================================================================
MODULE D'EVALUATION COMMUN
===============================================================================

Sert aux experiences 1 (echelles de lissage) et 2 (orientation du batiment),
et a toute evaluation ulterieure d'un raster de dommage contre une verite
terrain ponctuelle.

PROTOCOLE — identique a celui de l'evaluation multi-zones du 14 septembre 2026,
pour que tous les resultats du projet restent comparables entre eux :

  - les points de dommage EMS/UNOSAT sont des SIGNALEMENTS, sans classe
    « non endommage » ; ils sont accroches au batiment le plus proche dans un
    rayon de 20 m, et tout batiment non accroche de l'emprise est compte comme
    non endommage (correction du biais tautologique) ;
  - la statistique est lue sur la BOITE ENGLOBANTE du batiment : a 10 comme a
    20 m de resolution, la majorite des empreintes ne contient aucun centre de
    pixel, une statistique zonale stricte serait vide ;
  - le seuil est balaye exhaustivement, le kappa de Cohen servant de critere ;
  - l'AUC est calculee en parallele, car elle ne depend d'aucun seuil.

ORIENTATION DU BATIMENT (experience 2)
--------------------------------------
L'azimut de la trace au sol de Sentinel-1 se deduit de l'inclinaison de son
orbite (98,18 deg) et de la latitude :

    sin(azimut) = cos(inclinaison) / cos(latitude)

A la latitude de la Jamaique (18 deg N) cela donne une trace a 351,4 deg pour
une passe ascendante et 188,6 deg pour une descendante — soit une direction
quasi nord-sud. Le radar visant a droite, la direction de visee est
perpendiculaire : 81,4 et 278,6 deg, quasi est-ouest.

L'echo de double rebond sur le diedre mur-sol est maximal lorsque le mur est
PARALLELE a la trace, et s'effondre lorsqu'il est a 45 deg. On calcule donc,
pour chaque batiment, l'angle aigu entre son axe principal — grand cote du
rectangle englobant d'aire minimale — et la direction de la trace.
===============================================================================
"""
import csv
import math
import os

import numpy as np
from osgeo import gdal, ogr, osr
from shapely import wkb as shp_wkb

gdal.UseExceptions(); ogr.UseExceptions()

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

SNAP_M = 20.0
SEUILS = None          # defini a l'appel, depend de l'echelle des valeurs
INCLINAISON_S1 = 98.18


def azimut_trace_s1(latitude_deg, passe="ASCENDING"):
    """Azimut de la trace au sol de Sentinel-1, en degres depuis le nord."""
    r = math.cos(math.radians(INCLINAISON_S1)) / math.cos(math.radians(latitude_deg))
    r = max(-1.0, min(1.0, r))
    a = math.degrees(math.asin(r))          # negatif : la trace part vers le nord-ouest
    return (a % 360.0) if passe.upper().startswith("ASC") else ((180.0 - a) % 360.0)


def to_wgs84(lyr):
    s = lyr.GetSpatialRef()
    if s is None:
        return None
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return None if s.IsSame(WGS84) else osr.CoordinateTransformation(s, WGS84)


def lire_emprise(path):
    d = ogr.Open(path)
    if d is None:
        return None
    ly = d.GetLayer(); tr = to_wgs84(ly); u = None
    for f in ly:
        g = f.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        if not g.IsValid():
            g = g.MakeValid()
        u = g if u is None else u.Union(g)
    d = None
    return u


def lire_points(path, champ, positifs):
    d = ogr.Open(path); ly = d.GetLayer(); tr = to_wgs84(ly); out = []
    for f in ly:
        g = f.GetGeometryRef()
        if g is None or f.GetField(champ) not in positifs:
            continue
        p = g if g.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else g.Centroid()
        p = p.Clone()
        if tr is not None:
            p.Transform(tr)
        out.append((p.GetY(), p.GetX()))
    d = None
    return out


def orientation_batiment(geom_ogr, lat):
    """Azimut de l'axe principal du batiment, en degres depuis le nord,
    ramene dans [0, 180[ puisqu'un axe n'a pas de sens.

    Passe par le rectangle englobant d'aire minimale : plus robuste qu'une
    analyse en composantes principales sur les sommets, qui serait biaisee par
    une densite de sommets inegale le long du contour.
    """
    try:
        g = shp_wkb.loads(bytes(geom_ogr.ExportToWkb()))
        r = g.minimum_rotated_rectangle
        xs, ys = r.exterior.coords.xy
        if len(xs) < 4:
            return None
        k = math.cos(math.radians(lat))
        cotes = []
        for i in range(len(xs) - 1):
            dx = (xs[i + 1] - xs[i]) * k
            dy = (ys[i + 1] - ys[i])
            cotes.append((math.hypot(dx, dy), dx, dy))
        cotes.sort(reverse=True)
        _, dx, dy = cotes[0]
        return math.degrees(math.atan2(dx, dy)) % 180.0
    except Exception:
        return None


def ecart_angulaire(a, b):
    """Ecart aigu entre deux directions non orientees, dans [0, 90]."""
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)


def stats_batiments(source_path, raster_path, emprise_geom, avec_orientation=True):
    """Rend, pour les batiments dont le centroide est dans l'emprise :
    latitude, longitude, un dictionnaire {bande: valeurs}, le nombre de pixels
    lus et l'orientation de l'axe principal."""
    ds = gdal.Open(raster_path)
    gt = ds.GetGeoTransform(); nx, ny = ds.RasterXSize, ds.RasterYSize
    noms = []
    arrs = []
    for i in range(1, ds.RasterCount + 1):
        b = ds.GetRasterBand(i)
        d = b.GetDescription() or ("bande%d" % i)
        a = b.ReadAsArray().astype(np.float32)
        nd = b.GetNoDataValue()
        if nd is not None:
            a[np.isclose(a, nd)] = np.nan
        noms.append(d); arrs.append(a)
    ds = None

    e = emprise_geom.GetEnvelope()
    d = ogr.Open(source_path); ly = d.GetLayer(); tr = to_wgs84(ly)
    ly.SetSpatialFilterRect(e[0], e[2], e[1], e[3])

    lat, lon, npix, ori = [], [], [], []
    vals = {n: [] for n in noms}
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
        sous = [a[py0:py1 + 1, px0:px1 + 1] for a in arrs]
        v0 = sous[0][np.isfinite(sous[0])]
        if v0.size == 0:
            continue
        lat.append(c.GetY()); lon.append(c.GetX()); npix.append(int(v0.size))
        for n, s in zip(noms, sous):
            vv = s[np.isfinite(s)]
            vals[n].append(float(vv.mean()) if vv.size else np.nan)
        ori.append(orientation_batiment(g, c.GetY()) if avec_orientation else None)
    d = None
    return (np.array(lat), np.array(lon),
            {n: np.array(v, np.float32) for n, v in vals.items()},
            np.array(npix), np.array([o if o is not None else np.nan for o in ori],
                                     np.float32))


def accrocher(pts, lat, lon, snap_m=SNAP_M):
    y = np.zeros(len(lat), np.int8)
    if not pts:
        return y
    plat = np.array([p[0] for p in pts]); plon = np.array([p[1] for p in pts])
    # Une geometrie vide ou degeneree rend un centroide aberrant apres
    # reprojection : non pas l'infini, mais 1,8e308, que np.isfinite declare
    # fini. C'est la division par le pas du quadrillage qui deborde ensuite.
    # Le critere retenu est donc l'appartenance aux plages geographiques, qui
    # ne modifie rien pour des coordonnees valides.
    fini = (np.isfinite(plat) & np.isfinite(plon)
            & (np.abs(plat) <= 90.0) & (np.abs(plon) <= 180.0))
    if not fini.all():
        plat, plon = plat[fini], plon[fini]
        if plat.size == 0:
            return y
    pas = snap_m / 111320.0 * 1.5
    seau = {}
    for k in range(len(plat)):
        seau.setdefault((int(plon[k] / pas), int(plat[k] / pas)), []).append(k)
    for j in range(len(lat)):
        if not (-90.0 <= lat[j] <= 90.0 and -180.0 <= lon[j] <= 180.0):
            continue
        bx, by = int(lon[j] / pas), int(lat[j] / pas)
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand.extend(seau.get((bx + dx, by + dy), []))
        if not cand:
            continue
        c = np.array(cand)
        dl = (plat[c] - lat[j]) * 110574.0
        dn = (plon[c] - lon[j]) * 111320.0 * math.cos(math.radians(lat[j]))
        if np.min(dl * dl + dn * dn) <= snap_m * snap_m:
            y[j] = 1
    return y


def metriques(y, pred):
    tp = int(np.sum((y == 1) & (pred == 1))); fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0))); tn = int(np.sum((y == 0) & (pred == 0)))
    n = tp + fp + fn + tn
    if n == 0:
        return None
    po = (tp + tn) / n; pp = (tp + fp) / n; pt = (tp + fn) / n
    pe = pp * pt + (1 - pp) * (1 - pt)
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, n=n,
                precision=tp / (tp + fp) if tp + fp else float('nan'),
                recall=tp / (tp + fn) if tp + fn else float('nan'),
                kappa=(po - pe) / (1 - pe) if pe < 1 else float('nan'))


def auc(y, v):
    ok = np.isfinite(v); yy, vv = y[ok], v[ok]
    npos, nneg = int((yy == 1).sum()), int((yy == 0).sum())
    if npos == 0 or nneg == 0:
        return float('nan')
    o = np.argsort(vv, kind='mergesort'); tri = vv[o]
    r = np.empty(len(vv), np.float64); i = 0
    while i < len(tri):
        j = i
        while j + 1 < len(tri) and tri[j + 1] == tri[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return (r[yy == 1].sum() - npos * (npos + 1) / 2.0) / (npos * nneg)


def meilleur_seuil(y, v, seuils):
    ok = np.isfinite(v)
    if not ok.any():
        return None
    best = None
    for s in seuils:
        pred = np.zeros(len(y), np.int8); pred[ok] = (v[ok] >= s).astype(np.int8)
        m = metriques(y, pred)
        if m and m['kappa'] == m['kappa'] and (best is None or m['kappa'] > best['kappa']):
            best = dict(seuil=float(s), **m)
    return best


def ecrire_csv(chemin, lignes):
    if not lignes:
        return
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    cles = sorted({k for l in lignes for k in l})
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cles, delimiter=";")
        wr.writeheader(); wr.writerows(lignes)


def meilleur_seuil_youden(y, v, retourner_courbe=False):
    """Seuil maximisant l'indice de Youden J = Se + Sp - 1.

    Contrairement a `meilleur_seuil`, qui optimise le kappa, cet indice ne
    depend pas de la prevalence : il permet de comparer des zones ou des
    emprises dont la proportion de batiments touches differe.

    Rend un dictionnaire (seuil, youden, sensibilite, specificite, tp/fp/fn/tn)
    ou None si la mesure est impossible. Avec `retourner_courbe`, ajoute les
    tableaux de sensibilite et de specificite pour tracer la courbe ROC.
    """
    ok = np.isfinite(v)
    yy = np.asarray(y)[ok].astype(np.int8)
    vv = np.asarray(v)[ok].astype(np.float64)
    npos = int((yy == 1).sum()); nneg = int((yy == 0).sum())
    if npos == 0 or nneg == 0:
        return None

    # Tri decroissant : on fait descendre le seuil, les elements passent
    # positifs un a un. Les sommes cumulees donnent alors directement, pour
    # chaque seuil candidat, le nombre de vrais et de faux positifs.
    o = np.argsort(-vv, kind="mergesort")
    vs = vv[o]; ys = yy[o]
    tp = np.cumsum(ys == 1).astype(np.float64)
    fp = np.cumsum(ys == 0).astype(np.float64)
    # On ne retient qu'un point par valeur distincte, sinon un seuil couperait
    # au milieu d'un paquet d'ex aequo, ce qui n'est pas realisable.
    dernier = np.r_[vs[1:] != vs[:-1], True]
    tp = tp[dernier]; fp = fp[dernier]; seuils = vs[dernier]

    se = tp / npos
    sp = 1.0 - fp / nneg
    j = se + sp - 1.0
    k = int(np.argmax(j))

    r = dict(seuil=float(seuils[k]), youden=float(j[k]),
             sensibilite=float(se[k]), specificite=float(sp[k]),
             tp=int(tp[k]), fp=int(fp[k]),
             fn=int(npos - tp[k]), tn=int(nneg - fp[k]),
             n=int(npos + nneg), prevalence=float(npos) / (npos + nneg))
    if retourner_courbe:
        r["courbe_seuils"] = seuils
        r["courbe_sensibilite"] = se
        r["courbe_specificite"] = sp
    return r
