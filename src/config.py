# -*- coding: utf-8 -*-
"""Racines des donnees d'entree des scripts de `src/`.

Les jeux de donnees d'entree ne sont pas redistribues dans ce depot : plusieurs
portent des conditions de reutilisation qui l'interdiraient, et les acquisitions
Sentinel-1 sont de toute facon librement accessibles a leur source. Le fichier
`data/inventaire_donnees.csv` donne, pour chacun, son role et son chemin
d'origine, de quoi reconstituer l'arborescence attendue ici.

Trois racines suffisent. Elles se declarent par variable d'environnement, ou en
modifiant les valeurs par defaut ci-dessous :

    S1_TSTAT_DONNEES      couches vectorielles, rasters de score, verites de
                          reference, limites administratives, population
    S1_TSTAT_COHERENCE    produits interferometriques et leurs tables de paires
    S1_TSTAT_WHITEHOUSE   le cas cyclonique, dont les couches sont tenues a part

Les sorties sont ecrites a cote des entrees, dans le sous-dossier que declare
chaque script en tete de son bloc CONFIGURATION.
"""
import os

DONNEES = os.environ.get("S1_TSTAT_DONNEES", os.path.join("..", "donnees"))
COHERENCE = os.environ.get("S1_TSTAT_COHERENCE", os.path.join("..", "donnees", "coherence"))
WHITEHOUSE = os.environ.get("S1_TSTAT_WHITEHOUSE", os.path.join("..", "donnees", "whitehouse"))


def verifier(*racines):
    """Echoue tot, et en le disant, si une racine n'existe pas.

    A appeler au debut d'un script plutot que de laisser GDAL renvoyer un
    None silencieux vingt lignes plus loin.
    """
    manquantes = [r for r in racines if not os.path.isdir(r)]
    if manquantes:
        raise SystemExit(
            "Racine de donnees introuvable :\n  "
            + "\n  ".join(os.path.abspath(r) for r in manquantes)
            + "\n\nRenseignez S1_TSTAT_DONNEES, S1_TSTAT_COHERENCE ou "
              "S1_TSTAT_WHITEHOUSE, ou modifiez src/config.py."
        )
