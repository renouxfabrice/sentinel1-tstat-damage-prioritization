# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 79 — LE TABLEAU DE L'ANNEXE L, REFAIT
===============================================================================

POURQUOI

Le tableau L.1 du memoire oppose la variance regroupee au test de Welch sur
quinze comparaisons. Il repose sur l'evaluation du 15 septembre : deux couches
baties melangees en Jamaique — dont OpenStreetMap, ou plusieurs emprises
comptent moins de batiments que Copernicus n'a signale de dommages — et un
appariement des points aux empreintes par accrochage a vingt metres du
centroide, sans interdiction de doublon.

Les deux defauts ont ete corriges depuis, et la mesure doit l'etre aussi.

CE QUE FAIT CE PROGRAMME

Il reconstruit le tableau a partir des deux evaluations refaites : la Jamaique
sur Open Buildings seule (exp75) et le Venezuela sur Overture (exp73), toutes
deux avec la regle d'appariement stricte. Il ne calcule aucune carte : tout
existe deja.

Le sens de l'ecart est conserve — « variance regroupee moins Welch » — pour
qu'un ecart positif signifie, comme dans le memoire, que la forme employee
classe mieux.
===============================================================================
"""
import csv
import io
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import REEVALUATION  # noqa: E402
BASE = REEVALUATION
RES = os.path.join(BASE, "resultats")

NOMS = {
    "EMS_AOI16": "Big Woods (AOI16)", "EMS_AOI29": "Bartons (AOI29)",
    "EMS_AOI30": "Darliston (AOI30)", "EMS_AOI36": "Orange Bay (AOI36)",
    "EMS_AOI38": "Belmont (AOI38)", "EMS_AOI39": "White House (AOI39)",
    "UNOSAT_WhiteHouse": "White House (UNOSAT)",
    "UNOSAT_BlackRiver": "Black River (UNOSAT)",
    "UNOSAT_BlackRiverVillage": "Black River Village (UNOSAT)",
    "Caracas": "Caracas (AOI02)", "Moron": "Morón (AOI06)",
    "San_Felipe": "San Felipe (AOI08)", "la_guaira": "La Guaira (AOI12)",
    "catia_la_mar": "Catia La Mar (AOI12)", "caraballeda": "Caraballeda (AOI12)",
}
PREV_MIN, PREV_MAX = 5.0, 95.0


def lire(nom, col_variante):
    chemin = os.path.join(RES, nom)
    if not os.path.exists(chemin):
        sys.exit("absent : %s" % chemin)
    with io.open(chemin, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";")), col_variante


def collecter(lignes, col, campagne):
    """Apparie, pour chaque emprise, la reference et la variante Welch."""
    par_zone = {}
    for l in lignes:
        par_zone.setdefault(l["zone"], {})[l[col]] = l
    out = []
    for zone, d in sorted(par_zone.items()):
        if "reference" not in d or "welch" not in d:
            continue
        ref, wel = d["reference"], d["welch"]
        try:
            a_ref, a_wel = float(ref["auc"]), float(wel["auc"])
            prev = float(ref["prevalence"])
        except (TypeError, ValueError):
            continue
        if not (np.isfinite(a_ref) and np.isfinite(a_wel)):
            continue
        out.append(dict(
            campagne=campagne, zone=zone, emprise=NOMS.get(zone, zone),
            n_batiments=int(float(ref["n_batiments"])),
            n_endommages=int(float(ref["n_endommages"])),
            prevalence_pct=round(prev, 2),
            auc_regroupee=round(a_ref, 4), auc_welch=round(a_wel, 4),
            ecart=round(a_ref - a_wel, 4),
            fiable="oui" if PREV_MIN <= prev <= PREV_MAX else "non"))
    return out


jam, _ = lire("exp75_detail.csv", "famille")
ven, _ = lire("exp73_detail.csv", "variante")

lignes = (collecter(jam, "famille", "Jamaïque — cyclone Melissa")
          + collecter(ven, "variante", "Venezuela — séisme du 24 juin 2026"))

if not lignes:
    sys.exit("aucune comparaison appariée")

dest = os.path.join(RES, "exp79_annexe_L.csv")
with io.open(dest, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(lignes[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(lignes)

print("%-34s %9s %7s %10s %8s %9s" % ("emprise", "bâtiments", "prév.",
                                      "regroupée", "Welch", "écart"))
print("-" * 82)
campagne = None
for l in lignes:
    if l["campagne"] != campagne:
        campagne = l["campagne"]; print("\n%s" % campagne)
    print("%-34s %9d %6.2f %% %10.4f %8.4f %+9.4f%s"
          % (l["emprise"], l["n_batiments"], l["prevalence_pct"],
             l["auc_regroupee"], l["auc_welch"], l["ecart"],
             "" if l["fiable"] == "oui" else "   (écartée)"))

fiables = [l for l in lignes if l["fiable"] == "oui"]
e = np.array([l["ecart"] for l in fiables], float)
gagne = int((e > 0).sum())
print("\n%d comparaisons, dont %d exploitables." % (len(lignes), len(fiables)))
print("Sur les exploitables : écart moyen %+.4f, médian %+.4f, "
      "la variance regroupée l'emporte dans %d cas sur %d."
      % (e.mean(), float(np.median(e)), gagne, len(e)))
print("\nÉcrit : %s" % dest)
