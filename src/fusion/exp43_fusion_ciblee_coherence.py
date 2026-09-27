# -*- coding: utf-8 -*-
"""Fusion à deux termes du T-stat d'intensité avec un produit de cohérence interférométrique, mesurée en aire sous la courbe par commune contre deux vérités de référence, sur l'emprise commune aux termes fusionnés.

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

MIN_UNITE = 50
MIN_N = 200
MIN_POS = 20

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
ZERO_EST_ABSENCE = {"tstat_raster_max", "tstat_raster_mean",
                    "tstat_raster_p75", "tstat_raster_p90"}

REF = "notre T-stat"
COHERENCE = ["OSU", "BDPM (notre reproduction)", "EOS-RS"]


def centrer_par_unite(v, sel, unite):
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


def auc_commune(y, v, sel, unite):
    vz = centrer_par_unite(v, sel, unite)
    s = np.isfinite(vz) & sel
    n, p = int(s.sum()), int(y[s].sum())
    if n < MIN_N or p < MIN_POS or p == n:
        return float("nan"), n, p
    return ev.auc(y[s], vz[s]), n, p


def rangs(v, masque):
    """Rang relatif dans [0, 1] a l'interieur du masque. NaN ailleurs."""
    out = np.full(len(v), np.nan, np.float64)
    idx = np.flatnonzero(masque & np.isfinite(v))
    if idx.size == 0:
        return out
    ordre = np.argsort(v[idx], kind="mergesort")
    r = np.empty(idx.size, np.float64)
    r[ordre] = np.arange(idx.size, dtype=np.float64)
    out[idx] = r / max(idx.size - 1, 1)
    return out


def main():
    Z = np.load(os.path.join(RES, "exp27c_table_maitresse_v2.npz"), allow_pickle=True)
    U = np.load(os.path.join(RES, "exp27b_unites.npz"), allow_pickle=True)
    cols = list(Z["colonnes"]); V = Z["valeurs"]; N = V.shape[0]
    ix = {c: i for i, c in enumerate(cols)}
    adm3 = U["adm3"]
    codes = {a: i for i, a in enumerate(sorted(set(adm3)))}
    unite = np.array([codes.get(a, -1) for a in adm3], np.int32)

    def col(n):
        return V[:, ix[COLONNE[n]]]

    def present(n):
        v = col(n); m = np.isfinite(v)
        if COLONNE[n] in ZERO_EST_ABSENCE:
            m &= (v != 0.0)
        return m

    pres = {n: present(n) for n in COLONNE}
    VERITES = {}
    for nom, c in (("ems", "ems_damaged"), ("chatmap", "chatmap_damaged")):
        d = V[:, ix[c]]
        VERITES[nom] = (np.nan_to_num(d, nan=0.0) > 0, np.isfinite(d))

    lignes = []

    def noter(etiquette, emprise, nom_score, v):
        l = dict(lecture=etiquette, score=nom_score, n_emprise=int(emprise.sum()))
        for verite, (y, examine) in VERITES.items():
            a, n, p = auc_commune(y, v, emprise & examine, unite)
            l["auc_%s" % verite] = round(a, 4) if a == a else ""
            l["n_%s" % verite] = n
            l["pos_%s" % verite] = p
        aucs = [float(l["auc_%s" % k]) for k in VERITES if l["auc_%s" % k] != ""]
        l["moyenne"] = round(sum(aucs) / len(aucs), 4) if len(aucs) == len(VERITES) else ""
        lignes.append(l)
        return l

    def fusionner(etiquette, emprise, membres):
        """Note chaque membre seul, puis les quatre modes de fusion."""
        R = {n: rangs(col(n), emprise) for n in membres}
        for n in membres:
            noter(etiquette, emprise, "%s seul" % n, col(n))

        # poids : (AUC - 0,5) mesuree sur l'AUTRE verite, donc un jeu par verite
        poids = {}
        for verite in VERITES:
            autre = "chatmap" if verite == "ems" else "ems"
            y2, ex2 = VERITES[autre]
            p = {}
            for n in membres:
                a, _, _ = auc_commune(y2, col(n), emprise & ex2, unite)
                p[n] = max(a - 0.5, 0.0) if a == a else 0.0
            if sum(p.values()) <= 0:
                p = {n: 1.0 for n in membres}
            poids[verite] = p

        M = np.vstack([R[n] for n in membres])
        dispo = np.isfinite(M)
        n_disp = dispo.sum(axis=0)
        util = n_disp > 0
        Mz = np.where(dispo, M, np.nan)

        for mode in ("moyenne_ponderee", "moyenne", "maximum", "minimum"):
            l = dict(lecture=etiquette, score="fusion %s" % mode,
                     n_emprise=int(emprise.sum()),
                     membres=" + ".join(membres))
            for verite, (y, examine) in VERITES.items():
                if mode == "moyenne_ponderee":
                    w = np.array([poids[verite][n] for n in membres])[:, None]
                    num = np.nansum(np.where(dispo, Mz * w, 0.0), axis=0)
                    den = np.nansum(np.where(dispo, np.repeat(w, N, 1), 0.0), axis=0)
                    f = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
                elif mode == "moyenne":
                    f = np.nanmean(Mz, axis=0)
                elif mode == "maximum":
                    f = np.nanmax(Mz, axis=0)
                else:
                    f = np.nanmin(Mz, axis=0)
                f = np.where(util, f, np.nan)
                a, n, p = auc_commune(y, f, emprise & examine, unite)
                l["auc_%s" % verite] = round(a, 4) if a == a else ""
                l["n_%s" % verite] = n
                l["pos_%s" % verite] = p
            aucs = [float(l["auc_%s" % k]) for k in VERITES if l["auc_%s" % k] != ""]
            l["moyenne"] = round(sum(aucs) / len(aucs), 4) if len(aucs) == len(VERITES) else ""
            lignes.append(l)

    # ------------------------------------------------- A. emprise des huit
    larges = [n for n in COLONNE if pres[n].sum() >= 0.20 * N]
    emp8 = np.ones(N, bool)
    for n in larges:
        emp8 &= pres[n]
    print("A. EMPRISE COMMUNE AUX HUIT PRODUITS : %d batiments\n" % emp8.sum())

    fusionner("A - emprise des huit", emp8, [REF, "OSU"])
    # les six autres produits, pour situer la fusion dans le classement
    for n in larges:
        if n not in (REF, "OSU"):
            noter("A - emprise des huit", emp8, "%s seul" % n, col(n))
    # et la fusion large des douze, restreinte a la meme emprise
    fusionner("A - emprise des huit (fusion des 12)", emp8, list(COLONNE))

    # ------------------------------------------- B. emprise propre a la paire
    for partenaire in COHERENCE:
        emp = pres[REF] & pres[partenaire]
        if emp.sum() < MIN_N:
            continue
        print("B. T-stat x %s : %d batiments" % (partenaire, emp.sum()))
        fusionner("B - T-stat x %s" % partenaire, emp, [REF, partenaire])

    # les trois partenaires a la fois, la ou les quatre existent
    emp = pres[REF].copy()
    for n in COHERENCE:
        emp &= pres[n]
    if emp.sum() >= MIN_N:
        print("B. T-stat x les trois produits de coherence : %d batiments" % emp.sum())
        fusionner("B - T-stat x 3 coherences", emp, [REF] + COHERENCE)

    ev.ecrire_csv(os.path.join(RES, "exp43_fusion_ciblee_coherence.csv"), lignes)

    for etq in sorted(set(l["lecture"] for l in lignes)):
        bloc = [l for l in lignes if l["lecture"] == etq]
        print("\n=== %s  (%d batiments) ===" % (etq, bloc[0]["n_emprise"]))
        print("%-46s %11s %11s %9s" % ("score", "vs Copern.", "vs ChatMap", "moyenne"))
        for l in sorted(bloc, key=lambda d: -(float(d["moyenne"] or 0))):
            print("%-46s %11s %11s %9s"
                  % (l["score"], l["auc_ems"] or "-", l["auc_chatmap"] or "-",
                     l["moyenne"] or "-"))
    print("\necrit : %s" % os.path.join(RES, "exp43_fusion_ciblee_coherence.csv"))


if __name__ == "__main__":
    main()
