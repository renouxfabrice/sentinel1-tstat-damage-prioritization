# -*- coding: utf-8 -*-
"""Classement des produits de dommage sur l'emprise strictement commune, en aire sous la courbe par commune contre deux vérités de référence, avec trois lectures : l'emprise commune aux produits à large couverture, le face-à-face par paire, et l'intersection stricte des douze produits.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import os
import sys

import numpy as np

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)
import evaluation_commune as ev            # noqa: E402

RES = os.path.join(RACINE, "resultats")

MIN_UNITE = 50        # batiments minimaux dans une unite pour qu'elle compte
MIN_N = 200           # batiments minimaux pour qu'une AUC soit rendue
MIN_POS = 20          # signalements minimaux pour qu'une AUC soit rendue

# la meilleure, au sens de l'AUC par commune.
COLONNE = {
    "notre T-stat": "tstat_raster_max",
    "BDPM (notre reproduction)": "bdpm_raster_max",
    "EOS-RS": "eos_raster_max",
    "OSU": "osu_coverage_fraction",
    "NASA DRCS S1": "nasa_s1_raster_max",
    "NASA DRCS S2": "nasa_s2_raster_max",
    "IMPACT Initiatives": "impact_rang",
    "UNGSC": "ungsc_raster_max",
    "Microsoft AI for Good": "microsoft_rang",
    "fAIr HOTOSM": "fair_cm_score",
    "DISHA": "disha_cm_score",
    "UH SAIL": "uhsail_rang",
}

# Les quatre colonnes ou un zero signale une absence de calcul.
ZERO_EST_ABSENCE = {"tstat_raster_max", "tstat_raster_mean",
                    "tstat_raster_p75", "tstat_raster_p90"}

# Sens de lecture : toutes ces colonnes croissent avec le dommage.

REFERENCE = "notre T-stat"


# ---------------------------------------------------------------------------
def centrer_par_unite(v, sel, unite):
    """Centrage-reduction a l'interieur de chaque unite administrative.

    Reprise a l'identique de l'experience 28, pour que les valeurs restent
    comparables a celles du classement.
    """
    out = np.full(len(v), np.nan, np.float64)
    ok = sel & np.isfinite(v) & (unite >= 0)
    if ok.sum() < MIN_UNITE:
        return out
    ordre = np.argsort(unite[ok], kind="mergesort")
    idx = np.flatnonzero(ok)[ordre]
    uu = unite[idx]
    bornes = np.flatnonzero(np.r_[True, uu[1:] != uu[:-1], True])
    for a, b in zip(bornes[:-1], bornes[1:]):
        if b - a < MIN_UNITE:
            continue
        sub = idx[a:b]
        x = v[sub]
        sd = x.std()
        out[sub] = (x - x.mean()) / sd if sd > 1e-12 else 0.0
    return out


def auc_par_commune(y, v, sel, unite):
    """AUC apres retrait de l'effet de commune. Rend NaN si l'echantillon est
    trop maigre pour que le chiffre veuille dire quelque chose."""
    vz = centrer_par_unite(v, sel, unite)
    s = np.isfinite(vz) & sel
    n, p = int(s.sum()), int(y[s].sum())
    if n < MIN_N or p < MIN_POS or p == n:
        return float("nan"), n, p
    a = ev.auc(y[s], vz[s])
    return a, n, p


def main():
    Z = np.load(os.path.join(RES, "exp27c_table_maitresse_v2.npz"), allow_pickle=True)
    U = np.load(os.path.join(RES, "exp27b_unites.npz"), allow_pickle=True)
    cols = list(Z["colonnes"]); V = Z["valeurs"]
    idx = {c: i for i, c in enumerate(cols)}

    adm3 = U["adm3"]
    codes = {a: i for i, a in enumerate(sorted(set(adm3)))}
    unite = np.array([codes.get(a, -1) for a in adm3], np.int32)

    def colonne(nom):
        return V[:, idx[COLONNE[nom]]]

    def present(nom):
        v = colonne(nom)
        m = np.isfinite(v)
        if COLONNE[nom] in ZERO_EST_ABSENCE:
            m &= (v != 0.0)
        return m

    VERITES = {}
    for nom, col in (("ems", "ems_damaged"), ("chatmap", "chatmap_damaged")):
        d = V[:, idx[col]]
        VERITES[nom] = (np.nan_to_num(d, nan=0.0) > 0, np.isfinite(d))

    presents = {n: present(n) for n in COLONNE}
    for n in sorted(COLONNE):
        print("  %-28s couvre %8d batiments" % (n, presents[n].sum()))

    # ---------------------------------------------------------- A. intersection
    # Deux intersections. Celle des douze produits est la plus stricte, mais
    # elle est reduite par les trois produits a toute petite emprise (DISHA,
    # EOS-RS, Microsoft) et se concentre sur le coeur sinistre. Celle des
    # produits couvrant au moins un cinquieme de la table donne un echantillon
    # bien plus large, au prix de trois produits en moins.
    larges = [n for n in COLONNE if presents[n].sum() >= 0.20 * V.shape[0]]

    lignes_a = []
    for etiquette, sous_ensemble in (("douze produits", list(COLONNE)),
                                     ("produits >= 20 %% de couverture", larges)):
        inter = np.ones(V.shape[0], bool)
        for n in sous_ensemble:
            inter &= presents[n]
        print("\nA. INTERSECTION — %s (%d produits) : %d batiments"
              % (etiquette, len(sous_ensemble), inter.sum()))
        bloc = []
        for nom in sous_ensemble:
            v = colonne(nom)
            l = dict(intersection=etiquette, n_produits=len(sous_ensemble),
                     produit=nom, colonne=COLONNE[nom],
                     n_intersection=int(inter.sum()))
            for verite, (y, examine) in VERITES.items():
                sel = inter & examine
                a, n, p = auc_par_commune(y, v, sel, unite)
                l["auc_%s" % verite] = round(a, 4) if a == a else ""
                l["n_%s" % verite] = n
                l["pos_%s" % verite] = p
                l["n_unites_%s" % verite] = int(len(set(
                    unite[sel & np.isfinite(centrer_par_unite(v, sel, unite))])))
            bloc.append(l)
        bloc.sort(key=lambda d: -(float(d["auc_ems"] or 0)
                                  + float(d["auc_chatmap"] or 0)))
        print("%-28s %11s %12s %9s %8s %8s"
              % ("produit", "vs Copern.", "vs ChatMap", "n", "pos EMS", "communes"))
        for d in bloc:
            print("%-28s %11s %12s %9d %8d %8d"
                  % (d["produit"], d["auc_ems"] or "-", d["auc_chatmap"] or "-",
                     d["n_ems"], d["pos_ems"], d["n_unites_ems"]))
        lignes_a += bloc
    ev.ecrire_csv(os.path.join(RES, "exp42_aoi_commun_intersection.csv"), lignes_a)

    # ------------------------------------------------------- B. face-a-face
    print("\nB. FACE-A-FACE AVEC %s, SUR L'EMPRISE COMMUNE A CHAQUE PAIRE\n"
          % REFERENCE.upper())
    ref = colonne(REFERENCE)
    lignes_b = []
    entete = ("%-28s %8s | %-19s | %-19s"
              % ("adversaire", "n commun", "vs Copernicus", "vs ChatMap"))
    print(entete)
    print("%-28s %8s | %8s %10s | %8s %10s"
          % ("", "", "T-stat", "adversaire", "T-stat", "adversaire"))
    for nom in COLONNE:
        if nom == REFERENCE:
            continue
        commun = presents[REFERENCE] & presents[nom]
        v = colonne(nom)
        l = dict(adversaire=nom, colonne=COLONNE[nom], n_commun=int(commun.sum()))
        aff = []
        for verite, (y, examine) in VERITES.items():
            sel = commun & examine
            a_ref, n, p = auc_par_commune(y, ref, sel, unite)
            a_adv, _, _ = auc_par_commune(y, v, sel, unite)
            l["auc_tstat_%s" % verite] = round(a_ref, 4) if a_ref == a_ref else ""
            l["auc_adversaire_%s" % verite] = round(a_adv, 4) if a_adv == a_adv else ""
            l["n_%s" % verite] = n
            l["pos_%s" % verite] = p
            if a_ref == a_ref and a_adv == a_adv:
                l["ecart_%s" % verite] = round(a_ref - a_adv, 4)
            aff += ["%8s" % l["auc_tstat_%s" % verite],
                    "%10s" % l["auc_adversaire_%s" % verite]]
        lignes_b.append(l)
        print("%-28s %8d | %s %s | %s %s"
              % (nom, l["n_commun"], aff[0], aff[1], aff[2], aff[3]))

    ev.ecrire_csv(os.path.join(RES, "exp42_aoi_commun_face_a_face.csv"), lignes_b)
    print("\necrits dans %s" % RES)


if __name__ == "__main__":
    main()
