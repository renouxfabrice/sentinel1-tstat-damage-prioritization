# -*- coding: utf-8 -*-
r"""
===============================================================================
EXPERIENCE 74 — LES DEUX CAMPAGNES, COTE A COTE
===============================================================================

CE QUE CE PROGRAMME FAIT
------------------------
Il rapproche les deux evaluations — le cyclone jamaicain et le seisme
venezuelien — desormais conduites avec LA MEME regle d'appariement des points
de verite aux empreintes batimentaires. Rien n'est recalcule : les deux
fichiers de detail sont apparies configuration par configuration.

LA QUESTION A LAQUELLE IL REPOND
--------------------------------
« La methode reagit-elle de la meme facon a un cyclone et a un seisme ? »

Et la reponse observee est plus interessante qu'un oui ou un non : les deux
campagnes ne different pas par l'alea mais par le DELAI de leur premiere image.

    Jamaique     premiere acquisition a J+2,0
    Venezuela    premiere acquisition a J+0,76, et J+0,28 sur San Felipe

Or c'est precisement le seuil que les travaux anterieurs avaient identifie :
en dessous d'un jour, le score a image unique ne vaut guere mieux que le
hasard ; a deux jours, il rejoint la methode complete.

CE QU'IL FAUT ECRIRE, ET NE PAS ECRIRE
--------------------------------------
Les ECARTS entre configurations sont comparables d'une campagne a l'autre :
chacune est mesuree contre sa propre reference, sur son propre echantillon.

Les AUC ABSOLUES ne le sont pas : la Jamaique est evaluee sur OpenStreetMap et
Open Buildings, le Venezuela sur Overture, et les prevalences n'ont rien de
commun. Comparer 0,61 ici a 0,61 la-bas n'aurait aucun sens.
===============================================================================
"""
import csv
import datetime
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI); sys.path.insert(0, os.path.dirname(ICI))
from config import DONNEES, TRAVAUX, REEVALUATION  # noqa: E402,F401
BASE, ETUDE = REEVALUATION, TRAVAUX
import evaluation_commune as ev

RES = os.path.join(BASE, "resultats")
PREVALENCE_MIN, PREVALENCE_MAX = 5.0, 95.0

VARIANTES = ['welch', 'mahalanobis', 'sans_masque', 'lissage_20m',
             'orbites_stouffer', 'ztest_1img', 'poole_1img', 'mahalanobis_1img']
COURTS = {'welch': "test de Welch", 'mahalanobis': "distance de Mahalanobis",
          'sans_masque': "masque de validité levé",
          'lissage_20m': "médian focal 20 m",
          'orbites_stouffer': "combinaison de Stouffer",
          'ztest_1img': "score z, une seule image",
          'poole_1img': "variance regroupée, une seule image",
          'mahalanobis_1img': "Mahalanobis, une seule image"}

CAMPAGNES = [("Jamaïque", "cyclone Melissa", "J+2,0", "exp72_detail.csv"),
             ("Venezuela", "séisme du 24 juin", "J+0,76", "exp73_detail.csv")]


def log(m):
    print(m); sys.stdout.flush()


def nb(x, n=4, signe=False):
    s = ("%+.*f" if signe else "%.*f") % (n, x)
    return s.replace(".", ",").replace("-", "−")


def lire(nom):
    chemin = os.path.join(RES, nom)
    if not os.path.exists(chemin):
        log("manque : %s" % chemin); return None
    with open(chemin, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def ecarts(lignes, fiables_seulement):
    """Ecarts apparies a la reference, par (zone, couche)."""
    par = {}
    for l in lignes:
        cle = (l["zone"], l.get("source", "overture"))
        par.setdefault(cle, {})[l["variante"]] = l
    out = {}
    for var in VARIANTES:
        vals = []
        for cle, d in par.items():
            if "reference" not in d or var not in d:
                continue
            pv = float(d["reference"]["prevalence"])
            if fiables_seulement and not (PREVALENCE_MIN <= pv <= PREVALENCE_MAX):
                continue
            da = float(d[var]["auc"]) - float(d["reference"]["auc"])
            if np.isfinite(da):
                vals.append(da)
        if vals:
            out[var] = (float(np.mean(vals)), float(np.median(vals)), len(vals))
    return out


tables = {}
for nom, _alea, _delai, fichier in CAMPAGNES:
    lignes = lire(fichier)
    if lignes is None:
        continue
    tables[nom] = dict(tout=ecarts(lignes, False), fiable=ecarts(lignes, True))

if len(tables) < 2:
    log("Les deux campagnes ne sont pas disponibles."); raise SystemExit(1)

log("%-38s %22s %22s" % ("configuration", "Jamaïque (J+2,0)",
                         "Venezuela (J+0,76)"))
log("%-38s %10s %10s %10s %10s" % ("", "toutes", "fiables", "toutes", "fiables"))
log("-" * 86)
sortie = []
for var in VARIANTES:
    j_t = tables["Jamaïque"]["tout"].get(var)
    j_f = tables["Jamaïque"]["fiable"].get(var)
    v_t = tables["Venezuela"]["tout"].get(var)
    v_f = tables["Venezuela"]["fiable"].get(var)
    log("%-38s %10s %10s %10s %10s"
        % (COURTS[var],
           "%+.4f" % j_t[0] if j_t else "—", "%+.4f" % j_f[0] if j_f else "—",
           "%+.4f" % v_t[0] if v_t else "—", "%+.4f" % v_f[0] if v_f else "—"))
    sortie.append(dict(
        variante=var, libelle=COURTS[var],
        jamaique_moyen=round(j_t[0], 4) if j_t else '',
        jamaique_fiable=round(j_f[0], 4) if j_f else '',
        jamaique_n=j_t[2] if j_t else 0,
        venezuela_moyen=round(v_t[0], 4) if v_t else '',
        venezuela_fiable=round(v_f[0], 4) if v_f else '',
        venezuela_n=v_t[2] if v_t else 0))

ev.ecrire_csv(os.path.join(RES, "exp74_deux_campagnes.csv"), sortie)
log("\nEcrit : exp74_deux_campagnes.csv")

# ── la note ───────────────────────────────────────────────────────────────
auj = datetime.date.today().strftime("%d %B %Y")
for a_, b_ in {"September": "septembre", "October": "octobre"}.items():
    auj = auj.replace(a_, b_)

N = []
Q = N.append
Q("# Cyclone et séisme : la méthode réagit-elle de la même façon ?")
Q("")
Q("*Note produite automatiquement par `exp74_croisement_campagnes.py` le %s. "
  "Aucun calcul nouveau : les deux évaluations sont appariées.*" % auj)
Q("")
Q("## Ce qui est comparé")
Q("")
Q("Les mêmes configurations, mesurées sur deux campagnes, avec **la même règle "
  "d'appariement** des points de vérité aux empreintes bâties — ce qui n'était "
  "pas le cas auparavant.")
Q("")
Q("| campagne | aléa | première image |")
Q("|---|---|---|")
for nom, alea, delai, _f in CAMPAGNES:
    Q("| %s | %s | **%s** |" % (nom, alea, delai))
Q("")
Q("## Les écarts à la configuration de référence")
Q("")
Q("| configuration | Jamaïque | dont fiables | Venezuela | dont fiables |")
Q("|---|---|---|---|---|")
for s in sortie:
    Q("| %s | %s | %s | %s | %s |"
      % (s['libelle'],
         nb(s['jamaique_moyen'], 4, True) if s['jamaique_moyen'] != '' else "—",
         nb(s['jamaique_fiable'], 4, True) if s['jamaique_fiable'] != '' else "—",
         nb(s['venezuela_moyen'], 4, True) if s['venezuela_moyen'] != '' else "—",
         nb(s['venezuela_fiable'], 4, True) if s['venezuela_fiable'] != '' else "—"))
Q("")
Q("La colonne « fiables » ne retient que les comparaisons dont la prévalence "
  "tombe entre 5 et 95 %. Ailleurs, l'AUC est estimée sur trop peu de cas d'un "
  "côté ou de l'autre pour signifier quelque chose.")
Q("")
Q("## Ce que cela dit")
Q("")
Q("Les deux campagnes ne se distinguent pas par l'aléa mais par le **délai de "
  "leur première image**. En Jamaïque elle arrive à J+2,0, au Venezuela à "
  "J+0,76 — et les formes à une seule image, qui l'emportent dans le premier "
  "cas, s'effondrent dans le second.")
Q("")
Q("C'est exactement le seuil que les travaux antérieurs avaient identifié sans "
  "pouvoir le confirmer ailleurs : en dessous d'un jour, le score à image "
  "unique ne vaut guère mieux que le hasard ; à deux jours, il rejoint la "
  "méthode complète. Le résultat était appuyé sur une seule campagne ; il l'est "
  "désormais sur deux, avec deux aléas, deux pays et la même règle "
  "d'appariement.")
Q("")
Q("**La formulation juste n'est donc pas « la méthode réagit différemment au "
  "cyclone et au séisme ». C'est : la méthode réagit au délai, et les deux "
  "campagnes tombent de part et d'autre du seuil.**")
Q("")
Q("## Ce qu'il ne faut pas écrire")
Q("")
Q("Que les AUC d'une campagne se comparent à celles de l'autre. La Jamaïque "
  "est évaluée sur OpenStreetMap et Open Buildings, le Venezuela sur Overture, "
  "et les prévalences n'ont rien de commun — de 0,5 % à 100 % selon les zones. "
  "Seuls les **écarts à la référence interne de chaque campagne** sont "
  "comparables.")
Q("")
Q("La figure correspondante est produite par `../R/fig_exp74.R`.")

with open(os.path.join(RES, "NOTE_exp74.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(N) + "\n")
log("Note : NOTE_exp74.md")
log("Termine.")
