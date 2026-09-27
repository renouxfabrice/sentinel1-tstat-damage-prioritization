# Évaluer et améliorer la priorisation des dommages au bâti avec Sentinel-1

**Language / Langue :** 🇬🇧 [English](README.en.md) · 🇫🇷 Français

Après une catastrophe soudaine, la question opérationnelle n'est pas seulement
« où y a-t-il des dommages ? », mais aussi :

> **où faut-il vérifier en premier ?**

Les images optiques permettent souvent une interprétation détaillée des
bâtiments, des routes et des débris. Elles peuvent toutefois être indisponibles,
acquises trop tard ou masquées par les nuages. Sentinel-1 fournit un signal radar
indépendant de la lumière et de la couverture nuageuse.

Ce signal ne montre cependant pas directement les dommages. Il mesure une
variation de rétrodiffusion, dont l'interprétation dépend notamment de la
géométrie radar, de la structure observée et de la nature du changement.

Ce dépôt accompagne une étude consacrée à l'utilisation de Sentinel-1 pour
produire un **classement des bâtiments ou secteurs à vérifier** après une
catastrophe.

## Ce que contient l'étude

L'étude :

- réimplémente une approche fondée sur une statistique de changement par pixel ;
- agrège ensuite les scores à l'échelle des bâtiments ;
- compare ce classement à d'autres produits disponibles après catastrophe ;
- harmonise les empreintes bâties utilisées pour rendre les comparaisons plus équitables ;
- reproduit plusieurs méthodes fondées sur la cohérence interférométrique ;
- évalue des fusions de scores et de rangs ;
- étend la mesure aux routes et aux ponts ;
- documente les limites des données de référence et des emprises étudiées.

Les résultats sur le bâti portent sur **deux études de cas**, un séisme au
Venezuela et un cyclone tropical en Jamaïque. Une **troisième campagne**, une
lave torrentielle d'origine glaciaire au Népal, sert à éprouver la méthode sur
les routes et les ponts, et à vérifier si ses conclusions tiennent sur un aléa
de nature différente.

Dans la configuration T-stat × OSU, la fusion ciblée fait passer l'AUC moyenne
de **0,740** pour la T-stat seule à **0,764**. Cette amélioration est mesurée
sur les empreintes bâties et les références décrites dans l'étude. Elle ne
constitue ni une validation générale de la détection des dommages, ni une
garantie de transférabilité à d'autres catastrophes.

Le résultat doit donc être lu comme un **outil de priorisation**, et non comme
un diagnostic automatique de dommage.

## Lire le document

- 📄 [Texte complet](docs/partie_2/partie_2.md)
  Dix sections, 17 figures, quatre tableaux, une discussion des limites des
  références utilisées et un dictionnaire des méthodes comparées.

- 📚 [Bibliographie](docs/references.md)
  Références citées, identifiants pérennes et fichier RIS source.

Les sections consacrées à la méthode présentent les formules, les paramètres,
les choix de prétraitement, l'agrégation à l'échelle du bâtiment et les règles
d'évaluation.

## Organisation du dépôt

| Dossier ou fichier | Contenu |
|---|---|
| [`docs/partie_2/figures/`](docs/partie_2/figures/) | Les 17 figures du document |
| [`tables/`](tables/) | Les quatorze tables de synthèse citées dans le document, au format CSV |
| [`data/results/`](data/results/) | 74 tables de résultats : AUC, seuils, agrégations et fusions |
| [`data/raw/produits_tiers/`](data/raw/produits_tiers/) | Produits et relevés tiers utilisés en entrée, avec leurs attributions |
| [`data/inventaire_donnees.csv`](data/inventaire_donnees.csv) | Inventaire des 2 074 fichiers employés, soit environ 134 Go |
| [`src/`](src/) | Les 47 programmes qui calculent les tables de résultats |
| [`src/visualization/`](src/visualization/) | Les neuf programmes R qui produisent les figures |
| [`notebooks/`](notebooks/) | Six carnets permettant de rejouer les chiffres cités |
| [`docs/datasets/data_availability.md`](docs/datasets/data_availability.md) | Données redistribuées, données non redistribuées et procédures d'accès |

## Reproduire les résultats

Les figures sont produites par des programmes R à partir des tables de résultats.
Elles ne sont donc plus dessinées manuellement : une modification validée des
tables peut être propagée aux figures sans retouche graphique.

Les figures 5, 6 et 7 ont été recalculées le 1er octobre 2026. Les versions
précédentes employaient le test de Welch et une évaluation fondée sur
OpenStreetMap, alors que les résultats retenus dans l'étude emploient la
configuration de l'outil et la convention d'évaluation décrites dans le
document.

Les six carnets se terminent par des assertions. Ils vérifient que les tables
embarquant les résultats correspondent bien aux chiffres publiés dans le
document. Si une table est modifiée ou ne contient plus la valeur attendue, le
carnet échoue au contrôle final.

## Données

Les acquisitions Sentinel-1 employées dans les calculs sont ouvertes, mais elles
ne sont pas redistribuées dans ce dépôt. L'inventaire des données indique leur
origine, leur rôle et les informations nécessaires pour retrouver les mêmes
entrées.

Les tables contenant les résultats publiés sont en revanche incluses dans le
dépôt. Elles peuvent être consultées sans télécharger les acquisitions radar.

Certaines données tierces restent soumises à leurs propres conditions d'accès et
de réutilisation. Les licences et les attributions à conserver sont recensées
dans [`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

## À propos du test t

L'implémentation opérationnelle du test t par pixel n'est pas redistribuée dans
ce dépôt. Elle dérive d'un code publié sans licence permettant sa redistribution.

Le document fournit néanmoins :

- la formulation mathématique employée ;
- la description des périodes avant et après événement ;
- la distinction entre la forme à variance regroupée et la forme de Welch ;
- les paramètres de traitement ;
- ce qui sépare la formule écrite dans l'article de référence du code que son
  auteur a diffusé avec lui.

Les cartes et les résultats présentés ici emploient la forme à variance
regroupée, celle que le dépôt de référence appelle lui-même **Pooled t-test
(original)**. Une version ultérieure de ce dépôt propose Welch par défaut ; ce
réglage n'a pas été retenu pour les calculs présentés.

## Limites d'interprétation

Un score élevé indique une anomalie de signal à examiner. Il ne signifie pas
automatiquement qu'un bâtiment est détruit.

Le test mesure un **changement de rugosité de surface**, et non un dommage. Il
est aveugle lorsque la destruction remplace un milieu rugueux par un autre
milieu rugueux, même quand les dégâts sont totaux — la figure 17 en montre un
cas.

L'interprétation dépend par ailleurs :

- de la date et de la qualité des acquisitions ;
- de la géométrie d'observation ;
- de la saison et de l'humidité de la scène ;
- de la résolution et de la couche d'empreintes bâties ;
- de la référence employée pour l'évaluation ;
- du nombre de bâtiments et d'emprises disponibles.

Les résultats sur les routes et les ponts se lisent de la même manière : ils
peuvent aider à repérer des tronçons à vérifier, mais ne permettent pas à eux
seuls de conclure à la praticabilité d'un axe.

## Licence

Le code et les textes de ce dépôt sont distribués sous licence [MIT](LICENSE).

Les données tierces conservent leurs propres licences. Les conditions
d'utilisation et les attributions nécessaires figurent dans
[`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

Pour citer ce travail, consulter [`CITATION.cff`](CITATION.cff).

L'adresse d'un dépôt GitHub n'est pas, à elle seule, une référence
bibliographique stable. L'archivage de cette version dans un service fournissant
un identifiant pérenne reste à effectuer.

## Contact et contributions

**Fabrice Renoux** — [@renouxfabrice](https://github.com/renouxfabrice)

Pour signaler une erreur, proposer une amélioration ou demander des précisions
sur les données intermédiaires, le mieux est d'ouvrir
[une *issue*](https://github.com/renouxfabrice/sentinel1-tstat-damage-prioritization/issues/new).
Les échanges restent ainsi accessibles aux lecteurs et contributeurs suivants.

Pour un échange privé, le formulaire de contact du profil GitHub convient.
