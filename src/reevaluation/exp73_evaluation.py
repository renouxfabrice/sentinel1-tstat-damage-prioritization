# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 73 — EVALUATION DU SEISME VENEZUELIEN
===============================================================================

Les neuf configurations calculees sur les six emprises du Venezuela sont
evaluees ici avec EXACTEMENT la meme regle d'appariement que la Jamaique
reevaluee : un point qui tombe dans une empreinte lui est assigne ; sinon il va
a l'empreinte non deja prise la plus proche, mesuree au contour ; une empreinte
ne recoit qu'un seul point.

C'est tout l'objet de l'operation : rendre les deux campagnes comparables sur
ce point, apres avoir constate qu'elles ne l'etaient pas.

CE QUI RESTE DIFFERENT, ET QU'IL FAUT ECRIRE
--------------------------------------------
La couche d'empreintes. La Jamaique est evaluee sur OSM et Open Buildings, le
Venezuela sur Overture. Aligner la regle d'appariement ne supprime pas cette
difference-la.

Et une difference qui joue en faveur du Venezuela : 3 052 points de dommages
pour 288 374 empreintes, la ou plusieurs zones jamaicaines comptaient PLUS de
points que de batiments. La prevalence y sera donc bien plus faible, et l'AUC
bien plus interpretable.
===============================================================================
"""
import datetime
import os
import sys
import time

import numpy as np
from osgeo import ogr, osr

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import DONNEES, TRAVAUX, REEVALUATION  # noqa: E402,F401
BASE, ETUDE = REEVALUATION, TRAVAUX
import evaluation_commune as ev
import appariement as ap

ogr.UseExceptions()

D = os.path.join(DONNEES, r"VENEZUELA\EMS\EMSR884_products\EMSR884_ALL")
AOI_GPKG = os.path.join(D, "EMSR884_areOfinterestA_v3.gpkg")
BATIS = os.path.join(D, "EMSR884_Building_Overture.gpkg")
POINTS = os.path.join(D, "EMSR884_builtUpP.gpkg")
RASTERS = os.path.join(BASE, "cartes_venezuela")
OUT = os.path.join(BASE, "resultats")

CHAMP = "damage_gra"
POSITIFS = {"Destroyed", "Damaged", "Possibly damaged"}

VARIANTES = ['reference', 'welch', 'mahalanobis', 'sans_masque',
             'lissage_20m', 'orbites_stouffer',
             'ztest_1img', 'poole_1img', 'mahalanobis_1img']
COURTS = {'reference': "référence", 'welch': "Welch",
          'mahalanobis': "Mahalanobis", 'sans_masque': "sans masque",
          'lissage_20m': "lissage 20 m", 'orbites_stouffer': "Stouffer",
          'ztest_1img': "score z, 1 image", 'poole_1img': "regroupée, 1 image",
          'mahalanobis_1img': "Mahalanobis, 1 image"}

MIN_DOMMAGE = 20
N_SEUILS = 100
PREVALENCE_MIN, PREVALENCE_MAX = 5.0, 95.0

WGS84 = osr.SpatialReference(); WGS84.ImportFromEPSG(4326)
WGS84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)


def log(m):
    print(m); sys.stdout.flush()


def nb(x, n=4, signe=False):
    s = ("%+.*f" if signe else "%.*f") % (n, x)
    return s.replace(".", ",").replace("-", "\u2212")


def emprises():
    d = ogr.Open(AOI_GPKG); ly = d.GetLayer()
    s = ly.GetSpatialRef(); tr = None
    if s is not None:
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not s.IsSame(WGS84):
            tr = osr.CoordinateTransformation(s, WGS84)
    out = []
    for f in ly:
        g = f.GetGeometryRef()
        if g is None:
            continue
        g = g.Clone()
        if tr is not None:
            g.Transform(tr)
        out.append((str(f.GetField("area")).replace(" ", "_"), g))
    d = None
    return out


lignes, prevalences = [], []
t0 = time.time()
log("%-16s %10s %10s %10s %10s" % ("zone", "bâtiments", "points", "positifs",
                                   "prévalence"))
log("-" * 62)

for nom, emp in emprises():
    ref = os.path.join(RASTERS, "%s__reference.tif" % nom)
    if not os.path.exists(ref):
        log("  %-16s carte de reference absente" % nom); continue
    lat, lon, _v, geoms = ap.batiments_et_valeurs(BATIS, ref, emp)
    if len(lat) < 50:
        log("  %-16s %d batiments seulement" % (nom, len(lat))); continue

    pts = ap.lire_points(POINTS, CHAMP, POSITIFS, emp)
    j = {}
    y = ap.apparier(geoms, lat, lon, pts, journal=j)
    nd = int(y.sum())
    log("%-16s %10d %10d %10d %9.2f %%"
        % (nom, len(lat), len(pts), nd, 100.0 * nd / len(lat)))
    prevalences.append(dict(
        zone=nom, n_batiments=len(lat), n_points=len(pts), n_positifs=nd,
        prevalence=round(100.0 * nd / len(lat), 3),
        assignes_dedans=j.get("assignes_dedans", 0),
        assignes_hors=j.get("assignes_hors", 0),
        points_perdus=j.get("perdus", 0)))

    if nd < MIN_DOMMAGE:
        log("      moins de %d positifs, zone ecartee" % MIN_DOMMAGE); continue

    for var in VARIANTES:
        r = os.path.join(RASTERS, "%s__%s.tif" % (nom, var))
        if not os.path.exists(r):
            continue
        la2, lo2, vals, npix, _ = ev.stats_batiments(BATIS, r, emp,
                                                     avec_orientation=False)
        v2 = list(vals.values())[0]
        if len(la2) == len(lat) and np.allclose(la2, lat, atol=1e-9):
            v = v2
        else:
            index = {}
            for k in range(len(la2)):
                index[(round(float(la2[k]), 7), round(float(lo2[k]), 7))] = v2[k]
            v = np.full(len(lat), np.nan, np.float32)
            for k in range(len(lat)):
                v[k] = index.get((round(float(lat[k]), 7),
                                  round(float(lon[k]), 7)), np.nan)
        fini = v[np.isfinite(v)]
        if fini.size < 50:
            continue
        seuils = np.quantile(fini, np.linspace(0.01, 0.995, N_SEUILS))
        best = ev.meilleur_seuil(y, v, seuils)
        a = ev.auc(y, v)
        if best is None or not np.isfinite(a):
            continue
        lignes.append(dict(
            zone=nom, verite="EMS", source="overture", variante=var,
            n_batiments=len(lat), n_endommages=nd,
            prevalence=round(100.0 * nd / len(lat), 3),
            auc=round(a, 4), kappa_max=round(best['kappa'], 4),
            couverture_pct=round(100.0 * fini.size / len(lat), 2)))
        log("      %-20s AUC %.4f" % (var, a))

if not lignes:
    log("Aucune ligne produite."); raise SystemExit(1)

ev.ecrire_csv(os.path.join(OUT, "exp73_prevalences.csv"), prevalences)
ev.ecrire_csv(os.path.join(OUT, "exp73_detail.csv"), lignes)
log("\nDetail : exp73_detail.csv (%d lignes, %.0f s)" % (len(lignes), time.time() - t0))

par_cle = {}
for l in lignes:
    par_cle.setdefault(l['zone'], {})[l['variante']] = l

synth = []
for var in VARIANTES:
    if var == 'reference':
        continue
    d_auc, fiables, gagne = [], [], 0
    for cle, dd in par_cle.items():
        if 'reference' in dd and var in dd:
            da = dd[var]['auc'] - dd['reference']['auc']
            if not np.isfinite(da):
                continue
            d_auc.append(da)
            pv = dd['reference']['prevalence']
            if PREVALENCE_MIN <= pv <= PREVALENCE_MAX:
                fiables.append(da)
            if da > 0:
                gagne += 1
    if not d_auc:
        continue
    synth.append(dict(
        variante=var, n_zones=len(d_auc),
        delta_auc_moyen=round(float(np.mean(d_auc)), 4),
        delta_auc_median=round(float(np.median(d_auc)), 4),
        delta_auc_min=round(float(np.min(d_auc)), 4),
        delta_auc_max=round(float(np.max(d_auc)), 4),
        n_zones_fiables=len(fiables),
        delta_auc_fiables=round(float(np.mean(fiables)), 4) if fiables else '',
        zones_ou_la_variante_gagne=gagne))

ev.ecrire_csv(os.path.join(OUT, "exp73_synthese.csv"), synth)
log("\n%-22s %6s %11s %11s %9s %12s"
    % ("configuration", "zones", "dAUC moy", "dAUC med", "fiables", "dAUC fiab."))
for s in synth:
    log("%-22s %6d %11.4f %11.4f %9d %12s"
        % (COURTS.get(s['variante'], s['variante']), s['n_zones'],
           s['delta_auc_moyen'], s['delta_auc_median'],
           s['n_zones_fiables'], s['delta_auc_fiables']))

auj = datetime.date.today().strftime("%d %B %Y").replace("September", "septembre").replace("October", "octobre")

N = []
Q = N.append
Q("# Le séisme vénézuélien, mêmes configurations, même appariement")
Q("")
Q("*Note produite automatiquement par `exp73_evaluation.py` le %s.*" % auj)
Q("")
Q("## Ce qui est comparé")
Q("")
Q("Les neuf configurations déjà mesurées sur le cyclone jamaïcain, appliquées "
  "au séisme vénézuélien du 24 juin 2026, avec **la même règle d'appariement** "
  "des points de vérité aux empreintes bâties.")
Q("")
Q("Une différence subsiste et ne peut pas être supprimée : la Jamaïque est "
  "évaluée sur OpenStreetMap et Open Buildings, le Venezuela sur Overture.")
Q("")
Q("## L'échantillon")
Q("")
Q("| zone | bâtiments | points | positifs | prévalence |")
Q("|---|---|---|---|---|")
for p_ in prevalences:
    Q("| %s | %s | %s | %s | %s %% |"
      % (p_['zone'], p_['n_batiments'], p_['n_points'], p_['n_positifs'],
         nb(p_['prevalence'], 2)))
Q("")
Q("## Les résultats")
Q("")
Q("| configuration | écart moyen d'AUC | médiane | prévalence 5–95 % | l'emporte |")
Q("|---|---|---|---|---|")
for s in synth:
    f_ = (nb(s['delta_auc_fiables'], 4, True)
          if s['delta_auc_fiables'] != '' else "—")
    Q("| %s | **%s** | %s | %s | %d sur %d |"
      % (COURTS.get(s['variante'], s['variante']),
         nb(s['delta_auc_moyen'], 4, True), nb(s['delta_auc_median'], 4, True),
         f_, s['zones_ou_la_variante_gagne'], s['n_zones']))

with open(os.path.join(OUT, "NOTE_exp73.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(N) + "\n")
log("\nNote : NOTE_exp73.md")
log("Termine.")
