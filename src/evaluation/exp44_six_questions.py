# -*- coding: utf-8 -*-
r"""Experience 44 — les six questions du memoire, tous les chiffres recalcules.

POURQUOI
--------
La partie 2 du memoire ne doit plus repondre qu'a six questions. Les chiffres
qui y figuraient venaient de notes successives, ecrites a des dates
differentes, certaines avant les corrections etablies depuis. Cette experience
les recalcule tous, depuis les donnees, en un seul passage et sous un seul jeu
de regles.

LES REGLES, TELLES QU'ELLES SONT ETABLIES AUJOURD'HUI
-----------------------------------------------------
1. Un zero de remplissage n'est pas une valeur. Les quatre colonnes du T-stat
   portent des zeros la ou aucun calcul n'a tourne (le raster source ne declare
   pas de valeur nodata) : ils sont relus comme absence de donnee.
2. Toute AUC est mesuree PAR COMMUNE, c'est-a-dire apres centrage-reduction a
   l'interieur de chaque unite administrative de niveau 3. Une AUC sur grande
   region mesure surtout ou l'evenement a eu lieu.
3. Comparer deux produits suppose de les juger sur les MEMES batiments. Les
   deux lectures sont donnees : sur l'emprise propre de chacun, et sur
   l'emprise commune.
4. Aucun reglage n'est fait sur la verite qui sert a le noter. Les poids de
   fusion viennent de l'autre verite.
5. Le kappa n'est plus employe : il depend de la prevalence (Feinstein et
   Cicchetti, 1990), donc deux zones de sinistralite differente n'y sont pas
   comparables.

LES SIX QUESTIONS
-----------------
Q1  Le test t de Ballinger s'applique-t-il a d'autres catastrophes qu'un
    conflit arme ?
Q2  Reste-t-il efficace en 24-48 heures ?
Q3  Que vaut-il compare aux autres methodes employees sur le meme evenement ?
Q4  Le fusionner avec de la coherence ameliore-t-il la detection ?
Q5  Que vaut cette fusion par rapport aux autres methodes ?
Q6  Comment s'en servir concretement ?

SORTIE
------
resultats/exp44_six_questions.csv  — une ligne par chiffre, avec sa question,
ce qu'il mesure, sa valeur, son echantillon et sa provenance.
"""
import glob
import os
import sys

import numpy as np
from osgeo import gdal, ogr

gdal.UseExceptions()
ogr.UseExceptions()

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE); sys.path.insert(0, os.path.dirname(RACINE))
from config import DONNEES, TRAVAUX       # noqa: E402
import evaluation_commune as ev            # noqa: E402

RES = os.path.join(RACINE, "resultats")

MIN_UNITE = 50
MIN_N = 200
MIN_POS = 20

J = os.path.join(DONNEES, r"JAMAIQUE\_etude_p95")
BATI_JAM = os.path.join(DONNEES, r"JAMAIQUE\AOI\OSM_AOI_ttest.gpkg")
RASTERS_JAM = os.path.join(TRAVAUX, "exp21_ztest")

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

SORTIE = []


def dire(question, mesure, valeur, echantillon="", provenance="", note=""):
    SORTIE.append(dict(question=question, mesure=mesure, valeur=valeur,
                       echantillon=echantillon, provenance=provenance,
                       note=note))
    print("  %-58s %s" % (mesure[:58], valeur))


# ---------------------------------------------------------------- outillage
def centrer(v, sel, unite):
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
    vz = centrer(v, sel, unite)
    s = np.isfinite(vz) & sel
    n, p = int(s.sum()), int(y[s].sum())
    if n < MIN_N or p < MIN_POS or p == n:
        return float("nan"), n, p
    return ev.auc(y[s], vz[s]), n, p


def rangs(v, masque):
    out = np.full(len(v), np.nan, np.float64)
    idx = np.flatnonzero(masque & np.isfinite(v))
    if idx.size == 0:
        return out
    ordre = np.argsort(v[idx], kind="mergesort")
    r = np.empty(idx.size, np.float64)
    r[ordre] = np.arange(idx.size, dtype=np.float64)
    out[idx] = r / max(idx.size - 1, 1)
    return out


def agregations_batiments(source_path, raster_path, emprise_geom):
    """Comme ev.stats_batiments, mais rend les QUATRE agregations au lieu de la
    seule moyenne : maximum, moyenne, 75e et 90e centile sur l'empreinte."""
    ds = gdal.Open(raster_path)
    gt = ds.GetGeoTransform(); nx, ny = ds.RasterXSize, ds.RasterYSize
    b = ds.GetRasterBand(1)
    a = b.ReadAsArray().astype(np.float32)
    nd = b.GetNoDataValue()
    if nd is not None:
        a[np.isclose(a, nd)] = np.nan
    # le raster du T-stat ecrit les pixels masques a zero sans declarer de
    # nodata : c'est la meme correction que pour la table maitresse.
    a[a == 0] = np.nan
    ds = None

    e = emprise_geom.GetEnvelope()
    d = ogr.Open(source_path); ly = d.GetLayer(); tr = ev.to_wgs84(ly)
    ly.SetSpatialFilterRect(e[0], e[2], e[1], e[3])
    lat, lon = [], []
    out = dict(maximum=[], moyenne=[], centile75=[], centile90=[])
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
        sous = a[py0:py1 + 1, px0:px1 + 1]
        vv = sous[np.isfinite(sous)]
        if vv.size == 0:
            continue
        lat.append(c.GetY()); lon.append(c.GetX())
        out["maximum"].append(float(vv.max()))
        out["moyenne"].append(float(vv.mean()))
        out["centile75"].append(float(np.percentile(vv, 75)))
        out["centile90"].append(float(np.percentile(vv, 90)))
    d = None
    return (np.array(lat), np.array(lon),
            {k: np.array(v, np.float32) for k, v in out.items()})


def lire_csv(nom):
    import csv
    with open(os.path.join(RES, nom), encoding="utf-8") as f:
        texte = f.read()
    delim = ";" if texte.split("\n")[0].count(";") >= texte.split("\n")[0].count(",") else ","
    return list(csv.DictReader(texte.splitlines(), delimiter=delim))


# ===========================================================================
def main():
    Z = np.load(os.path.join(RES, "exp27c_table_maitresse_v2.npz"), allow_pickle=True)
    U = np.load(os.path.join(RES, "exp27b_unites.npz"), allow_pickle=True)
    cols = list(Z["colonnes"]); V = Z["valeurs"]; N = V.shape[0]
    ix = {c: i for i, c in enumerate(cols)}
    adm3 = U["adm3"]
    codes = {a: i for i, a in enumerate(sorted(set(adm3)))}
    unite = np.array([codes.get(a, -1) for a in adm3], np.int32)

    def col(nom):
        return V[:, ix[COLONNE[nom]]]

    def brut(c):
        return V[:, ix[c]]

    def present(nom):
        v = col(nom); m = np.isfinite(v)
        if COLONNE[nom] in ZERO_EST_ABSENCE:
            m &= (v != 0.0)
        return m

    pres = {n: present(n) for n in COLONNE}
    VER = {}
    for nom, c in (("Copernicus", "ems_damaged"), ("ChatMap", "chatmap_damaged")):
        d = brut(c)
        VER[nom] = (np.nan_to_num(d, nan=0.0) > 0, np.isfinite(d))

    # =================================================== Q1 — transposition
    print("\nQ1 — S'APPLIQUE-T-IL A D'AUTRES CATASTROPHES QU'UN CONFLIT ARME ?")

    # Q1.a — l'agregation, sur le seisme, recalculee depuis la table maitresse
    print("\n Q1.a agregation sur le SEISME (Venezuela, table maitresse)")
    for etiquette, c in (("maximum", "tstat_raster_max"),
                         ("moyenne", "tstat_raster_mean"),
                         ("centile 75", "tstat_raster_p75"),
                         ("centile 90", "tstat_raster_p90")):
        v = brut(c)
        m = np.isfinite(v) & (v != 0.0)
        aucs = []
        for verite, (y, ex) in VER.items():
            a, n, p = auc_commune(y, v, m & ex, unite)
            if a == a:
                aucs.append(a)
                dire("Q1", "seisme — agregation %s, vs %s" % (etiquette, verite),
                     round(a, 4), "%d batiments, %d signalements" % (n, p),
                     "exp27c_table_maitresse_v2.npz")
        if len(aucs) == 2:
            dire("Q1", "seisme — agregation %s, moyenne des deux verites" % etiquette,
                 round(sum(aucs) / 2, 4), "", "calcul exp44")

    # Q1.b — l'agregation, sur le CYCLONE, recalculee depuis les rasters
    print("\n Q1.b agregation sur le CYCLONE (Jamaique, rasters archives)")
    ZONES_JAM = [
        ("White House",
         os.path.join(J, "unosat", "TC20251028JAM_SHP",
                      "AP_20251031_AnalysisExtent_WhiteHouse.shp"),
         os.path.join(J, "unosat", "TC20251028JAM_SHP",
                      "AP_20251031_Damagedbuilding_WhiteHouse.shp"),
         os.path.join(RASTERS_JAM, "UNOSAT_WhiteHouse__welch_n03.tif")),
        ("Black River Village",
         os.path.join(J, "unosat", "TC20251028JAM_SHP",
                      "WV2_20251029_AnalysisExtent_BlackRiverVillage.shp"),
         os.path.join(J, "unosat", "TC20251028JAM_SHP",
                      "WV2_20251029_DamagedBuildings_BlackRiverVillage.shp"),
         os.path.join(RASTERS_JAM, "UNOSAT_BlackRiverVillage__welch_n03.tif")),
    ]
    cumul = {k: [] for k in ("maximum", "moyenne", "centile75", "centile90")}
    for nom, emp_path, pts_path, raster in ZONES_JAM:
        if not (os.path.exists(emp_path) and os.path.exists(raster)):
            print("   %s : fichiers absents, zone ignoree" % nom)
            continue
        emp = ev.lire_emprise(emp_path)
        pts = ev.lire_points(pts_path, "Main_Damag", {1, 13})
        lat, lon, vals = agregations_batiments(BATI_JAM, raster, emp)
        if len(lat) < MIN_N:
            print("   %s : %d batiments seulement" % (nom, len(lat)))
            continue
        y = ev.accrocher(pts, lat, lon)
        if int(y.sum()) < MIN_POS:
            print("   %s : %d signalements seulement" % (nom, int(y.sum())))
            continue
        for k, v in vals.items():
            a = ev.auc(y, v)
            if a == a:
                cumul[k].append(a)
                dire("Q1", "cyclone — %s, agregation %s" % (nom, k),
                     round(a, 4), "%d batiments, %d signalements"
                     % (len(lat), int(y.sum())), "calcul exp44 sur raster archive")
    for k, l in cumul.items():
        if l:
            dire("Q1", "cyclone — agregation %s, moyenne des zones" % k,
                 round(float(np.mean(l)), 4), "%d zones" % len(l), "calcul exp44")

    # Q1.c — le seuil ne se transporte pas
    print("\n Q1.c le seuil calibre en Jamaique, applique au Venezuela")
    seuils_jam = [float(r["seuil_youden"]) for r in lire_csv("exp16_seuils_par_zone.csv")
                  if r.get("pays") == "Jamaique" and r.get("seuil_youden")]
    if seuils_jam:
        sj = float(np.median(seuils_jam))
        dire("Q1", "seuil median calibre sur les zones jamaicaines",
             round(sj, 2), "%d mesures de zone" % len(seuils_jam),
             "exp16_seuils_par_zone.csv")
        v = brut("tstat_raster_max")
        m = np.isfinite(v) & (v != 0.0)
        parts = []
        for u in np.unique(unite[m]):
            mm = m & (unite == u)
            if mm.sum() < 500:
                continue
            parts.append(100.0 * (v[mm] >= sj).mean())
        if parts:
            dire("Q1", "part des batiments depassant ce seuil, commune la plus touchee",
                 round(float(np.max(parts)), 1), "%d communes" % len(parts),
                 "calcul exp44")
            dire("Q1", "part des batiments depassant ce seuil, mediane des communes",
                 round(float(np.median(parts)), 1), "%d communes" % len(parts),
                 "calcul exp44")

    # ========================================================= Q2 — 24-48 h
    print("\nQ2 — RESTE-T-IL EFFICACE EN 24-48 HEURES ?")
    lat_rows = lire_csv("exp20a_latence_acquisition.csv")
    h = [float(r["premiere_apres_h"]) for r in lat_rows if r.get("premiere_apres_h")]
    if h:
        dire("Q2", "delai median de la premiere image radar (heures)",
             round(float(np.median(h)), 1), "%d zones" % len(h),
             "exp20a_latence_acquisition.csv")
        dire("Q2", "part des zones avec une image en moins de 48 h (%)",
             round(100.0 * np.mean(np.array(h) <= 48.0), 1), "%d zones" % len(h),
             "calcul exp44")
    n48 = [float(r["n_images_a_48h"]) for r in lat_rows if r.get("n_images_a_48h")]
    if n48:
        dire("Q2", "part des zones avec DEUX images en moins de 48 h (%)",
             round(100.0 * np.mean(np.array(n48) >= 2), 1), "%d zones" % len(n48),
             "calcul exp44",
             "le test de Welch exige deux images posterieures par orbite")
    orb = lire_csv("exp21b_delai_deuxieme_image_meme_orbite.csv")
    d2 = [float(r["deuxieme_image_meme_orbite_j"]) for r in orb
          if r.get("deuxieme_image_meme_orbite_j")]
    if d2:
        dire("Q2", "delai median de la deuxieme image de la MEME orbite (jours)",
             round(float(np.median(d2)), 1), "%d zones" % len(d2),
             "exp21b_delai_deuxieme_image_meme_orbite.csv")

    # z-score a une image contre Welch a trois, apparie par zone
    zw = lire_csv("exp21_ztest_vs_welch.csv")
    par_zone = {}
    for r in zw:
        if not r.get("auc"):
            continue
        par_zone.setdefault(r["zone"], {})[(r["mode"], r["n_images_post"])] = r
    ecarts, delais_z, delais_w, gagne = [], [], [], 0
    for zone, d in par_zone.items():
        z1 = d.get(("ztest", "1")); w3 = d.get(("welch", "3"))
        if not (z1 and w3):
            continue
        e = float(z1["auc"]) - float(w3["auc"])
        ecarts.append(e)
        delais_z.append(float(z1["duree_post_jours"]))
        delais_w.append(float(w3["duree_post_jours"]))
        gagne += (e >= 0)
    if ecarts:
        dire("Q2", "z-score 1 image contre Welch 3 images — ecart moyen d'AUC",
             round(float(np.mean(ecarts)), 4), "%d zones appariees" % len(ecarts),
             "calcul exp44 sur exp21_ztest_vs_welch.csv")
        dire("Q2", "zones ou le z-score a une image fait aussi bien ou mieux",
             "%d / %d" % (gagne, len(ecarts)), "", "calcul exp44")
        dire("Q2", "delai median du z-score a une image (jours)",
             round(float(np.median(delais_z)), 2), "", "calcul exp44")
        dire("Q2", "delai median du Welch a trois images (jours)",
             round(float(np.median(delais_w)), 2), "", "calcul exp44")
        dire("Q2", "jours gagnes (mediane)",
             round(float(np.median(delais_w)) - float(np.median(delais_z)), 2),
             "", "calcul exp44")

    # ===================================================== Q3 — comparaison
    print("\nQ3 — QUE VAUT-IL COMPARE AUX AUTRES ?")
    larges = [n for n in COLONNE if pres[n].sum() >= 0.20 * N]
    commune = np.ones(N, bool)
    for n in larges:
        commune &= pres[n]
    dire("Q3", "emprise commune aux produits a large couverture (batiments)",
         int(commune.sum()), "%d produits" % len(larges), "calcul exp44")

    for etiquette, emprise_de in (("emprise propre", None), ("emprise commune", commune)):
        for nom in COLONNE:
            emp = pres[nom] if emprise_de is None else emprise_de
            aucs = []
            for verite, (y, ex) in VER.items():
                a, n, p = auc_commune(y, col(nom), emp & ex, unite)
                if a == a:
                    aucs.append(a)
                    dire("Q3", "%s — %s, vs %s" % (etiquette, nom, verite),
                         round(a, 4), "%d batiments, %d signalements" % (n, p),
                         "calcul exp44")
            if len(aucs) == 2:
                dire("Q3", "%s — %s, moyenne des deux verites" % (etiquette, nom),
                     round(sum(aucs) / 2, 4), "", "calcul exp44")

    # ============================================= Q4 et Q5 — fusion ciblee
    print("\nQ4 / Q5 — LA FUSION AVEC LA COHERENCE")

    def fusion(membres, emprise, mode, verite):
        R = np.vstack([rangs(col(n), emprise) for n in membres])
        dispo = np.isfinite(R)
        if mode == "moyenne":
            f = np.nanmean(np.where(dispo, R, np.nan), axis=0)
        elif mode == "maximum":
            f = np.nanmax(np.where(dispo, R, np.nan), axis=0)
        elif mode == "minimum":
            f = np.nanmin(np.where(dispo, R, np.nan), axis=0)
        else:  # moyenne ponderee, poids venant de l'AUTRE verite
            autre = "ChatMap" if verite == "Copernicus" else "Copernicus"
            y2, ex2 = VER[autre]
            w = []
            for n in membres:
                a, _, _ = auc_commune(y2, col(n), emprise & ex2, unite)
                w.append(max(a - 0.5, 0.0) if a == a else 0.0)
            w = np.array(w, np.float64)
            if w.sum() <= 0:
                w = np.ones(len(membres))
            num = np.nansum(np.where(dispo, R * w[:, None], 0.0), axis=0)
            den = np.nansum(np.where(dispo, np.repeat(w[:, None], R.shape[1], 1), 0.0),
                            axis=0)
            f = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
        return np.where(dispo.sum(axis=0) > 0, f, np.nan)

    CIBLES = [("T-stat x OSU", [REF, "OSU"]),
              ("T-stat x BDPM", [REF, "BDPM (notre reproduction)"]),
              ("T-stat x EOS-RS", [REF, "EOS-RS"]),
              ("fusion des douze", list(COLONNE))]

    for etiquette, membres in CIBLES:
        emp = np.ones(N, bool)
        for n in membres:
            emp &= pres[n]
        if emp.sum() < MIN_N:
            continue
        dire("Q4", "%s — emprise commune (batiments)" % etiquette, int(emp.sum()),
             "", "calcul exp44")
        # les termes seuls, sur cette emprise
        for n in membres if len(membres) <= 3 else [REF]:
            aucs = []
            for verite, (y, ex) in VER.items():
                a, _, _ = auc_commune(y, col(n), emp & ex, unite)
                if a == a:
                    aucs.append(a)
            if len(aucs) == 2:
                dire("Q4", "%s — %s seul, moyenne des deux verites" % (etiquette, n),
                     round(sum(aucs) / 2, 4), "", "calcul exp44")
        for mode in ("moyenne_ponderee", "moyenne", "maximum", "minimum"):
            aucs = []
            for verite, (y, ex) in VER.items():
                f = fusion(membres, emp, mode, verite)
                a, _, _ = auc_commune(y, f, emp & ex, unite)
                if a == a:
                    aucs.append(a)
            if len(aucs) == 2:
                dire("Q4", "%s — fusion %s, moyenne des deux verites"
                     % (etiquette, mode), round(sum(aucs) / 2, 4), "", "calcul exp44")

    # Q5 : la fusion ciblee replacee dans le classement, sur l'emprise commune
    print("\n Q5 la fusion ciblee, replacee dans le classement")
    for mode in ("moyenne_ponderee",):
        aucs = []
        for verite, (y, ex) in VER.items():
            f = fusion([REF, "OSU"], commune, mode, verite)
            a, _, _ = auc_commune(y, f, commune & ex, unite)
            if a == a:
                aucs.append(a)
        if len(aucs) == 2:
            dire("Q5", "emprise commune — fusion T-stat x OSU (%s)" % mode,
                 round(sum(aucs) / 2, 4), "%d batiments" % commune.sum(),
                 "calcul exp44")
        aucs = []
        for verite, (y, ex) in VER.items():
            f = fusion(list(COLONNE), commune, mode, verite)
            a, _, _ = auc_commune(y, f, commune & ex, unite)
            if a == a:
                aucs.append(a)
        if len(aucs) == 2:
            dire("Q5", "emprise commune — fusion des douze (%s)" % mode,
                 round(sum(aucs) / 2, 4), "%d batiments" % commune.sum(),
                 "calcul exp44")

    # ========================================================= Q6 — usages
    print("\nQ6 — COMMENT S'EN SERVIR ?")
    detruits = np.nan_to_num(brut("ems_destroyed"), nan=0.0) > 0
    y_ems, ex_ems = VER["Copernicus"]

    def au_sommet(score, emprise, n_tete):
        s = emprise & np.isfinite(score) & ex_ems
        idx = np.flatnonzero(s)
        if idx.size < n_tete:
            return None
        ordre = idx[np.argsort(-score[idx], kind="mergesort")][:n_tete]
        return 100.0 * y_ems[ordre].mean()

    scores = {"T-stat seul": col(REF),
              "fusion T-stat x OSU": fusion([REF, "OSU"], commune,
                                            "moyenne_ponderee", "Copernicus"),
              "fusion des douze": fusion(list(COLONNE), commune,
                                         "moyenne_ponderee", "Copernicus")}
    for nom, sc in scores.items():
        for n_tete in (1000, 5000):
            p = au_sommet(sc, commune, n_tete)
            if p is not None:
                dire("Q6", "ciblage — precision sur les %d premiers, %s (%%)"
                     % (n_tete, nom), round(p, 1),
                     "emprise commune", "calcul exp44")

    for nom, sc in scores.items():
        s = commune & np.isfinite(sc) & ex_ems
        idx = np.flatnonzero(s)
        ordre = idx[np.argsort(-sc[idx], kind="mergesort")]
        d = detruits[ordre]
        total = d.sum()
        if total < MIN_POS:
            continue
        cum = np.cumsum(d)
        for cible in (0.90, 0.95, 0.99):
            k = int(np.searchsorted(cum, cible * total) + 1)
            dire("Q6", "balayage — part a relire pour %d %% des detruits, %s (%%)"
                 % (int(cible * 100), nom), round(100.0 * k / len(ordre), 1),
                 "%d detruits" % int(total), "calcul exp44")

    ev.ecrire_csv(os.path.join(RES, "exp44_six_questions.csv"), SORTIE)
    print("\n%d chiffres ecrits dans exp44_six_questions.csv" % len(SORTIE))


if __name__ == "__main__":
    main()
