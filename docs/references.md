# Bibliographie

Les références sont regroupées par rôle plutôt que par ordre alphabétique : ce
qui compte, pour un lecteur qui veut vérifier, est de savoir quelle référence
fonde quelle affirmation. La page d'accueil n'en cite que cinq ; celles-ci
portent l'ensemble du raisonnement des chapitres.

---

## La méthode évaluée

**Ballinger, O.** (2025). Open access battle damage detection via Pixel-Wise
T-Test on Sentinel-1 imagery. *Remote Sensing of Environment*, 331, 115025.
<https://doi.org/10.1016/j.rse.2025.115025>

> La méthode reproduite et évaluée ici. Son équation (3) rapporte chaque
> variance à son propre effectif et son équation (4) combine les orbites par
> maximum ; le code diffusé avec l'article calcule, lui, une variance
> regroupée. La section 4.3 expose ce point.

**Ballinger, O.** (2024). *PWTT: Pixel-Wise T-Test for battle damage detection*
[Logiciel]. <https://github.com/oballinger/PWTT>

> Le code de référence. Diffusé sans licence, ce qui n'autorise pas sa
> redistribution : ce dépôt en donne la formulation, pas le code.

**Salaheldin, A.** (2026). *PWTT QGIS Plugin: Pixel-Wise T-Test for building
damage detection* [Logiciel]. Dépôt officiel des greffons QGIS.
<https://plugins.qgis.org/plugins/pwtt_qgis/>

**Student** (1908). The Probable Error of a Mean. *Biometrika*, 6(1), 1–25.
<https://doi.org/10.2307/2331554>

**Welch, B. L.** (1947). The generalization of Student's problem when several
different population variances are involved. *Biometrika*, 34(1-2), 28–35.
<https://doi.org/10.1093/biomet/34.1-2.28>

> Les deux formulations comparées en section 4.3. Welch ne suppose pas
> l'égalité des variances, ce que la configuration employée ici — une
> trentaine d'images de référence contre cinq postérieures — interdit en
> principe de supposer ; la comparaison empirique ne départage pourtant pas
> les deux formes.

---

## Les méthodes de cohérence interférométrique reproduites

**Jung, J., Yun, S.-H., Kim, D.-J., & Lavalle, M.** (2018). Damage-Mapping
Algorithm Based on Coherence Model Using Multitemporal
Polarimetric-Interferometric SAR Data. *IEEE Transactions on Geoscience and
Remote Sensing*, 56(3), 1520–1532.
<https://doi.org/10.1109/TGRS.2017.2764748>

**Liu, H.** (2024). A New Method for the Identification of Earthquake-Damaged
Buildings Using Sentinel-1 Multitemporal Coherence Optimized by Homogeneous SAR
Pixels and Histogram Matching. *IEEE Journal of Selected Topics in Applied
Earth Observations and Remote Sensing*.
<https://ieeexplore.ieee.org/document/10472520>

> La méthode désignée BDPM dans ce travail, reproduite depuis ses formules et
> évaluée au chapitre 7. Sa sortie binaire publiée obtient 0,462, sous le
> hasard, ce qui mesure le coût du passage d'un score continu à une déclaration.

**O'Donnell, T. M., Zimmaro, P., Fielding, E. J., & Stewart, J. P.** (2025).
Quantitative validation of NASA ARIA damage proxy maps for detection of ground
displacement from surface fault rupture from the 2019 Ridgecrest earthquake
sequence. *Earthquake Spectra*, 41(5).
<https://doi.org/10.1177/87552930251377727>

> Les méthodes désignées DPM1 et DPM2, reproduites depuis leurs formules.

**Scher, C., & Van Den Hoek, J.** (2025). Nationwide conflict damage mapping
with interferometric synthetic aperture radar: A study of the 2022
Russia-Ukraine conflict. *Science of Remote Sensing*, 11, 100217.
<https://doi.org/10.1016/j.srs.2025.100217>

**Scher, C., & Van Den Hoek, J.** (2025). *Active InSAR monitoring of building
damage in Gaza during the Israel-Hamas War*. arXiv:2506.14730.
<https://arxiv.org/abs/2506.14730>

**Scher, C., & Van Den Hoek, J.** (2026). *Building Damage Assessment Portal —
Open Access Satellite Conflict Damage Data*.
<https://damage.conflict-ecology.org/>

> La méthode du produit OSU, partenaire de la fusion ciblée, et le portail qui
> en diffuse les résultats. La notice du produit employé ici est décrite dans
> [l'annexe « Dictionnaire des méthodes »](partie_2/partie_2.md#annexe--dictionnaire-des-méthodes-de-cartographie-des-dommages).

---

## L'évaluation des dommages par radar : revues et cas

**Ge, P., Gokon, H., & Meguro, K.** (2020). A review on synthetic aperture
radar-based building damage assessment in disasters. *Remote Sensing of
Environment*, 240, 111693. <https://doi.org/10.1016/j.rse.2020.111693>

**Plank, S.** (2014). Rapid Damage Assessment by Means of Multi-Temporal SAR —
A Comprehensive Review and Outlook to Sentinel-1. *Remote Sensing*, 6(6),
4870–4906. <https://doi.org/10.3390/rs6064870>

**Wang, X., Feng, G., He, L., An, Q., Xiong, Z., Lu, H., Wang, W., Li, N.,
Zhao, Y., Wang, Y., & Wang, Y.** (2023). Evaluating Urban Building Damage of
2023 Kahramanmaraş, Turkey Earthquake Sequence Using SAR Change Detection.
*Sensors*, 23(14), 6342. <https://doi.org/10.3390/s23146342>

**Dietrich, O., Peters, T., Sainte Fare Garnot, V., Sticher, V.,
Ton-That Whelan, T., Schindler, K., & Wegner, J. D.** (2025). An open-source
tool for mapping war destruction at scale in Ukraine using Sentinel-1 time
series. *Communications Earth & Environment*.
<https://doi.org/10.1038/s43247-025-02183-7>

---

## Ce que valent les données de référence

**Ainscoe, E. A., Swaminathan, R., Way, L., Modugno, S., Chin, S. T., Panta, N.,
Crevoisier, T., & Yun, S.-H.** (2025). Earthquake damage mapped more
comprehensively and accurately by radar satellites than optical imagery.
*Communications Earth & Environment*, 6, 631.
<https://www.nature.com/articles/s43247-025-02623-4>

> La comparaison radar/optique contre deux millions de bâtiments inspectés porte
> à porte après Kahramanmaraş 2023 : rappel de 0,59 pour le radar contre 8 à
> 17 % pour l'optique, et une couverture de 100 % contre 5,4 % en dix jours.

**Cotrufo, S., Sandu, C., Giulio Tonolo, F., & Boccardo, P.** (2018). Building
damage assessment scale tailored to remote sensing vertical imagery. *European
Journal of Remote Sensing*, 51(1), 991–1005.
<https://doi.org/10.1080/22797254.2018.1527662>

> L'échelle de gradation employée par la cartographie rapide, et sa mesure
> contre un levé par drone sur Amatrice 2016 : 42 % d'exactitude de
> l'utilisateur pour *aucun dommage visible*, 28 % pour *possiblement
> endommagé*, contre 100 % pour *détruit*. La référence de la section 9.3.

**Saito, K., Spence, R. J. S., Going, C., & Markus, M.** (2004). Using
High-Resolution Satellite Images for Post-Earthquake Building Damage
Assessment: A Study following the 26 January 2001 Gujarat Earthquake.
*Earthquake Spectra*, 20(1), 145–169. <https://doi.org/10.1193/1.1650865>

**Ehrlich, D., Guo, H., Molch, K., Ma, J., & Pesaresi, M.** (2009). Identifying
damage caused by the 2008 Wenchuan earthquake from VHR remote sensing data.
*International Journal of Digital Earth*, 2(4), 309–326.
<https://doi.org/10.1080/17538940902767401>

**Manzini, T., Perali, P., Tripathi, J., & Murphy, R.** (2025). *Now you see
it, Now you don't: Damage Label Agreement in Drone & Satellite Post-Disaster
Imagery*. arXiv:2505.08117. <https://arxiv.org/abs/2505.08117>

**Manzini, T., Perali, P., Karnik, R., & Murphy, R.** (2024).
*CRASAR-U-DROIDs: A Large Scale Benchmark Dataset for Building Alignment and
Damage Assessment in Georectified sUAS Imagery*. arXiv:2407.17673.
<https://arxiv.org/abs/2407.17673>

> Le désaccord entre annotations sur imagerie drone et sur imagerie satellite,
> mesuré : un rappel utile lorsqu'on emploie l'une pour valider l'autre.

**Westrope, C., Banick, R., & Levine, M.** (2014). Groundtruthing
OpenStreetMap Building Damage Assessment. *Procedia Engineering*, 78, 29–39.
<https://doi.org/10.1016/j.proeng.2014.07.035>

**Westrope, C., Banick, R., & Levine, M.** (2014). *Groundtruthing
OpenStreetMap Damage Assessment Review — Interim Report*. REACH Initiative /
ACTED et Croix-Rouge américaine, avec le soutien de l'USAID-OFDA.
<https://americanredcross.github.io/OSM-Assessment/>

---

## Mesure et indicateurs

**Feinstein, A. R., & Cicchetti, D. V.** (1990). High agreement but low kappa:
I. The problems of two paradoxes. *Journal of Clinical Epidemiology*, 43(6),
543–549.

> La raison pour laquelle le kappa, présent dans plusieurs tables de résultats,
> ne porte aucune conclusion de ce travail : il dépend de la prévalence, ce qui
> interdit de comparer deux zones de sinistralité différente.

**Worden, C. B., Wald, D. J., Allen, T. I., Lin, K., Garcia, D., & Cua, G.**
(2012). Probabilistic relationship between ground-motion parameters and
modified Mercalli intensity in California. *Bulletin of the Seismological
Society of America*, 102(1), 204–221.

> Les seuils de tranches d'intensité macrosismique employés dans les
> agrégations par unité administrative.

---

## Réseau routier et cohérence en milieu urbain

**Karimzadeh, S., et al.** (2022). Évaluation de dommages routiers par SAR sur le
séisme de Kumamoto, validée au sol par 530 km de mesures d'indice
d'uni (IRI) relevées par accéléromètre embarqué ; perceptron multicouche
combinant intensité et cohérence, 87,1 % d'exactitude en classement binaire.

> **Référence à compléter.** Cette étude est citée dans le corps du texte
> comme la seule validation au sol identifiée sur le réseau routier. Ses
> éléments bibliographiques complets — revue, volume, DOI — n'ont pas pu être
> retrouvés dans les catalogues consultés et doivent être vérifiés avant
> soumission.

**Washaya, P., Balz, T., & Mohamadi, B.** (2018). Coherence Change-Detection
with Sentinel-1 for Natural and Anthropogenic Disaster Monitoring in Urban
Areas. *Remote Sensing*, 10(7), 1026. <https://doi.org/10.3390/rs10071026>

> La mesure de perte de cohérence en zone urbaine citée dans l'état de l'art :
> 65 % après séisme, 75 % après ouragan.

**Malmgren-Hansen, D., Sohnesen, T., Fisker, P., & Baez, J.** (2020).
Sentinel-1 Change Detection Analysis for Cyclone Damage Assessment in Urban
Environments. *Remote Sensing*, 12(15), 2409.
<https://doi.org/10.3390/rs12152409>

> L'application de la détection de changement aux dommages cycloniques urbains,
> sans volet routier.

---

## Les sources de données et les produits comparés

Les quatorze produits de cartographie des dommages diffusés après le séisme du
Venezuela de juin 2026 — leur méthode, leurs paramètres et l'adresse de leurs
données — sont décrits dans
[l'annexe « Dictionnaire des méthodes de cartographie des dommages »](partie_2/partie_2.md#annexe--dictionnaire-des-méthodes-de-cartographie-des-dommages).

Les jeux de données d'entrée, leurs licences et les attributions à porter sont
dans [`tables/datasets_sources_licences.csv`](../tables/datasets_sources_licences.csv).
Les statistiques de la Charte internationale Espace et catastrophes majeures
proviennent de ses rapports annuels, <https://disasterscharter.org>, et les
tables de calcul correspondantes sont dans
[`tables/charte_synthese_optique_radar.csv`](../tables/charte_synthese_optique_radar.csv)
et [`tables/charte_images_par_satellite_et_annee.csv`](../tables/charte_images_par_satellite_et_annee.csv).

---

_Les références de cette page sont tenues dans un fichier RIS, qui reste la
source ; cette page en est le rendu lisible. Les deux dernières entrées, sur le
kappa et sur les tranches d'intensité, ont été ajoutées d'après leur citation
standard et méritent une vérification avant soumission._
