# Le code

Les 46 scripts de ce dossier calculent l'ensemble des tables de
[`data/results/`](../data/results/). Ils sont publiés dans l'état où ils ont
servi, à trois différences près : l'en-tête de chacun a été ramené à une phrase
décrivant ce qu'il calcule, les chemins absolus ont été déportés dans
[`config.py`](config.py), et les commentaires qui renvoyaient à l'avancement du
travail plutôt qu'au calcul ont été retirés.

## Avant d'exécuter

Les données d'entrée ne sont pas redistribuées ici — voir
[`data/README.md`](../data/README.md) pour ce qui l'est et pourquoi. Trois
racines sont à renseigner dans [`config.py`](config.py) ou par variable
d'environnement : `S1_TSTAT_DONNEES`, `S1_TSTAT_COHERENCE` et
`S1_TSTAT_WHITEHOUSE`.

Les scripts s'exécutent avec les liaisons Python de GDAL/OGR, hors de QGIS ; un
interpréteur d'installation OSGeo4W convient. Aucun n'a besoin de réseau, sauf
le téléchargement facultatif du masque terre dans les deux scripts de
recouvrement.

## Le T-stat lui-même

L'implémentation du test t par pixel n'est pas reproduite dans ce dépôt. Elle
dérive du code publié par Ballinger (2024), diffusé sans licence, ce qui
n'autorise pas sa redistribution ni celle d'un travail dérivé. Le chapitre
[section 2.4 du document](../docs/partie_2/partie_2.md) en donne la formulation complète, les
paramètres employés et chacun des écarts entre le code évalué ici et la méthode
publiée — de quoi réécrire l'un ou l'autre sans le recopier.

## Ce que chaque script calcule


### Les méthodes

| script | ce qu'il calcule | tables produites |
|---|---|---|
| [`dpm1_deux_resolutions.py`](methods/dpm1_deux_resolutions.py) | Reproduction de la première méthode de cohérence publiée, calculée en parallèle sur deux résolutions — traitement par rafales à 20 m et scène entière à 40 m rééchantillonnée à 30 m — pour mesurer l'effet de la résolution sur le classement. | [`dpm1_burst_20m_resultats.csv`](../data/results/dpm1_burst_20m_resultats.csv), [`dpm1_fullscene_40mto30m_resultats.csv`](../data/results/dpm1_fullscene_40mto30m_resultats.csv) |
| [`dpm1_methode1_burst20m.py`](methods/dpm1_methode1_burst20m.py) | Reproduction de la première méthode de cohérence publiée sur les produits par rafales à 20 m : construction du raster, recherche du paramétrage contre la vérité de référence, puis projection des meilleurs paramètres sur tous les bâtiments. | [`dpm1_methode1_burst20m_resultats.csv`](../data/results/dpm1_methode1_burst20m_resultats.csv) |
| [`dpm1_methode2_fullscene30m.py`](methods/dpm1_methode2_fullscene30m.py) | Reproduction de la première méthode de cohérence publiée sur les produits scène entière à 40 m rééchantillonnés à 30 m, la paire antérieure la plus proche de l'événement étant retenue. | [`dpm1_methode2_fullscene30m_resultats.csv`](../data/results/dpm1_methode2_fullscene30m_resultats.csv) |
| [`dpm2_a_enveloppe.py`](methods/dpm2_a_enveloppe.py) | Reproduction de la seconde méthode de cohérence publiée dans sa variante en enveloppe simple, sans correction de tendance : empilement de toutes les paires antérieures, puis recherche du paramétrage et projection sur tous les bâtiments. | [`dpm2_A_enveloppe_resultats_complets.csv`](../data/results/dpm2_A_enveloppe_resultats_complets.csv) |

### Les fusions

| script | ce qu'il calcule | tables produites |
|---|---|---|
| [`exp43_fusion_ciblee_coherence.py`](fusion/exp43_fusion_ciblee_coherence.py) | Fusion à deux termes du T-stat d'intensité avec un produit de cohérence interférométrique, mesurée en aire sous la courbe par commune contre deux vérités de référence, sur l'emprise commune aux termes fusionnés. | [`exp43_fusion_ciblee_coherence.csv`](../data/results/exp43_fusion_ciblee_coherence.csv) |
| [`fusion_tstat_coevent_filtre_osu.py`](fusion/fusion_tstat_coevent_filtre_osu.py) | Fusion par conjonction du T-stat avec la cohérence co-événement, et effet d'un filtre de confiance emprunté au produit OSU — la valeur qu'il publie, non une reproduction de sa méthode. | [`fusion_tstat_coevent_filtre_osu.csv`](../data/results/fusion_tstat_coevent_filtre_osu.csv) |
| [`fusion_tstat_eos.py`](fusion/fusion_tstat_eos.py) | Fusion du T-stat avec le produit EOS-RS continu, en faisant varier les deux seuils en conjonction et en testant une pondération continue entre les deux termes. | [`fusion_tstat_eos.csv`](../data/results/fusion_tstat_eos.csv) |
| [`fusion_tstat_osu.py`](fusion/fusion_tstat_osu.py) | Fusion par conjonction du T-stat avec le produit de cohérence OSU, par inclusion progressive des niveaux de confiance et contre trois définitions du positif ; produit le meilleur kappa, le meilleur F1, et le seuil qui minimise les faux positifs à rappel garanti. | [`fusion_tstat_osu.csv`](../data/results/fusion_tstat_osu.csv) |

### L'évaluation

| script | ce qu'il calcule | tables produites |
|---|---|---|
| [`02_admin3_stats_coverage.py`](evaluation/02_admin3_stats_coverage.py) | Statistiques par unité administrative de niveau 3 — surface urbaine, nombre de bâtiments, population, mouvement de sol — et part de chaque unité couverte par l'emprise d'analyse de chaque produit de dommage. | [`admin3_stats.csv`](../data/results/admin3_stats.csv) |
| [`03_overlap_matrix_layers.py`](evaluation/03_overlap_matrix_layers.py) | Matrice de recoupement entre les emprises d'analyse des produits, deux à deux, et couches des zones couvertes par au moins N produits, calculées sur une grille raster commune plutôt que par superposition vectorielle. | [`matrice_recoupement_sources.csv`](../data/results/matrice_recoupement_sources.csv) |
| [`admin3_mmi_bins-allcems.py`](evaluation/admin3_mmi_bins-allcems.py) | Comptage du bâti, de la population et de la surface urbaine par unité administrative de niveau 3 et par tranche d'intensité macrosismique MMI, sur l'emprise complète de l'activation Copernicus EMS. | [`AllCEMS_admin3_mmi_bins.csv`](../data/results/AllCEMS_admin3_mmi_bins.csv), [`admin3_mmi_bins.csv`](../data/results/admin3_mmi_bins.csv) |
| [`admin3_mmi_bins.py`](evaluation/admin3_mmi_bins.py) | Comptage du bâti, de la population et de la surface urbaine par unité administrative de niveau 3 et par tranche d'intensité macrosismique MMI, sur l'emprise effectivement analysée. | [`admin3_mmi_bins.csv`](../data/results/admin3_mmi_bins.csv) |
| [`admin3_stats_aoi_mmi_groundmovement-cemsaoi.py`](evaluation/admin3_stats_aoi_mmi_groundmovement-cemsaoi.py) | Tableau des unités administratives de niveau 3 contenues dans l'emprise Copernicus EMS, avec bâti, surface urbaine, déplacement InSAR maximal et intensité MMI maximale. | [`CEMS_admin3_dans_aoi.csv`](../data/results/CEMS_admin3_dans_aoi.csv) |
| [`admin3_stats_aoi_mmi_groundmovement-cemsaoiv2.py`](evaluation/admin3_stats_aoi_mmi_groundmovement-cemsaoiv2.py) | Même tableau, rapporté à l'emprise effectivement analysée par Copernicus EMS, le rattachement de chaque unité de niveau 3 à son unité parente étant explicite. | [`CEMS_admin3_dans_aoi.csv`](../data/results/CEMS_admin3_dans_aoi.csv) |
| [`admin3_stats_aoi_mmi_groundmovement.py`](evaluation/admin3_stats_aoi_mmi_groundmovement.py) | Tableau des unités administratives de niveau 3 contenues dans une emprise donnée, avec bâti, surface urbaine, déplacement InSAR maximal et intensité MMI maximale. | [`CEMSALL_admin3_dans_aoi.csv`](../data/results/CEMSALL_admin3_dans_aoi.csv) |
| [`admin3_unifie_mmi_dommages.py`](evaluation/admin3_unifie_mmi_dommages.py) | Tranches d'intensité MMI et comptages de dommages par produit calculés dans un seul passage, afin que les deux analyses portent sur exactement le même périmètre, le même fichier de bâti et la même sélection d'unités administratives. | [`admin3_dommages_nuages.csv`](../data/results/admin3_dommages_nuages.csv), [`admin3_mmi_bins.csv`](../data/results/admin3_mmi_bins.csv) |
| [`admin3_unifie_mmi_dommages_v2.py`](evaluation/admin3_unifie_mmi_dommages_v2.py) | Même calcul unifié que la version précédente, avec la séparation des zones couvertes et non couvertes par les nuages et un comptage par produit étendu. | [`admin3_dommages_nuages.csv`](../data/results/admin3_dommages_nuages.csv), [`admin3_dommages_nuagesv3.csv`](../data/results/admin3_dommages_nuagesv3.csv), [`admin3_mmi_bins.csv`](../data/results/admin3_mmi_bins.csv), [`admin3_mmi_binsv3.csv`](../data/results/admin3_mmi_binsv3.csv) |
| [`analyse_complete_multi_gt.py`](evaluation/analyse_complete_multi_gt.py) | Balayage complet des seuils et des règles d'agrégation contre deux vérités de référence, chacune restreinte à sa propre emprise d'analyse : un bâtiment situé hors de l'emprise d'une source n'est pas un vrai négatif pour elle, c'est une absence de donnée. | [`analyse_complete_multi_gt.csv`](../data/results/analyse_complete_multi_gt.csv) |
| [`analyse_complete_seuils.py`](evaluation/analyse_complete_seuils.py) | Balayage des seuils de 0 à 6 et de toutes les règles d'agrégation du pixel au bâtiment, à trois niveaux de portée : global, zones côtières, et zone par zone. | [`analyse_complete_seuils.csv`](../data/results/analyse_complete_seuils.csv) |
| [`analyse_complete_seuils_ems.py`](evaluation/analyse_complete_seuils_ems.py) | Balayage des seuils de 0 à 6 et de toutes les règles d'agrégation du pixel au bâtiment, contre la vérité Copernicus EMS, à trois niveaux de portée : global, zones côtières, et zone par zone. | [`analyse_complete_seuils.csv`](../data/results/analyse_complete_seuils.csv) |
| [`aoi_couverture_et_etapes.py`](evaluation/aoi_couverture_et_etapes.py) | Recouvrement réel de chaque zone de référence par l'emprise d'analyse de chaque produit, puis construction des emprises communes par inclusion progressive des produits, du mieux couvrant au moins couvrant. | [`aoi_communes_etapes.csv`](../data/results/aoi_communes_etapes.csv), [`aoi_couverture_reelle.csv`](../data/results/aoi_couverture_reelle.csv), [`fusion_tstat_eos.csv`](../data/results/fusion_tstat_eos.csv) |
| [`cems_admin3_comptage_dommages_nuages.py`](evaluation/cems_admin3_comptage_dommages_nuages.py) | Comptage des bâtiments endommagés et détruits par unité administrative de niveau 3, en séparant les zones où la couverture nuageuse a empêché l'analyse optique, afin de mesurer l'apport propre des produits radar. | [`CEMS_admin3_comptage_dommages_nuages.csv`](../data/results/CEMS_admin3_comptage_dommages_nuages.csv) |
| [`comparaison_sources_vs_ems.py`](evaluation/comparaison_sources_vs_ems.py) | Kappa, précision et rappel de chaque produit contre la vérité Copernicus EMS, bâtiment par bâtiment sur un identifiant d'empreinte partagé, et non par comptage indépendant dans une même zone. | [`comparaison_sources_vs_ems.csv`](../data/results/comparaison_sources_vs_ems.csv) |
| [`comptage_par_classe_par_zone.py`](evaluation/comptage_par_classe_par_zone.py) | Comptage par classe de dommage dans le vocabulaire natif de chaque produit, sur ses géométries d'origine et non reprojetées, réparti par zone d'analyse. | [`comptage_par_classe_par_zone.csv`](../data/results/comptage_par_classe_par_zone.csv) |
| [`comptage_par_classe_par_zone_aoi_cems.py`](evaluation/comptage_par_classe_par_zone_aoi_cems.py) | Même comptage par classe native, restreint à l'emprise de l'activation Copernicus EMS. | [`comptage_par_classe_par_zone.csv`](../data/results/comptage_par_classe_par_zone.csv), [`comptage_par_classe_par_zone_EMSR884_aoi.csv`](../data/results/comptage_par_classe_par_zone_EMSR884_aoi.csv) |
| [`dommages_par_zone_aoi_directe.py`](evaluation/dommages_par_zone_aoi_directe.py) | Comptage des dommages par zone d'analyse par jointure spatiale directe, sans passer par les unités administratives. | [`dommages_par_zone_aoi_directe.csv`](../data/results/dommages_par_zone_aoi_directe.csv) |
| [`exp42_aoi_commun.py`](evaluation/exp42_aoi_commun.py) | Classement des produits de dommage sur l'emprise strictement commune, en aire sous la courbe par commune contre deux vérités de référence, avec trois lectures : l'emprise commune aux produits à large couverture, le face-à-face par paire, et l'intersection stricte des douze produits. | [`exp42_aoi_commun_face_a_face.csv`](../data/results/exp42_aoi_commun_face_a_face.csv), [`exp42_aoi_commun_intersection.csv`](../data/results/exp42_aoi_commun_intersection.csv) |
| [`jamaique_evaluation_tstat.py`](evaluation/jamaique_evaluation_tstat.py) | Évaluation du raster T-stat sur le cas cyclonique : quatre règles d'agrégation par bâtiment, deux sources d'empreintes et deux vérités de référence, sans jamais recalculer le raster. | [`jamaique_seuils_tstat_agregations.csv`](../data/results/jamaique_seuils_tstat_agregations.csv) |
| [`mmi_source_comptage_coherence.py`](evaluation/mmi_source_comptage_coherence.py) | Comptage des dommages par tranche d'intensité MMI et par produit, puis vérification que le taux de dommage de chaque produit croît bien avec l'intensité sismique. | [`mmi_coherence_analyse.csv`](../data/results/mmi_coherence_analyse.csv), [`mmi_source_comptage.csv`](../data/results/mmi_source_comptage.csv) |
| [`recouvrement_aoi_par_source.py`](evaluation/recouvrement_aoi_par_source.py) | Part de chaque zone de référence couverte par l'emprise d'analyse propre à chaque produit, en traitant les quatre formes sous lesquelles cette emprise est publiée. | [`recouvrement_aoi_par_source.csv`](../data/results/recouvrement_aoi_par_source.csv) |
| [`recouvrement_aoi_par_sourcevs_ems.py`](evaluation/recouvrement_aoi_par_sourcevs_ems.py) | Même calcul de recouvrement, rapporté aux unités administratives effectivement analysées par Copernicus EMS. | [`recouvrement_aoi_par_source.csv`](../data/results/recouvrement_aoi_par_source.csv), [`recouvrement_aoi_par_source_VS_REALadmin3_EMS.csv`](../data/results/recouvrement_aoi_par_source_VS_REALadmin3_EMS.csv) |
| [`seuil_balayage_3classes.py`](evaluation/seuil_balayage_3classes.py) | Recherche du meilleur couple de seuils pour classer chaque bâtiment en trois niveaux — intact, endommagé, détruit — au lieu du partage binaire habituel. | [`seuilOSM_balayage_3classes.csv`](../data/results/seuilOSM_balayage_3classes.csv) |
| [`seuil_balayage_chatmap.py`](evaluation/seuil_balayage_chatmap.py) | Recherche de la meilleure combinaison de raster, de règle d'agrégation et de seuil contre la vérité issue du signalement participatif, sur les empreintes de la base collaborative. | — |
| [`seuil_balayage_chatmap_osu.py`](evaluation/seuil_balayage_chatmap_osu.py) | Recherche de la meilleure combinaison de raster, de règle d'agrégation et de seuil contre la vérité issue du signalement participatif. | [`seuil_balayage_chatmap_OSU_EOS_BDPM.csv`](../data/results/seuil_balayage_chatmap_OSU_EOS_BDPM.csv) |
| [`seuil_balayage_ems.py`](evaluation/seuil_balayage_ems.py) | Recherche de la meilleure combinaison de raster, de règle d'agrégation et de seuil contre la vérité Copernicus EMS. | [`seuil_balayage_EMS_OSU_EOS_BDPM.csv`](../data/results/seuil_balayage_EMS_OSU_EOS_BDPM.csv) |
| [`seuil_balayage_par_zone.py`](evaluation/seuil_balayage_par_zone.py) | Balayage seuil par règle d'agrégation, zone par zone et sur deux sources d'empreintes en un seul passage, la zone de chaque bâtiment étant déterminée par jointure spatiale réelle avec la couche d'emprise. | [`seuil_balayage_par_zone_multisource.csv`](../data/results/seuil_balayage_par_zone_multisource.csv) |
| [`seuils_asc_desc_complet.py`](evaluation/seuils_asc_desc_complet.py) | Analyse des seuils avec mosaïquage automatique des rafales co-événement et trois règles de combinaison des orbites ascendantes et descendantes par bâtiment. | [`seuils_asc_desc_complet.csv`](../data/results/seuils_asc_desc_complet.csv) |
| [`seuils_par_zone_et_gt.py`](evaluation/seuils_par_zone_et_gt.py) | Analyse des seuils du T-stat, de la cohérence et de leur conjonction, zone par zone et globalement, sous trois définitions du positif. | [`seuils_par_zone_et_gt.csv`](../data/results/seuils_par_zone_et_gt.csv) |
| [`stats_par_zone_cloud.py`](evaluation/stats_par_zone_cloud.py) | Population, nombre de bâtiments selon quatre bases d'empreintes, surface totale et surface urbaine de chaque zone, déclinées en zones couvertes par les nuages, non couvertes, et total. | [`stats_par_zone_cloud.csv`](../data/results/stats_par_zone_cloud.csv) |
| [`toutes_sources_vs_ems_etapes.py`](evaluation/toutes_sources_vs_ems_etapes.py) | Comparaison de tous les produits contre la vérité Copernicus EMS sur des emprises communes construites par inclusion progressive, du produit le mieux couvrant au moins couvrant. | [`fusion_tstat_eos.csv`](../data/results/fusion_tstat_eos.csv), [`toutes_sources_vs_ems_etapes.csv`](../data/results/toutes_sources_vs_ems_etapes.csv) |
| [`toutes_sources_vs_ems_etapes_overture.py`](evaluation/toutes_sources_vs_ems_etapes_overture.py) | Même comparaison par inclusion progressive, tous les produits étant au préalable reprojetés sur une base d'empreintes unique. | [`fusion_tstat_eos.csv`](../data/results/fusion_tstat_eos.csv), [`toutes_sources_vs_ems_etapes.csv`](../data/results/toutes_sources_vs_ems_etapes.csv) |
| [`whitehouse_coherence_et_seuils.py`](evaluation/whitehouse_coherence_et_seuils.py) | Accord entre deux vérités de référence indépendantes sur grille hexagonale, restreint à l'intersection de leurs emprises d'analyse, puis recherche du seuil optimal du T-stat contre chacune d'elles séparément. | [`whitehouse_coherence_unosat_ems_h3.csv`](../data/results/whitehouse_coherence_unosat_ems_h3.csv) |
| [`whitehouse_h3_coherence_via_batiments.py`](evaluation/whitehouse_h3_coherence_via_batiments.py) | Accord entre deux vérités de référence sur grille hexagonale, l'univers de référence étant l'ensemble des empreintes de bâtiments et non les seuls points de dommage, ce qui rend possible l'existence de cellules non endommagées. | [`whitehouse_coherence_unosat_ems_h3.csv`](../data/results/whitehouse_coherence_unosat_ems_h3.csv), [`whitehouse_coherence_unosat_ems_h3_via_batiments.csv`](../data/results/whitehouse_coherence_unosat_ems_h3_via_batiments.csv) |
| [`zone_mmi_repartition.py`](evaluation/zone_mmi_repartition.py) | Surface de chaque zone d'analyse répartie par tranche d'intensité macrosismique MMI. | [`zone_mmi_repartition.csv`](../data/results/zone_mmi_repartition.csv) |

### La préparation

| script | ce qu'il calcule | tables produites |
|---|---|---|
| [`build_couches_finales_overture.py`](preprocessing/build_couches_finales_overture.py) | Documente le seuil et les poids retenus pour chaque combinaison de méthode et de portée, puis projette ces paramètres sur l'ensemble des bâtiments pour produire les couches finales. | [`reference_parametres.csv`](../data/results/reference_parametres.csv) |
| [`exp63_inventaire_paires_coherence.py`](preprocessing/exp63_inventaire_paires_coherence.py) | Inventaire consolidé des paires interférométriques employées pour les calculs de cohérence, rassemblées depuis cinq fichiers de schémas différents en un tableau unique portant le nom de zone de chaque paire. | [`image_pairs.csv`](../data/results/image_pairs.csv), [`image_pairs2.csv`](../data/results/image_pairs2.csv) |

### Les tables que le tableau ci-dessus ne relie pas

Onze des soixante-quatre tables de [`data/results/`](../data/results/) ne
portent pas le nom qu'un script publié déclare écrire. Deux raisons, et aucune
n'est un trou dans la traçabilité — mais elles ne se valent pas, et le lecteur a
le droit de savoir laquelle s'applique.

Cinq fichiers qui étaient rangés ici sans être des calculs de cette étude ont
été remontés dans [`data/raw/produits_tiers/`](../data/raw/produits_tiers/), où
leur nature de données d'entrée est explicite. Un brouillon abandonné a été
retiré.

**Une famille de scripts publiée ici, exécutée sous une autre configuration.**
Le nom de sortie déclaré dans le script a changé depuis la campagne qui a produit
la table ; les colonnes, elles, coïncident exactement, ce qui identifie la
famille sans ambiguïté. Chaque script de ces familles ne diffère de ses voisins
que par l'emprise ou le fichier de bâti pointé en tête de son bloc
`CONFIGURATION`.

| table | famille qui l'a produite |
|---|---|
| `comptage_par_classe_par_zone_all_cems_aoi.csv` | [`comptage_par_classe_par_zone*.py`](evaluation/) |
| `recouvrement_aoi_par_source_VS_ALL_EMS.csv` | [`recouvrement_aoi_par_source*.py`](evaluation/) |
| `recouvrement_aoi_par_source_VS_REAL_EMS.csv` | [`recouvrement_aoi_par_source*.py`](evaluation/) |
| `seuil_balayage_chatmap_osm.csv` | [`seuil_balayage_*.py`](evaluation/) |
| `reference_parametres_1.csv` | [`build_couches_finales_overture.py`](preprocessing/build_couches_finales_overture.py) |
| `toutes_sources_vs_ems_etapes_justemymethod.csv` | [`toutes_sources_vs_ems_etapes*.py`](evaluation/) — colonnes identiques, seul le séparateur diffère |
| `CEMS_admin3_mmi_fusionne.csv` | [`admin3_unifie_mmi_dommages*.py`](evaluation/) — les colonnes de `CEMS_admin3_dans_aoi.csv` plus `aoi_zone` |
| `CEMSALL_admin3_mmi_fusionne.csv` | [`admin3_unifie_mmi_dommages*.py`](evaluation/), sur l'emprise complète de l'activation |

**Origine non retrouvée.** Pour ces trois tables, aucun script conservé ne
déclare ni ce nom de sortie ni ce jeu de colonnes. Elles ne portent aucun chiffre
cité dans l'article et sont conservées uniquement parce qu'un inventaire amputé
de ce qu'il ne sait pas expliquer ne vaut rien.

| table | remarque |
|---|---|
| `comparaison_agregee.csv` | agrégation par classe normalisée, postérieure à `comparaison_sources_vs_ems.csv` |
| `jamaique_agregations_detail.csv` | étude d'agrégation sur le cas cyclonique, employée par le carnet 02 |
| `jamaique_agregations_strat.csv` | même étude, stratifiée par nombre de pixels par bâtiment |

