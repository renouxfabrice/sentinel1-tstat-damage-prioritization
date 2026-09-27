# Les données des calculs

Ce dossier répond à une question simple : **d'où vient chaque chiffre ?**

L'inventaire complet est dans [`inventaire_donnees.csv`](inventaire_donnees.csv),
produit par balayage du disque de travail et non écrit à la main — une liste
tenue à la main diverge de la réalité dès la semaine suivante. Il donne pour
chaque fichier sa campagne, son rôle, son chemin d'origine, sa taille et sa
date de dernière modification.

## Ce qui est ici, et ce qui ne l'est pas

Les **tables de résultats** — celles qui portent les AUC, les seuils, les
agrégations et les sorties de fusion — sont copiées dans
[`results/`](results/). Elles pèsent peu et ce sont elles qu'un lecteur veut
rouvrir. Il y en a 68.

Les **rasters, emprises volumineuses et archives** ne sont pas redistribués.
Plusieurs portent des conditions de réutilisation qui l'interdiraient, et les
acquisitions Sentinel-1 sont de toute façon librement accessibles à leur
source. L'inventaire donne de quoi les retrouver.

## L'évaluation refaite du 1er octobre 2026

Quatre tables portent une évaluation qui **remplace** des mesures plus anciennes
présentes ailleurs dans ce dossier. Deux défauts ont été corrigés : les
comparaisons jamaïcaines s'appuyaient sur OpenStreetMap, où plusieurs emprises
comptent moins de bâtiments que Copernicus n'a signalé de dommages, et les
points de signalement étaient rattachés aux empreintes par accrochage à vingt
mètres du centroïde, sans rien qui empêche un même point d'en marquer
plusieurs.

| fichier | ce qu'il porte |
|---|---|
| [`results/exp75_detail.csv`](results/exp75_detail.csv) | toutes les configurations jamaïcaines, sur Open Buildings seule, appariement strict |
| [`results/exp73_detail.csv`](results/exp73_detail.csv) | les mêmes configurations au Venezuela, sur Overture |
| [`results/exp74_deux_campagnes.csv`](results/exp74_deux_campagnes.csv) | les deux campagnes côte à côte, chacune comparée à sa propre référence |
| [`results/exp79_annexe_L.csv`](results/exp79_annexe_L.csv) | la variance regroupée face au test de Welch, sur les deux campagnes |
| [`results/exp82_nepal.csv`](results/exp82_nepal.csv) | le test t sur les routes et les ponts emportés par la lave torrentielle népalaise des 26–27 août 2026, activation EMSR927 — la seule mesure de ce travail dont **les négatifs sont déclarés** par l'analyste et non déduits |

La règle d'appariement retenue est celle-ci : un point qui tombe dans une
empreinte lui est assigné ; s'ils sont plusieurs, le plus sévère l'emporte ; un
point orphelin va à l'empreinte non déjà prise la plus proche, mesurée au
contour et non au centroïde ; une empreinte ne reçoit qu'un seul point.

Les comparaisons dont la prévalence sort de l'intervalle de 5 à 95 % sont
écartées des moyennes : l'aire sous la courbe n'y mesure rien de fiable.

## Répartition

| Campagne | Fichiers | Volume |
|---|---|---|
| Charte | 2 | 0.00 Go |
| Colombie | 91 | 0.22 Go |
| Haiti | 96 | 4.33 Go |
| Jamaique | 689 | 2.04 Go |
| Transversal | 362 | 44.06 Go |
| Venezuela | 834 | 83.71 Go |

## Par rôle

| Rôle | Fichiers | Volume |
|---|---|---|
| Cohérence — reproduction des méthodes publiées | 353 | 52.50 Go |
| Autre | 411 | 48.11 Go |
| Vérité de référence — Copernicus EMS Rapid Mapping | 1044 | 10.21 Go |
| Imagerie optique très haute résolution — Vantor | 3 | 8.77 Go |
| Emprises bâties — OSM et Overture | 61 | 4.96 Go |
| Analyse multi-vérités et comptages par classe | 54 | 2.58 Go |
| Vérité de référence — ChatMap, signalements au sol | 28 | 1.85 Go |
| Produit concurrent — fAIr, HOT OSM | 36 | 1.82 Go |
| Orthophotographie drone | 4 | 1.51 Go |
| Produit concurrent — UNGSC | 12 | 0.97 Go |
| Produit concurrent — NASA DRCS | 17 | 0.86 Go |
| Comparaison et fusion multi-sources | 22 | 0.15 Go |
| Produit concurrent — DISHA | 12 | 0.05 Go |
| Produit concurrent — EOS-RS | 5 | 0.02 Go |
| Étude des seuils et des agrégations | 9 | 0.00 Go |
| Charte internationale — dépouillement des activations | 2 | 0.00 Go |
| Tables livrées — seuils et agrégations | 1 | 0.00 Go |

## Avertissement sur les licences

Les conditions de réutilisation diffèrent d'un jeu à l'autre et sont
récapitulées, pour les vingt-sept jeux employés, dans
[`../tables/datasets_sources_licences.csv`](../tables/datasets_sources_licences.csv).

Le principe retenu est que ce dépôt **ne redistribue aucun produit de tiers**. Il
publie les résultats calculés à partir d'eux — taux de recouvrement, aires sous
la courbe, décomptes d'accord —, ce qui ne constitue pas une rediffusion des
produits eux-mêmes. Les quatre fichiers extérieurs qui figuraient dans
`raw/produits_tiers/` en ont donc été retirés, et
[le fichier de lecture de ce dossier](raw/produits_tiers/README.md) renvoie
maintenant chacun à sa source : le registre d'effondrements à
[crisisvenezuela.org](https://crisisvenezuela.org), les trois fichiers
`nwcaracas_*` du produit DISHA — UNOPS et UN Global Pulse — à
[disha.unglobalpulse.org](https://disha.unglobalpulse.org).

Deux entrées de la table appellent une réserve explicite. Les conditions de
réutilisation du produit **UNGSC** y sont indiquées comme *à établir auprès du
producteur* : le dépôt n'en rediffuse aucune donnée, mais des résultats calculés
à partir de ce produit figurent bien dans les tables de comparaison et dans le
document. Celles du produit **WFP-LIST-CERN** portent la mention *méthodologie en
cours d'affinement*, qui vise la méthode et non la licence.

Les acquisitions Sentinel-1 et Sentinel-2 relèvent des conditions Copernicus, qui
autorisent la redistribution avec la mention *contains modified Copernicus
Sentinel data*. L'imagerie à très haute résolution employée dans les figures
relève de Maxar Open Data, 2026 © Vantor Open Data et 2026 © Planet Open Data,
sous licence CC BY-NC 4.0.
