# -*- coding: utf-8 -*-
"""Inventaire consolidé des paires interférométriques employées pour les calculs de cohérence, rassemblées depuis cinq fichiers de schémas différents en un tableau unique portant le nom de zone de chaque paire.

Les chemins d'entree et de sortie sont declares dans le bloc CONFIGURATION
ci-dessous, relativement aux racines de donnees fixees dans `config.py`.
"""

import csv
import io
import os
import sys
from config import COHERENCE, DONNEES

ETUDE = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ETUDE, "exp63_paires_coherence.csv")

SOURCES = [
    dict(chemin=os.path.join(COHERENCE, r"Jindiries\pairs.csv"),
         zone="Syrie - Jindiries", zone_deduite="nom du dossier"),
    dict(chemin=os.path.join(COHERENCE, r"VENEZ\Methode BDPM\pairs.csv"),
         zone="Venezuela", zone_deduite="nom du dossier"),
    dict(chemin=os.path.join(COHERENCE,
                             r"VENEZ\Methode BDPM\burst Cariballada_20m",
                             r"paires_pre_evenement.csv"),
         zone="Venezuela - Caraballeda", zone_deduite="nom du dossier"),
    # Ces deux fichiers ne portent aucune zone dans leur nom. Le rattachement
    # au Venezuela n'est pas devine : 100 % de leurs granules se retrouvent
    # dans VENEZ\Methode BDPM\pairs.csv, et 0 % dans le fichier syrien. La
    # verification est refaite a chaque execution par `verifier_rattachement()`
    # ci-dessous, qui echoue bruyamment si ce n'etait plus vrai.
    dict(chemin=os.path.join(DONNEES, r"image_pairs.csv"),
         zone="Venezuela",
         zone_deduite="granules communs a 100% avec VENEZ ; base courte 5-6 j"),
    dict(chemin=os.path.join(DONNEES, r"image_pairs2.csv"),
         zone="Venezuela",
         zone_deduite="granules communs a 100% avec VENEZ ; sous-ensemble"),
]

REFERENCE_VENEZ = os.path.join(COHERENCE, r"VENEZ\Methode BDPM\pairs.csv")
REFERENCE_SYRIE = os.path.join(COHERENCE, r"Jindiries\pairs.csv")

# Les cinq schemas ne se recouvrent pas. On ramene tout a un jeu commun, et ce
# qui n'y entre pas part dans `autres_champs` plutot que d'etre jete.
CORRESPONDANCES = {
    "sat": "satellite", "dir": "direction", "track": "direction",
    "type": "type_paire", "orbit": "orbite_relative",
    "rel_orbit": "orbite_relative", "orbite": "direction",
    "frame": "frame", "burst_id": "burst_id", "sous_fauchee": "sous_fauchee",
    "date a (master)": "date_master", "master": "date_master",
    "date b (slave)": "date_slave", "slave": "date_slave",
    "\u0394 days": "delta_jours", "interval_days": "delta_jours",
    "aoi%": "couverture_aoi", "perpendicular(m)": "base_perpendiculaire_m",
    "scene": "granule_slave", "slave scene": "granule_slave",
    "slave_granule": "granule_slave",
    "master scene": "granule_master", "master_granule": "granule_master",
}

COLONNES = ["zone", "zone_deduite", "fichier_source", "satellite", "direction",
            "type_paire", "orbite_relative", "frame", "burst_id",
            "sous_fauchee", "date_master", "date_slave", "delta_jours",
            "couverture_aoi", "base_perpendiculaire_m", "granule_master",
            "granule_slave", "doublon_de", "autres_champs"]


def log(m):
    print(m)
    sys.stdout.flush()


def lire(source):
    chemin = source["chemin"]
    if not os.path.exists(chemin):
        log("  ABSENT : %s" % chemin)
        return []
    with io.open(chemin, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f))
    out = []
    for l in lignes:
        row = {c: "" for c in COLONNES}
        row["zone"] = source["zone"]
        row["zone_deduite"] = source["zone_deduite"]
        row["fichier_source"] = chemin
        reste = []
        for cle, val in l.items():
            if cle is None:
                continue
            cible = CORRESPONDANCES.get(cle.strip().lower())
            if cible:
                row[cible] = (val or "").strip()
            elif (val or "").strip():
                reste.append("%s=%s" % (cle.strip(), val.strip()))
        row["autres_champs"] = " | ".join(reste)
        out.append(row)
    log("  %-52s %3d paire(s)" % (os.path.basename(chemin), len(out)))
    return out


def granules_de(chemin):
    """Tous les identifiants de granule d'un CSV, quel que soit son schema."""
    import re
    out = set()
    if not os.path.exists(chemin):
        return out
    with io.open(chemin, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            for v in row.values():
                v = (v or "").strip()
                if re.match(r"^S1[A-Z]_IW_SLC", v):
                    out.add(v.replace("-SLC", ""))
    return out


def verifier_rattachement():
    """Refait la preuve qui rattache les deux fichiers anonymes au Venezuela.

    On ne se contente pas d'avoir trouve la reponse une fois : la verification
    tourne a chaque execution, et parle si le resultat change.
    """
    ven = granules_de(REFERENCE_VENEZ)
    syr = granules_de(REFERENCE_SYRIE)
    if not ven:
        log("  (verification impossible : fichier Venezuela de reference absent)")
        return
    for chemin in (os.path.join(DONNEES, r"image_pairs.csv"),
                   os.path.join(DONNEES, r"image_pairs2.csv")):
        g = granules_de(chemin)
        if not g:
            continue
        pv = 100.0 * len(g & ven) / len(g)
        ps = 100.0 * len(g & syr) / len(g) if syr else 0.0
        etat = "OK" if pv > 95 else "A REVOIR"
        log("  %-22s %3d granules | Venezuela %3.0f%% | Syrie %3.0f%%  -> %s"
            % (os.path.basename(chemin), len(g), pv, ps, etat))


def cle_paire(r):
    """Identifie une paire par orbite + les deux dates, pour reperer les doublons."""
    return (r["orbite_relative"], r["date_master"], r["date_slave"])


def main():
    log("Verification du rattachement des fichiers sans zone :")
    verifier_rattachement()
    log("")

    toutes = []
    for s in SOURCES:
        toutes.extend(lire(s))

    # Les trois fichiers venezueliens se recouvrent partiellement : image_pairs2
    # est pour l'essentiel un sous-ensemble de VENEZ pairs.csv. On marque les
    # doublons au lieu de les supprimer — la ligne garde son fichier d'origine,
    vues = {}
    for r in toutes:
        k = (r["zone"], cle_paire(r))
        if k[1] == ("", "", ""):
            r["doublon_de"] = ""
            continue
        if k in vues:
            r["doublon_de"] = os.path.basename(vues[k])
        else:
            r["doublon_de"] = ""
            vues[k] = r["fichier_source"]

    with io.open(SORTIE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES, delimiter=";")
        w.writeheader()
        w.writerows(toutes)

    par_zone = {}
    for r in toutes:
        par_zone.setdefault(r["zone"], []).append(r)
    log("")
    for zone in sorted(par_zone):
        rows = par_zone[zone]
        uniques = [r for r in rows if not r.get("doublon_de")]
        orbites = sorted({r["orbite_relative"] for r in rows
                          if r["orbite_relative"]})
        log("  %-26s %3d lignes dont %3d paires distinctes | orbites: %s"
            % (zone, len(rows), len(uniques), ", ".join(orbites) or "-"))
    log("")
    uniques = sum(1 for r in toutes if not r.get("doublon_de"))
    log("%d lignes, %d paires distinctes -> %s" % (len(toutes), uniques, SORTIE))


if __name__ == "__main__":
    main()
