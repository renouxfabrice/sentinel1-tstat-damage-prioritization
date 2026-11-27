# Prioriser les bâtiments à vérifier après une catastrophe avec Sentinel-1

**Language / Langue :** 🇬🇧 [English](README.en.md) · 🇫🇷 Français

Après une catastrophe soudaine, la question n'est pas seulement de savoir où il y a des dégâts. Sur le terrain, la vraie question est souvent :

> **par où commencer les vérifications ?**

Les images optiques permettent de voir les bâtiments, les routes et les débris en détail. Mais elles arrivent parfois tard, ou sont cachées par les nuages. Sentinel-1 est un radar : il prend des images de jour comme de nuit et à travers les nuages.

Le radar ne montre pas directement les dégâts. Il mesure un changement du signal renvoyé par le sol, et ce changement dépend de la géométrie de prise de vue, de ce qui est observé et du type de changement.

Ce dépôt accompagne une étude sur l'usage de Sentinel-1 pour **classer les bâtiments ou les zones à vérifier en priorité** après une catastrophe.

## Ce que fait l'étude

- elle reprend une méthode de détection de changement pixel par pixel (test t) ;
- elle ramène les scores à l'échelle des bâtiments ;
- elle compare ce classement à d'autres produits publiés après les mêmes catastrophes ;
- elle utilise la même couche d'empreintes bâties pour tous les produits, pour que la comparaison soit équitable ;
- elle reproduit plusieurs méthodes basées sur la cohérence interférométrique ;
- elle teste des combinaisons (fusions) de scores et de rangs ;
- elle applique aussi la méthode aux routes et aux ponts ;
- elle décrit les limites des données de référence et des zones étudiées.

Les résultats sur le bâti portent sur **deux cas** : un séisme au Venezuela et un cyclone en Jamaïque. Un **troisième cas**, une lave torrentielle d'origine glaciaire au Népal, sert à tester la méthode sur les routes et les ponts, et à voir si les conclusions tiennent pour un autre type d'aléa.

En combinant notre test t avec le produit de cohérence OSU (moyenne pondérée des rangs), l'AUC moyenne passe de **0,740** à **0,764**. Ce gain est mesuré sur les empreintes bâties et les références décrites dans l'étude. Il ne prouve pas que la méthode marche partout, ni qu'elle donnera le même résultat sur une autre catastrophe.

Le résultat est donc un **outil pour prioriser les vérifications**, pas un diagnostic automatique des dégâts.

## Lire l'étude

- 📄 [Texte complet](docs/partie_2/partie_2.md) : dix sections, 20 figures, quatre tableaux, une discussion des limites des références et un dictionnaire des méthodes comparées.
- 📚 [Bibliographie](docs/references.md) : références citées, identifiants (DOI) et fichier RIS.

Les sections de méthode donnent les formules, les paramètres, le prétraitement, le passage au bâtiment et les règles d'évaluation.

## Contenu du dépôt

| Dossier ou fichier | Contenu |
|---|---|
| [`docs/partie_2/figures/`](docs/partie_2/figures/) | Les 20 figures de l'étude |
| [`tables/`](tables/) | Les 15 tables de synthèse citées dans l'étude (CSV) |
| [`data/results/`](data/results/) | 76 tables de résultats : AUC, seuils, agrégations et fusions |
| [`data/raw/produits_tiers/`](data/raw/produits_tiers/) | Produits et relevés tiers utilisés, avec leurs attributions |
| [`data/inventaire_donnees.csv`](data/inventaire_donnees.csv) | Inventaire des 2 074 fichiers utilisés (environ 134 Go) |
| [`src/`](src/) | Les 61 programmes qui calculent les tables de résultats |
| [`src/reevaluation/`](src/reevaluation/) | Les programmes de la réévaluation du 1er octobre 2026 (expériences 73 à 86) |
| [`src/visualization/`](src/visualization/) | Les programmes R qui produisent les figures (8 tracent une figure, 2 contiennent des fonctions communes) |
| [`notebooks/`](notebooks/) | 6 carnets pour recalculer les chiffres cités |
| [`docs/datasets/data_availability.md`](docs/datasets/data_availability.md) | Données fournies, données non fournies et comment y accéder |

## Refaire les calculs

Les figures qui portent des chiffres sont produites par des programmes R à partir des tables de résultats. Si une table change, il suffit de relancer le programme pour mettre la figure à jour. Les autres figures — planches d'imagerie, schémas, cartes — sont décrites dans leur légende.

Les figures 5, 6 et 7 ont été recalculées le 1er octobre 2026. Les anciennes versions utilisaient le test de Welch et une évaluation sur OpenStreetMap. Les versions actuelles utilisent les réglages de l'outil et la méthode d'évaluation décrits dans l'étude.

Chaque carnet se termine par des vérifications automatiques : il contrôle que les tables donnent bien les chiffres publiés dans l'étude. Si une valeur ne correspond plus, le carnet s'arrête en erreur.

## Données

Les images Sentinel-1 sont en accès libre, mais elles ne sont pas copiées dans ce dépôt. L'inventaire des données indique pour chaque fichier son origine, son rôle et comment le retrouver.

Les tables de résultats, elles, sont dans le dépôt : on peut les consulter sans télécharger les images radar.

Certaines données tierces ont leurs propres conditions d'accès et de réutilisation. Les licences et les attributions sont listées dans [`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

## À propos du test t

Le code du test t utilisé dans l'outil n'est pas fourni ici : il vient d'un code publié sans licence qui autorise sa redistribution.

L'étude donne quand même :

- la formule utilisée ;
- les périodes avant et après l'événement ;
- la différence entre le test à variance regroupée et le test de Welch ;
- les paramètres de traitement ;
- les différences entre la formule de l'article de référence et le code diffusé par son auteur.

Les cartes et les résultats utilisent le test à variance regroupée, que le dépôt de référence appelle lui-même **Pooled t-test (original)**. Une version plus récente de ce dépôt propose Welch par défaut ; nous ne l'avons pas utilisée ici.

## Limites

Un score élevé signale un changement du signal radar à regarder de plus près. Il ne veut pas dire que le bâtiment est détruit.

Le test mesure un changement du signal renvoyé, pas un dégât. Il peut passer à côté d'une destruction totale quand une surface rugueuse est remplacée par une autre surface rugueuse (par exemple une piste végétalisée recouverte de sédiments). La figure 17 en montre un cas.

Le résultat dépend aussi :

- de la date et de la qualité des images ;
- de la géométrie de prise de vue ;
- de la saison et de l'humidité ;
- de la résolution et de la couche d'empreintes bâties ;
- de la référence utilisée pour l'évaluation ;
- du nombre de bâtiments et de zones disponibles.

Pour les routes et les ponts, c'est pareil : les scores aident à repérer des tronçons à vérifier, mais ils ne suffisent pas pour dire si une route est praticable.

## Comment ce travail a été fait

J'ai conçu cette étude, choisi les cas, les données et les références, et vérifié les résultats. Pour écrire et corriger le code, faire les calculs et rédiger la documentation, je me suis fait aider par un outil d'intelligence artificielle, Claude (Anthropic). J'ai relu le code et les textes produits, et les chiffres publiés sont contrôlés par les carnets décrits plus haut. Les erreurs qui resteraient sont les miennes : n'hésitez pas à les signaler.

Le détail — ce que l'outil a fait, ce qu'il n'a pas fait, et comment c'est vérifiable — est dans [`AI_USE.md`](AI_USE.md).

## Licence

Le code est distribué sous licence [MIT](LICENSE).

Les données tierces gardent leurs propres licences. Les conditions et les attributions sont dans [`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

Pour citer ce travail, voir [`CITATION.cff`](CITATION.cff).

## Contact

**Fabrice Renoux** ([@renouxfabrice](https://github.com/renouxfabrice))

Pour signaler une erreur, proposer une amélioration ou poser une question sur les données, le plus simple est d'ouvrir [une *issue*](https://github.com/renouxfabrice/sentinel1-tstat-damage-prioritization/issues/new) : la réponse restera utile aux suivants.

Pour un échange privé, passez par le formulaire de contact du profil GitHub.
