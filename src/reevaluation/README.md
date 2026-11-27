# La réévaluation du 1er octobre 2026

Ce dossier porte les programmes d'une seule séance de travail, celle qui a
repris les résultats de délai, de fenêtre et d'agrégation sous **une
configuration et une convention d'évaluation uniques**.

## Ce qui a changé ce jour-là

Les premières versions des figures 5, 6 et 7 avaient été calculées avec le test
de Welch et les orbites combinées par somme de Stouffer, puis évaluées sur
OpenStreetMap, les signalements étant rattachés aux empreintes par accrochage à
vingt mètres du centroïde. Ce n'était ni la configuration de l'outil, ni la
convention d'évaluation retenue dans l'étude — deux conventions coexistaient
donc dans le même document.

Tout a été refait avec :

| réglage | valeur |
|---|---|
| test multi-images | variance regroupée |
| combinaison des orbites | maximum |
| couche bâtie | Open Buildings en Jamaïque, Overture au Venezuela |
| appariement | règle stricte, sans doublon |
| emprises retenues | prévalence comprise entre 5 et 95 % |
| période de référence | 12 mois |

## La chaîne, et pourquoi elle est en deux temps

Un programme **calcule** des cartes de score depuis Earth Engine ; un autre les
**réévalue** sans les recalculer. La séparation n'est pas cosmétique : elle
permet de changer de couche bâtie ou de règle d'appariement sans refaire des
heures de calcul radar, et c'est exactement ce qui a été fait le 1er octobre.

    exp77_une_image_regroupee.py  ──>  cartes  ──>  exp80_reevaluer_exp77.py  ──>  figures 5 et 7
    exp78_fenetre_pre_regroupee.py ─>  cartes  ──>  exp81_reevaluer_exp78.py  ──>  figure 6
    exp73_venezuela.py            ──>  cartes  ──>  exp73_evaluation.py       ──>  exp73_detail.csv
    exp82_nepal_calcul.py         ──>  cartes  ──>  exp82_nepal_evaluation.py ──>  exp82_nepal.csv

`exp74_croisement_campagnes.py`, `exp75_tout_reevaluer.py` et
`exp79_tableau_annexe_L.py` ne lisent que des tables déjà écrites.
`exp83_nepal_route_signature.py`, `exp83b_serie_vv.py` et
`exp86_serie_piste_ensevelie.py` extraient directement des séries temporelles
depuis Earth Engine : ce sont les deux courbes de la figure 17.

## Ce qu'il faut pour les exécuter

Le détail de chaque programme est dans [`../README.md`](../README.md). Trois
conditions s'ajoutent à celles des autres dossiers :

- **les racines de données** `S1_TSTAT_TRAVAUX`, `S1_TSTAT_REEVALUATION` et
  `S1_TSTAT_MODULES`, déclarées dans [`../config.py`](../config.py) ;
- **un accès Earth Engine** pour les quatre programmes de calcul et les trois
  programmes de série temporelle. Le projet employé est déclaré en tête de
  chacun (`PROJET_GEE`) ; il faut y substituer le vôtre ;
- **le module du test t**, que `S1_TSTAT_MODULES` doit pointer. Il n'est pas
  redistribué ici : il dérive d'un code publié sans licence l'autorisant. Les
  programmes de calcul ne s'exécutent donc pas en l'état. Voir la section
  « À propos du test t » du [README](../../README.md) du dépôt, qui donne la
  formulation et les paramètres nécessaires pour le réécrire.

Les programmes de réévaluation (`exp7x_reevaluer_*`, `exp73_evaluation`,
`exp75`, `exp79`, `exp82_nepal_evaluation`) n'ont besoin ni d'Earth Engine ni de
ce module : ils relisent des cartes déjà écrites.

## Ce qui a été modifié à la publication

Comme les autres programmes du dépôt, ceux-ci sont publiés dans l'état où ils
ont servi, à une différence près : les chemins absolus ont été remplacés par les
racines de [`../config.py`](../config.py). Les modules partagés
`evaluation_commune.py` et `appariement.py` ont été remontés dans
[`../`](../), d'où tous les programmes les importent désormais.
