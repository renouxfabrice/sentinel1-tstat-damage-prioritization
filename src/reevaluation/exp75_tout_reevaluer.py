# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 75 — TOUT REEVALUER D'UN SEUL TENANT
===============================================================================

POURQUOI

Vingt-sept familles de cartes ont ete calculees sur la Jamaique, et seules neuf
ont ete evaluees avec la regle d'appariement stricte, sur la couche Open
Buildings. Les balayages de fenetre et de periode de reference reposent encore
sur l'ancienne regle — accrochage a 20 m du centroide, sans interdiction de
doublon — et sur les deux couches baties melangees.

Laisser coexister deux methodes d'evaluation interdit de comparer leurs
resultats entre eux. Ce programme les refait toutes, une fois, de la meme
facon.

CE QU'IL FAIT

Pour chaque zone, il etablit UNE SEULE FOIS la liste des batiments et la verite
terrain — c'est l'etape couteuse — puis il evalue toutes les cartes presentes,
quelle que soit leur famille. Cela divise le temps de calcul par le nombre de
familles.

Les familles sont deduites des noms de fichiers, donc ajouter une experience ne
demande aucune modification ici.

LA CONVENTION, RAPPELEE
    couche batie     Open Buildings  (OpenStreetMap est ecarte : plusieurs
                     zones y comptent moins de batiments que Copernicus n'a
                     signale de dommages)
    appariement      regle stricte du module `appariement`
    fiabilite        prevalence entre 5 et 95 %, bornee des DEUX cotes
===============================================================================
"""
import datetime
import glob
import os
import re
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import DONNEES, TRAVAUX, REEVALUATION  # noqa: E402,F401
BASE, ETUDE = REEVALUATION, TRAVAUX
import evaluation_commune as ev
import appariement as ap

W = os.path.join(DONNEES, r"JAMAIQUE\_etude_p95")
RASTERS = os.path.join(BASE, "cartes")
OUT = os.path.join(BASE, "resultats")
SOURCE = os.path.join(DONNEES, r"JAMAIQUE\AOI\Open_Building_AOI_t_test.gpkg")

EMS_AOIS = {
    'AOI16': 'EMSR847_AOI16_GRA_MONIT02_v1', 'AOI29': 'EMSR847_AOI29_GRA_MONIT01_v1',
    'AOI30': 'EMSR847_AOI30_GRA_MONIT01_v1', 'AOI36': 'EMSR847_AOI36_GRA_PRODUCT_v1',
    'AOI38': 'EMSR847_AOI38_GRA_PRODUCT_v1', 'AOI39': 'EMSR847_AOI39_GRA_PRODUCT_v1',
}
U = os.path.join(W, "unosat", "TC20251028JAM_SHP")
UNOSAT = {
    'WhiteHouse': ('AP_20251031_AnalysisExtent_WhiteHouse.shp',
                   'AP_20251031_Damagedbuilding_WhiteHouse.shp'),
    'BlackRiver': ('WV2_20251029_AnalysisExtent_BlackRiver.shp',
                   'WV2_20251029_Damagedbuilding_BlackRiver.shp'),
    'BlackRiverVillage': ('WV2_20251029_AnalysisExtent_BlackRiverVillage.shp',
                          'WV2_20251029_DamagedBuildings_BlackRiverVillage.shp'),
}
MIN_DOMMAGE = 20
N_SEUILS = 100
PREVALENCE_MIN, PREVALENCE_MAX = 5.0, 95.0

# A quelle experience chaque famille appartient, et quelle est sa reference.
GROUPES = [
    ("configurations", "exp75a",
     ['reference', 'welch', 'mahalanobis', 'sans_masque', 'lissage_20m',
      'orbites_stouffer', 'ztest_1img', 'poole_1img', 'mahalanobis_1img'],
     'reference'),
    ("fenetre posterieure, toutes orbites", "exp75b",
     ['fenetre_1img', 'fenetre_07j', 'fenetre_14j', 'fenetre_21j',
      'fenetre_30j', 'fenetre_60j'], 'fenetre_1img'),
    ("fenetre posterieure, orbite 150", "exp75c",
     ['orb150_1img', 'orb150_07j', 'orb150_14j', 'orb150_21j',
      'orb150_30j', 'orb150_60j'], 'orb150_1img'),
    ("periode de reference", "exp75d",
     ['pre_03m', 'pre_06m', 'pre_09m', 'pre_12m', 'pre_18m', 'pre_24m'],
     'pre_12m'),
]


def log(m):
    print(m); sys.stdout.flush()


def nb(x, n=4, signe=False):
    s = ("%+.*f" if signe else "%.*f") % (n, x)
    return s.replace(".", ",").replace("-", "\u2212")


zones = []
for nom, dossier in sorted(EMS_AOIS.items()):
    a = glob.glob(os.path.join(W, "emsr", dossier, "*areaOfInterestA*.shp"))
    p = glob.glob(os.path.join(W, "emsr", dossier, "*builtUpP*.shp"))
    if a and p:
        zones.append(dict(zone="EMS_" + nom, verite="EMS", emprise=a[0], points=p[0],
                          champ="damage_gra",
                          positifs={'Damaged', 'Possibly damaged', 'Destroyed'}))
for nom, (e, p) in sorted(UNOSAT.items()):
    zones.append(dict(zone="UNOSAT_" + nom, verite="UNOSAT",
                      emprise=os.path.join(U, e), points=os.path.join(U, p),
                      champ="Main_Damag", positifs={1, 13}))

toutes = set()
for _n, _e, familles, _r in GROUPES:
    toutes |= set(familles)

lignes = []
t0 = time.time()
log("%-26s %9s %8s %9s %11s" % ("zone", "bâtiments", "points", "positifs",
                                "prévalence"))
log("-" * 68)

for z in zones:
    emp = ev.lire_emprise(z['emprise'])
    if emp is None:
        continue
    ancre = os.path.join(RASTERS, "%s__reference.tif" % z['zone'])
    if not os.path.exists(ancre):
        continue
    lat, lon, _v, geoms = ap.batiments_et_valeurs(SOURCE, ancre, emp)
    if len(lat) < 50:
        continue
    pts = ap.lire_points(z['points'], z['champ'], z['positifs'], emp)
    y = ap.apparier(geoms, lat, lon, pts)
    nd = int(y.sum())
    prev = 100.0 * nd / len(lat)
    log("%-26s %9d %8d %9d %10.2f %%" % (z['zone'], len(lat), len(pts), nd, prev))
    if nd < MIN_DOMMAGE or prev >= 100.0:
        log("      ecartee (prevalence %.1f %%)" % prev)
        continue

    for famille in sorted(toutes):
        r = os.path.join(RASTERS, "%s__%s.tif" % (z['zone'], famille))
        if not os.path.exists(r):
            continue
        la2, lo2, vals, npix, _ = ev.stats_batiments(SOURCE, r, emp,
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
            zone=z['zone'], verite=z['verite'], source="open_buildings",
            famille=famille, n_batiments=len(lat), n_endommages=nd,
            prevalence=round(prev, 3), auc=round(a, 4),
            kappa_max=round(best['kappa'], 4),
            couverture_pct=round(100.0 * fini.size / len(lat), 2)))

if not lignes:
    log("Aucune ligne produite."); raise SystemExit(1)

ev.ecrire_csv(os.path.join(OUT, "exp75_detail.csv"), lignes)
log("\nDetail : exp75_detail.csv (%d lignes, %.0f s)" % (len(lignes), time.time() - t0))

par_zone = {}
for l in lignes:
    par_zone.setdefault(l['zone'], {})[l['famille']] = l

auj = datetime.date.today().strftime("%d %B %Y")
for a_, b_ in {"September": "septembre", "October": "octobre"}.items():
    auj = auj.replace(a_, b_)

N = []
Q = N.append
Q("# Toutes les expériences jamaïcaines, réévaluées d'un seul tenant")
Q("")
Q("*Note produite automatiquement par `exp75_tout_reevaluer.py` le %s.*" % auj)
Q("")
Q("## La convention, pour toutes les mesures qui suivent")
Q("")
Q("- couche bâtie : **Open Buildings** — OpenStreetMap est écarté, plusieurs "
  "zones y comptant moins de bâtiments que Copernicus n'a signalé de dommages ;")
Q("- appariement : la **règle stricte** — point dans l'empreinte, sinon la plus "
  "proche non déjà prise mesurée au contour, une empreinte ne recevant qu'un "
  "seul point ;")
Q("- fiabilité : les comparaisons dont la prévalence sort de l'intervalle "
  "**5–95 %** sont écartées, des deux côtés.")
Q("")

for titre_, etiquette, familles, ref in GROUPES:
    dispo = [f for f in familles if any(f in d for d in par_zone.values())]
    if ref not in dispo:
        continue
    synth = []
    for f in dispo:
        if f == ref:
            continue
        ec, fi, gagne = [], [], 0
        for zn, d in par_zone.items():
            if ref in d and f in d:
                da = d[f]['auc'] - d[ref]['auc']
                if not np.isfinite(da):
                    continue
                ec.append(da)
                if PREVALENCE_MIN <= d[ref]['prevalence'] <= PREVALENCE_MAX:
                    fi.append(da)
                if da > 0:
                    gagne += 1
        if not ec:
            continue
        synth.append(dict(groupe=etiquette, famille=f, reference=ref,
                          n_zones=len(ec),
                          delta_auc_moyen=round(float(np.mean(ec)), 4),
                          delta_auc_median=round(float(np.median(ec)), 4),
                          n_fiables=len(fi),
                          delta_auc_fiables=round(float(np.mean(fi)), 4) if fi else '',
                          zones_gagnantes=gagne))
    if not synth:
        continue
    ev.ecrire_csv(os.path.join(OUT, "%s_synthese.csv" % etiquette), synth)
    log("\n--- %s (référence : %s) ---" % (titre_, ref))
    log("%-20s %6s %11s %9s %12s" % ("famille", "zones", "dAUC moy", "fiables",
                                     "dAUC fiab."))
    for s in synth:
        log("%-20s %6d %11.4f %9d %12s"
            % (s['famille'], s['n_zones'], s['delta_auc_moyen'],
               s['n_fiables'], s['delta_auc_fiables']))

    Q("## %s" % titre_.capitalize())
    Q("")
    Q("Référence : `%s`." % ref)
    Q("")
    Q("| variante | zones | écart moyen d'AUC | dont fiables | l'emporte |")
    Q("|---|---|---|---|---|")
    for s in synth:
        f_ = (nb(s['delta_auc_fiables'], 4, True)
              if s['delta_auc_fiables'] != '' else "—")
        Q("| `%s` | %d | **%s** | %s | %d sur %d |"
          % (s['famille'], s['n_zones'], nb(s['delta_auc_moyen'], 4, True),
             f_, s['zones_gagnantes'], s['n_zones']))
    Q("")

with open(os.path.join(OUT, "NOTE_exp75.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(N) + "\n")
log("\nNote : NOTE_exp75.md")
log("Termine.")
