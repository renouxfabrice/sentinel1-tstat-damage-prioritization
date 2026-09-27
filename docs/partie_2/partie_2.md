# Évaluation et amélioration par fusion d’une méthode de classement de bâtiments post-catastrophe avec Sentinel-1

**Language / Langue :** 🇬🇧 [English](partie_2.en.md) · 🇫🇷 Français

Cette version longue constitue le volet satellite complet du dépôt GitHub ; elle conserve les développements, résultats et limites qui sont condensés dans la thèse.

Après une catastrophe à déclenchement soudain, l’enjeu opérationnel n’est pas seulement de localiser des dommages, mais de déterminer où vérifier en premier. L’imagerie optique peut être retardée ou limitée par la couverture nuageuse ; Sentinel-1 fournit un signal radar disponible indépendamment de la lumière et des nuages. Ce signal ne montre toutefois pas directement les dommages : il mesure une variation de rétrodiffusion, dont l’interprétation dépend de la géométrie radar, de la structure bâtie et de la nature du changement observé [Ballinger, 2025].

L’étude réimplémente et évalue une approche fondée sur une statistique de changement par pixel, agrégée ensuite à l’échelle des bâtiments. Elle compare ce score à d’autres produits sur des empreintes de bâtiments explicitement harmonisées, reproduit plusieurs méthodes fondées sur la cohérence interférométrique, et teste des fusions de rangs.

Les résultats montrent, sur les deux études de cas seulement, qu’un score Sentinel-1 peut contribuer à prioriser des bâtiments ou secteurs à vérifier. La fusion ciblée améliore l’AUC moyenne de la T-stat seule de 0,740 à 0,764 dans la configuration T-stat × OSU. Cette amélioration est mesurée sur les références et empreintes décrites ici ; elle ne constitue ni une validation générale de la détection de dommages ni une preuve de transférabilité à d’autres catastrophes.


## 1 Analyse de l'existant et problématique

L'évaluation rapide des dommages post-catastrophe repose aujourd'hui largement sur l'interprétation visuelle d'images optiques à très haute résolution. Lorsqu'une image claire, récente et suffisamment détaillée est disponible, l'analyste peut reconnaître directement les formes du bâti, les toitures arrachées, les effondrements, les zones inondées, les glissements de terrain et les débris. Cette capacité de lecture fait de l'imagerie optique la référence pour caractériser les dommages.

Mais cette référence dépend d'une condition qui n'est pas toujours réunie dans les premières heures : disposer d'une image réellement exploitable. Après une catastrophe, l'image peut être absente, acquise trop tard, partiellement couverte de nuages, insuffisamment résolue ou ne pas couvrir le secteur qui doit être analysé. Le problème ne consiste donc pas seulement à obtenir une image. Il consiste à obtenir une image utile au moment où la décision doit être prise.

Cette section examine cette tension entre la qualité de l'interprétation optique et les contraintes de disponibilité qui l'accompagnent. Elle montre ensuite pourquoi le radar peut fournir, non pas une substitution à l'optique, mais une première information de priorisation lorsque les conditions nécessaires à une lecture détaillée ne sont pas encore réunies.

### 1.1 Des mécanismes distincts, une forte place de l'optique

La Charte internationale Espace et catastrophes majeures, Copernicus EMS et UNOSAT sont trois mécanismes distincts. Ils peuvent contribuer à une même crise, mais ils ne disposent pas du même mandat, des mêmes règles d'activation ni des mêmes produits.

La Charte internationale permet à des utilisateurs autorisés de demander une mobilisation coordonnée de ressources spatiales après une catastrophe. Elle met à disposition des données sous conditions d'usage ; il serait donc incorrect de dire qu'elle fournit simplement des images « gratuites ».[^8]

Copernicus EMS est le service européen de cartographie d'urgence. Il produit des cartes et des jeux de données selon des activations et des emprises définies. Les informations issues de l'imagerie sont interprétées et transformées en produits cartographiques utilisables par les acteurs de la réponse.

UNOSAT fournit des analyses géospatiales dans le cadre du système des Nations unies, en produisant notamment des cartes d'impact, des estimations de population exposée et des analyses de dommages pour soutenir la coordination humanitaire.

Ces mécanismes ont un point commun : l'imagerie optique joue un rôle central dans les informations effectivement mobilisées après catastrophe.

Les rapports annuels de la Charte internationale permettent d'observer la répartition entre images optiques et radar sur la période 2020-2024.

| Année | Part optique | Part radar |
|---|---|---|
| 2020 | 78,3 % | 21,7 % |
| 2021 | 59,4 % | 40,6 % |
| 2022 | 77,5 % | 22,5 % |
| 2023 | 87,2 % | 12,8 % |
| 2024 | 85,3 % | 14,7 % |

**Tableau 1 — Répartition des images optiques et radar mobilisées par la Charte internationale entre 2020 et 2024. Source : calculs de l'auteur à partir des données d'activation et d'imagerie de la Charte internationale « Espace et catastrophes majeures », 2020-2024. La période étudiée couvre cinq années seulement ; les variations observées ne permettent pas d'établir une tendance structurelle de long terme.[^9]**

L'optique représente ainsi la majorité des images chaque année. La part radar atteint 40,6 % en 2021, puis descend à 12,8 % en 2023 et 14,7 % en 2024. Entre 2021 et 2023, elle passe d'environ quatre images sur dix à environ une image sur huit.

Cette série ne doit pas être interprétée comme la preuve d'un abandon progressif du radar. Elle porte sur cinq années seulement. Les variations peuvent s'expliquer par la nature des événements activés, leur répartition géographique, la saison, la couverture nuageuse, la disponibilité des capteurs ou les contraintes propres à chaque activation. Elle établit néanmoins un constat robuste pour la période observée : le radar participe à la réponse internationale, mais reste minoritaire parmi les images effectivement mobilisées.

Le détail des acquisitions montre aussi une concentration sur un nombre limité de constellations :

| Satellite | Type | Images 2020-2024 |
|---|---|---|
| WorldView-1/2/3 | Optique | 25 556 |
| PlanetScope | Optique | 12 486 |
| GeoEye-1 | Optique | 6 281 |
| Pléiades 1A/1B | Optique | 5 503 |
| Sentinel-1 (toutes générations) | Radar | 4 695 |

**Tableau 2 — Principaux satellites mobilisés par la Charte internationale, total 2020-2024. Source : calculs de l'auteur à partir des données d'activation et d'imagerie de la Charte internationale « Espace et catastrophes majeures », 2020-2024.**

La disponibilité de l'information dépend donc non seulement de la présence de satellites, mais aussi de la programmation, de l'accès aux données, de la couverture de la zone et des choix de mobilisation effectués lors de chaque crise.

### 1.2 Copernicus EMS : anticiper, acquérir, livrer

Les trois activations étudiées ici permettent d'illustrer la différence entre activation, acquisition post-événement et première livraison d'un produit Copernicus EMS.

| Activation | Part SAR | Événement → activation | → 1re acquisition post | → 1re livraison |
|---|---|---|---|---|
| EMSR847 — Cyclone Melissa | 22 % | −9,3 h | +35,4 h | +9,3 h |
| EMSR884 — Séisme Venezuela | 8 % | +11,8 h | +6,8 h | +32,9 h |
| EMSR916 — Colombie | 11 % | +4,7 h | +27,0 h | +39,3 h |

**Tableau 3 — Délais relatifs à trois activations Copernicus EMS étudiées. Source : calculs de l'auteur à partir des activations Copernicus EMS étudiées. La part SAR correspond à la proportion des produits ou acquisitions radar recensés dans l'activation. L'échantillon porte sur trois activations et ne permet pas d'établir une règle générale sur les délais Copernicus EMS.**

Le cas de Melissa montre qu'un cyclone peut être anticipé : l'activation EMSR847 précède le passage de l'événement de 9,3 heures. Cette anticipation ne garantit cependant pas qu'une image optique post-événement exploitable soit immédiatement disponible. La première acquisition post-événement recensée intervient à +35,4 heures, alors que la première livraison est indiquée à +9,3 heures. Ces deux délais ne décrivent pas le même objet : une livraison peut reposer sur d'autres sources ou produits, et la disponibilité d'une acquisition ne garantit pas qu'elle soit dégagée ou suffisante pour lire l'ensemble du territoire.[^10]

Pour le Venezuela, l'activation intervient à +11,8 heures, la première acquisition post-événement à +6,8 heures et la première livraison à +32,9 heures. Dans le cas colombien, l'activation intervient à +4,7 heures, la première acquisition à +27,0 heures et la première livraison à +39,3 heures.

Ces trois activations confirment que les étapes de réponse ne sont pas synchrones : activation, acquisition, interprétation et livraison correspondent à des temporalités différentes. La première image acquise n'est pas nécessairement la première image utile. De même, la première livraison n'est pas nécessairement synonyme de couverture complète, homogène ou suffisamment détaillée pour répondre à toutes les questions d'une cellule d'évaluation.

La part SAR reste faible dans les trois activations étudiées : 22 % pour Melissa, 8 % pour le Venezuela et 11 % pour la Colombie. Ce résultat est cohérent avec la prédominance de l'optique observée dans les données de la Charte. Il doit toutefois être lu pour ce qu'il est : une observation sur trois activations, non une estimation de l'ensemble des opérations Copernicus EMS.

### 1.3 Une image acquise n'est pas nécessairement une image exploitable

Le délai opérationnel pertinent ne se limite pas au délai de la première acquisition. Il faut aussi connaître la couverture nuageuse, la résolution et l'emprise effectivement couverte. Une image peut exister tout en restant inutilisable sur une part importante de la zone sinistrée.

Cette distinction est particulièrement importante après un cyclone. Les nuages, la pluie, l'humidité et la persistance du système météorologique constituent à la fois des éléments du phénomène et des obstacles à la lecture optique de ses conséquences.

L'analyse des données Maxar Open Data disponibles en Jamaïque après le cyclone Melissa (28 octobre 2025) porte sur 8 469 tuiles, regroupées par date et par plateforme, avec le nombre de tuiles, la couverture nuageuse moyenne, minimale et maximale, le GSD moyen ainsi que le nombre de tuiles dont la couverture est inférieure à 10 %.

La première acquisition post-événement existe dès J+1 (29 octobre), mais seuls 20 % des 80 tuiles acquises ce jour-là présentent moins de 10 % de couverture nuageuse. Ce taux monte à 84 % le lendemain (J+2), sur un échantillon plus restreint de 217 tuiles, avant de retomber à 21 % à J+3 (727 tuiles), puis de se stabiliser progressivement entre 54 % et 63 % à partir de J+4 et J+5.

Réserve — cette évolution n'est pas monotone : elle reflète autant la variabilité des zones effectivement imagées chaque jour, le nombre et l'emplacement des tuiles acquises changeant d'un jour à l'autre, que l'amélioration progressive des conditions météorologiques. Une analyse restreinte à une emprise fixe rejouée chaque jour, plutôt qu'à l'ensemble variable des tuiles disponibles, permettrait de confirmer si la tendance de fond est réellement à l'amélioration continue ou si elle reste dominée par cet effet de sélection. Les calculs sont fournis dans les matériaux complémentaires.

Cette analyse ne remet pas en cause la valeur de l'optique. Lorsqu'une image très haute résolution est disponible, dégagée et couvrante, elle reste la source la plus lisible pour caractériser visuellement un dommage. Elle montre simplement que cette condition peut manquer précisément dans la fenêtre où l'information est la plus nécessaire.

### 1.4 Le cyclone tropical est un aléa multiple

Un cyclone ne détruit pas partout de la même façon. Ses vents, ses pluies, la houle, la marée de tempête et parfois les tornades peuvent endommager le bâti, couper les réseaux et provoquer inondations ou glissements de terrain. Une carte de changement doit donc être interprétée à la lumière de plusieurs mécanismes, pas d’une signature cyclonique unique.

La répartition des dommages n'est donc ni uniforme ni entièrement aléatoire. Elle dépend de la trajectoire du système, de sa vitesse, du relief, de l'exposition des côtes, de la saturation préalable des sols, de la taille du cyclone et de la configuration des bassins versants. Les systèmes lents peuvent concentrer de fortes quantités de précipitations sur un même territoire. Les reliefs exposés favorisent les pluies orographiques. Les sols saturés rendent les ruissellements, les inondations et les glissements de terrain plus probables.

Cette description provient de la doctrine cyclonique et de la littérature sur les risques ; elle ne résulte pas d’une mesure menée dans cette étude.

![Figure 1](figures/figure_1.png)

**Figure 1 — Asymétrie spatiale des effets d'un cyclone tropical. Schéma conceptuel montrant que les effets d'un cyclone ne sont pas répartis uniformément autour de sa trajectoire. Dans l'hémisphère Nord, le quadrant avant droit (nord-est ici) combine généralement le vent maximal, la surcote la plus forte et le plus grand potentiel de tornades. Cette asymétrie fournit une information de priorisation à l'échelle territoriale, mais ne permet pas de conclure sur l'état d'un bâtiment individuel.**

![Figure 2](figures/figure_2.png)

**Figure 2 — Facteurs aggravants des dommages liés à un cyclone tropical : trajectoire dans l'hémisphère Sud. Représentation d'une tempête tropicale de l'hémisphère Sud, avec sa trajectoire probable, son point de récurvature et les demi-cercles navigable et dangereux, symétriques de la configuration de l'hémisphère Nord présentée en figure A.**

L'asymétrie autour de la trajectoire est un élément utile à l'échelle de la planification. Dans l'hémisphère Nord, le quadrant avant droit est généralement considéré comme le secteur où le mouvement de translation du cyclone et sa circulation renforcent les vents. Dans l'hémisphère Sud, la situation symétrique correspond au quadrant avant gauche.

Cette règle n'autorise pas à prédire directement les dommages à l'échelle d'un bâtiment. La vulnérabilité du bâti, le relief, l'exposition locale, les pluies, la submersion et l'accessibilité modifient fortement les effets observés. Elle permet toutefois d'orienter les premières acquisitions et l'analyse vers les secteurs les plus susceptibles de concentrer les impacts.

Deux analyses complémentaires pourraient renforcer le lien entre la physique de l'aléa et le signal produit par l'outil.

La première consisterait à croiser les valeurs du T-stat avec la trajectoire du cyclone Melissa. Si l'asymétrie décrite par la doctrine se retrouve dans les données, on peut s'attendre à une concentration plus élevée du signal de changement dans les secteurs situés du côté de la trajectoire considéré comme le plus exposé. Une relation positive soutiendrait la cohérence spatiale entre le signal radar et la géographie attendue de l'aléa. Une relation faible ou absente serait également informative : elle indiquerait que le signal dépend aussi de la structure urbaine, de l'humidité, de la végétation ou d'autres mécanismes locaux.

La seconde consisterait à comparer le T-stat aux valeurs du ShakeMap de l'USGS pour le séisme vénézuélien. Une corrélation positive indiquerait que les unités les plus fortement secouées tendent à recevoir des scores de changement plus élevés. Une corrélation faible ou absente préciserait les limites entre l'intensité macrosismique modélisée, les dommages réellement produits et la réponse du signal radar.

Ni le croisement avec la trajectoire de Melissa ni celui avec le ShakeMap vénézuélien n’a été calculé ici. Ils constituent des pistes d’évaluation, non des résultats acquis.

### 1.5 L'optique reste la référence, le radar répond à son absence

Lorsque deux images optiques à très haute résolution montrent clairement le même bâtiment avant et après la catastrophe, l’analyste peut comparer directement ses formes et son environnement. Le radar étudié ici ne remplace pas cette lecture : il intervient surtout lorsqu’elle n’est pas encore possible.

La difficulté apparaît lorsque cette condition manque dans les 24 à 48 premières heures. Trois limites sont alors particulièrement importantes.

La première est météorologique. La couverture nuageuse, fréquente après un cyclone, peut masquer une part importante de la zone sinistrée. Sur le Venezuela, jusqu'à 31,9 % de la surface de Caraballeda est restée masquée par les nuages lors des premières acquisitions très haute résolution. Un second passage, plus de dix jours après l'événement, a été nécessaire pour tenter de compléter la couverture.

La deuxième tient à l'étendue de la zone à analyser. L'évaluation d'une catastrophe peut couvrir un territoire bien plus vaste que ce qu'un analyste peut interpréter visuellement dans un délai court. Lors du cyclone Melissa, l'activation Copernicus EMSR847 a couvert 39 zones d'intérêt réparties sur trois pays, plus de 10 600 km² et 262 154 bâtiments potentiellement exposés. La couverture optique complète ne s'est achevée qu'à la fin novembre, près d'un mois après le passage du cyclone.

La troisième est liée au caractère programmatique de l'imagerie optique. Les satellites doivent être programmés pour acquérir une image sur une zone donnée. Cette programmation peut retarder la première acquisition, mais aussi la révision d'une analyse lorsqu'une nouvelle image est nécessaire pour compléter une zone ou lever un doute.

Le radar échappe à la contrainte nuageuse. Il acquiert de jour comme de nuit et, avec Sentinel-1, il offre une couverture étendue et une fréquence de revisite utile pour l'évaluation initiale. Il ne fournit cependant pas une photographie : il mesure un signal indirect, lié à la rétrodiffusion et à la stabilité des diffuseurs.

J'ai donc cherché une méthode capable d'utiliser cet avantage, non pour remplacer l'interprétation optique, mais pour la compléter là où les zones restent sous les nuages ou n'ont pas encore été couvertes en haute résolution. L'objectif est de produire une première priorisation : déterminer les secteurs où l'effort de photo-interprétation, l'acquisition aérienne ou les vérifications de terrain doivent se concentrer en premier.

Cette question prolonge un intérêt plus ancien, né du cyclone Idai au Mozambique en 2019. J'y ai élaboré la méthodologie d'un indice de vulnérabilité logistique et conduit ses premiers essais de calcul par analyse spatiale sous SIG. Ce travail, dont le Mozambique a été le moteur, a donné lieu deux ans plus tard au projet Signal. C'est là que j'ai abordé la géomatique pour la première fois, et c'est ce qui m'a décidé à m'y former. Le constat initial était déjà le même : l'imagerie satellite peut fournir une information rapide, mais elle est rarement transformée en outil dynamique de priorisation adapté aux besoins des organisations humanitaires.[^11]

### 1.6 Les critères qui guideront le choix de la méthode

L'idée initiale était d'éviter les méthodes lourdes en calcul, notamment les approches de deep learning. Cette voie a été testée dans ArcGIS Pro lors de la constitution d'une couche bâtimentaire de référence. Les limites observées étaient importantes : temps de calcul long, bâtiments mitoyens fusionnés, fausses détections en zone bâtie dense et forte dépendance au contexte d'entraînement.

Un bâti léger en tôle en Haïti, un ensemble urbain du Venezuela et une zone sismique turque ne présentent pas les mêmes matériaux, formes, environnements ni mécanismes de destruction. Une méthode supervisée doit donc disposer de données d'entraînement représentatives du contexte auquel elle est appliquée. Cette dépendance en données et en calcul entre en tension avec une fenêtre opérationnelle de 24 à 48 heures.

Une contrainte pratique s'ajoute dans l'environnement retenu pour le projet : un greffon QGIS ne dispose pas nécessairement d'un GPU ni d'un environnement PyTorch approprié pour exécuter un modèle profond complexe.

Le travail s'est donc orienté vers une méthode statistique fondée sur l'intensité radar : la Pixel-Wise T-Test ou PWTT, développée par Ballinger pour détecter les dommages liés aux conflits en Ukraine et à Gaza. La méthode compare chaque pixel à son propre comportement historique. Elle ne nécessite pas de jeu d'entraînement propre au cyclone, au séisme ou au territoire étudié.

Le choix répond à une exigence de reproductibilité et d'explicabilité : produire un indicateur dont les calculs peuvent être inspectés, discutés et rejoués, plutôt qu'un résultat issu d'un modèle difficile à interpréter. Dans l'article de référence, Ballinger rapporte des AUC de l'ordre de 0,88 en Ukraine et de 0,81 à Gaza, sur plus de 500 000 empreintes bâtimentaires réparties sur douze villes.[^12]

La simplicité du principe ne garantit toutefois pas sa transposition. La méthode a été développée et validée sur des dommages de conflits armés. Il reste donc à déterminer si elle peut produire un signal utile sur des dommages d'origine naturelle, notamment après un cyclone et un séisme, et si elle peut le faire dans un délai compatible avec l'évaluation initiale.

La suite de cette partie examine donc :

- la méthode statistique retenue et ses paramètres ;
- le délai nécessaire pour produire un premier signal ;
- la longueur de ligne de base pré-événement ;
- les différences observées entre cyclone et séisme ;
- la comparaison avec les autres produits de détection disponibles ;
- l'apport de la cohérence interférométrique ;
- la manière d'utiliser un score selon que l'objectif est de cibler quelques adresses ou de balayer une zone plus large ;
- les limites liées à la résolution, à la couverture, au type d'aléa et aux vérités disponibles.

L'enjeu n'est pas d'opposer l'optique au radar. L'optique reste la référence pour interpréter un dommage lorsqu'une image exploitable est disponible. Le radar intervient dans la période et dans les secteurs où cette condition n'est pas encore satisfaite. C'est dans cet espace, entre le besoin d'une information précoce et la disponibilité différée d'une lecture détaillée, que s'inscrit la méthode étudiée ici.

## 2 Résolution, délai et couverture : le compromis de l’imagerie optique

Une image acquise après l’événement ne suffit pas : il faut qu’elle arrive à temps, couvre effectivement la zone recherchée et montre les objets avec assez de détail. Les cas de Black River et de Playa Verde mettent en regard ces trois exigences, qui ne sont pas toujours réunies par la même source.

### 2.1 Black River : l'image du lendemain n'est pas forcément la meilleure

![Figure 3](figures/figure_3.png)

**Figure 3 — Black River, Jamaïque : disponibilité, qualité et délai des observations après le cyclone Melissa.** La planche compare les acquisitions optiques satellitaires, l'imagerie aérienne NOAA, l'imagerie drone et les passages Sentinel-1. Elle montre qu'une acquisition disponible à J+1 peut être moins exploitable qu'une image plus tardive, en raison de la résolution, de la couverture nuageuse ou de l'angle de prise de vue. Source : données Maxar Open Data, NOAA, Atlas Logistique / UNDAC et catalogue Sentinel-1.

À Black River, la première image optique post-cyclone est disponible dès J+1. Elle présente une résolution de 0,71 m et une couverture nuageuse moyenne de 14 % pour l'ensemble de la scène. Cette acquisition permet déjà de repérer le secteur, mais elle ne fournit pas nécessairement une lecture détaillée de chaque bâtiment. Une acquisition plus fine est disponible à J+3, avec une résolution de 0,50 m. Elle est toutefois affectée par 71 % de couverture nuageuse, et le bâtiment étudié est masqué par les nuages. Dans ce cas, la meilleure résolution théorique ne produit aucune information exploitable sur la cible.

Les acquisitions de J+5 et J+6 sont plus favorables : elles offrent respectivement 0,33 m et 0,47 m de résolution, avec 2 % puis 0 % de couverture nuageuse sur la scène. Elles permettent une interprétation plus confortable, mais arrivent plusieurs jours après l'événement.

La couverture nuageuse moyenne d'une scène doit donc être interprétée avec prudence. Une scène couverte à 71 % peut être dégagée sur un bâtiment et inutilisable sur un autre. Les métadonnées générales ne suffisent pas à le déterminer : il faut examiner l'image elle-même.

La géométrie d'acquisition ajoute une deuxième contrainte. L'image de J+1 est prise avec un angle hors nadir de 36,9°, le plus élevé de la série. Les acquisitions suivantes sont prises sous des angles plus favorables, de 16,5° à 10,4°. Une prise de vue très oblique peut réduire la qualité apparente de l'image, allonger les ombres et compliquer l'interprétation des bâtiments et de leurs abords.

Dans ce cas, la première information véritablement lisible sur le bâtiment ne provient pas nécessairement du satellite. L'acquisition aérienne NOAA, réalisée à J+3 avec une résolution de 0,15 m, fournit une observation plus détaillée. Elle reste toutefois limitée à la zone couverte par le vol.

La série radar apporte une autre continuité : Sentinel-1 acquiert des images indépendamment de la lumière et de la couverture nuageuse. Entre l'événement et J+18, cinq passages radar sont disponibles, dont le premier autour de l'arrivée des premières images optiques. Le radar ne remplace pas l'optique ; il fournit un signal complémentaire lorsque l'image optique est nuageuse, oblique ou insuffisamment lisible.

### 2.2 Playa Verde : les acquisitions s'interrompent

![Figure 4](figures/figure_4.png)

**Figure 4 — Playa Verde, La Guaira : continuité des observations après le séisme du 24 juin 2026.** Les acquisitions optiques se concentrent dans les premiers jours, puis laissent un intervalle sans nouvelle observation optique détaillée jusqu'à l'orthophotographie drone de J+17. Les passages Sentinel-1 assurent une continuité d'observation pendant cet intervalle. Source : données Vantor Open Data, Planet Open Data, Copernicus Sentinel, Atlas Logistique et catalogue Sentinel-1.

À Playa Verde, la première image optique apparaît dès J+1, avec une résolution de 0,36 m. D'autres acquisitions sont disponibles à J+2, puis une image Sentinel-2 à J+3 et une image optique à J+5. Le catalogue semble donc bien renseigné pendant les premiers jours.

Après J+5, cependant, les acquisitions optiques s'interrompent pendant environ douze jours. La prochaine observation détaillée présentée dans la planche est l'orthophotographie drone de J+17.

Cette absence temporaire est importante pour une mission d'évaluation : une image très détaillée peut être disponible au début, puis aucune nouvelle image optique exploitable ne l'est pendant plusieurs jours. Les seules observations disponibles dans cet intervalle sont alors les acquisitions radar Sentinel-1, avec six passages entre l'événement et le vol drone : deux autour de J+1, deux autour de J+7 et deux autour de J+13.

La chronologie montre ainsi trois fonctions différentes :

- l'imagerie optique fournit une lecture visuelle lorsqu'elle est dégagée et suffisamment détaillée ;
- le radar maintient une observation régulière pendant les périodes où l'optique est absente, nuageuse ou difficile à interpréter ;
- l'imagerie aérienne ou le drone apportent une observation plus fine lorsque la mission peut être organisée.

### 2.3 Ce que les deux planches montrent

Ces deux exemples ne permettent pas de définir un délai universel auquel une image devient exploitable. Ils montrent plutôt que le délai utile dépend de plusieurs éléments à la fois :

- la date de l'acquisition ;
- la couverture nuageuse au niveau de la cible ;
- la résolution réelle ;
- l'angle de prise de vue ;
- la continuité des acquisitions ;
- la possibilité de mobiliser un avion ou un drone.

La question opérationnelle n'est donc pas seulement : « Quand la première image est-elle disponible ? » Elle est aussi : « Quand dispose-t-on d'une observation suffisamment fiable pour décider quoi faire ? »

Une image optique détaillée peut être essentielle pour caractériser un dommage, mais elle peut arriver trop tard, être masquée par les nuages ou ne pas couvrir la cible sous un angle favorable. Le radar fournit une information différente : il ne permet pas toujours d'identifier directement la nature du dommage, mais il peut signaler plus tôt les secteurs où le comportement de la surface a changé.

Pour répondre à cette question, il fallait retenir une méthode compatible avec les contraintes du projet : données ouvertes, traitement reproductible, absence de données d'entraînement propres à un événement particulier, fonctionnement sur des emprises choisies par l'utilisateur et possibilité d'intégration dans QGIS. La méthode retenue est la Pixel-Wise T-Test (PWTT), qui compare, pixel par pixel, les valeurs radar observées avant et après l'événement afin d'identifier les variations statistiquement significatives.

Cette méthode est introduite dans la section suivante, avant l'examen de ses adaptations, de ses performances et de ses limites dans les cas du cyclone et du séisme étudiés.

## 3 État de l’art : des cartes disponibles, peu d’outils à exécuter

### 3.1 Distinguer le résultat de l’outil

Après une catastrophe, on trouve des cartes de dommages, des portails de consultation et des méthodes publiées. Ils ne répondent pas au même besoin. Une carte livre le résultat d’une analyse menée par un tiers ; un outil permet à l’évaluateur de choisir une nouvelle emprise, une date et des paramètres, puis de refaire le calcul.

Cette revue distingue donc trois familles. Les **outils exécutables** (catégorie A) donnent à l’utilisateur la main sur l’analyse. Les **produits et portails** (catégorie B) donnent accès à des résultats déjà calculés. Les **modèles d’impact** (catégorie C) croisent un aléa et des données d’exposition sans détecter de changement dans une image post-événement. InaSAFE et OpenQuake relèvent de cette dernière famille : ils répondent à des questions utiles, mais différentes de celle traitée ici.

Le nombre de produits ne doit ainsi pas être confondu avec celui des outils réutilisables. La revue consacrée au Venezuela recense vingt producteurs de résultats ; elle n’implique pas que vingt méthodes soient exécutables par une cellule d’évaluation sur le prochain événement. C’est cette autonomie de calcul qui délimite le sujet du présent travail.

### 3.2 Les outils identifiés et leurs différences

Quatre approches ou outils exécutables ont été retenus dans la recherche, dont le développement présenté dans ce dépôt :

- **PWTT**, proposé par Ballinger (2024-2025), calcule un test t par pixel sur les séries de rétrodiffusion Sentinel-1. La méthode est non supervisée et a été diffusée avec une application Earth Engine et un carnet Colab ; un greffon QGIS tiers existe également.
- Le **Rapid Damage Mapping Tool** de Dietrich et al. (2025) exploite des séries Sentinel-1 avec un modèle supervisé entraîné sur des évaluations de dommages en Ukraine. Il est accessible au moyen de tableaux de bord Earth Engine.
- Les **pratiques recommandées par UN-SPIDER** décrivent pas à pas des calculs de changement de rétrodiffusion, notamment à partir d’un rapport et d’un seuil, sans constituer pour autant une interface intégrée prête à l’emploi.
- Le **Rapid Damage Detection Tool** développé dans ce travail reprend une approche non supervisée de changement par pixel, d’abord exécutée sur Earth Engine, puis intégrée à un greffon QGIS proposant notamment cohérence, fusion, inondation et informations de contexte.

Le PWTT n’est donc pas le seul outil que l’on puisse manipuler. La distinction décisive pour ce projet tient plutôt au **domaine d’entraînement**. Un modèle entraîné sur les dommages observés en Ukraine peut être performant dans ce contexte ; son application à un cyclone jamaïcain ou à un séisme vénézuélien demande une évaluation spécifique, car les bâtiments, les mécanismes de destruction et les conditions d’observation diffèrent. Cela ne signifie pas qu’un modèle supervisé serait nécessairement inutilisable ailleurs, mais qu’on ne peut pas présumer sa transférabilité.

Le PWTT, lui, compare chaque pixel à son propre passé et ne requiert pas d’étiquettes de dommages pour être ajusté à un nouveau territoire. Ce caractère non supervisé a permis de l’essayer sur le cyclone et le séisme étudiés ici. Il ne garantit pas que le signal obtenu classe bien les dommages : c’est précisément ce que les expériences suivantes mesurent.

### 3.3 Le cas plus difficile des routes

#### 3.3.1 Ce que proposent les travaux existants

La pratique recommandée « Earthquake Urban Damage Detection Using Sentinel-1 Data » d’UN-SPIDER⁴ croise une carte de changement avec un réseau routier afin de mettre en évidence des voies **susceptibles** d’être bloquées par des gravats. Son vocabulaire importe : elle ne présente pas le croisement comme un constat de route coupée ou endommagée. Elle déconseille par ailleurs son application aux ouragans, tornades et tsunamis, réserve directement pertinente pour le cas cyclonique étudié ici.

Karimzadeh et al. (2022)⁵ apportent un autre type de validation. Après le séisme de Kumamoto, leur étude confronte une méthode combinant intensité et cohérence radar à 530 km de mesures de rugosité routière réalisées par accéléromètre embarqué ; elle rapporte 87,1 % d’exactitude pour son résultat binaire. L’intérêt pour ce projet n’est pas de reprendre ce chiffre comme une performance attendue, mais de noter que la vérification porte sur une mesure de chaussée indépendante des images. Un tel protocole constitue une piste pour évaluer ultérieurement les sorties routières du dispositif développé ici.

Les études de Washaya et Balz (2018)⁶ et de Malmgren-Hansen et al. (2020)⁷ examinent des changements radar dans des zones urbaines soumises à des séismes ou à des cyclones, mais ne fournissent pas, dans la revue menée ici, une validation dédiée au couple cyclone–réseau routier. Le corpus ne justifie donc pas d’assimiler une anomalie radar le long d’une route à un diagnostic d’accessibilité.

#### 3.3.2 Une référence vénézuélienne trop peu renseignée

Les couches routières Copernicus EMS de l’activation EMSR884 ont été examinées : sept couches couvrant quatre zones d’intérêt et 24 696 entités, dont trois seulement portent une annotation de dommage (deux *Damaged*, une *Destroyed*). À titre de contraste, la même activation comprend 3 072 bâtiments annotés par classe de dommage, dont 695 détruits.

Avec trois routes positives, une AUC serait **mathématiquement calculable** si les deux classes sont présentes, mais son estimation serait beaucoup trop fragile pour servir de comparaison. Le protocole de cette étude fixe un minimum de vingt objets positifs pour retenir une évaluation quantitative. Les résultats routiers vénézuéliens ne sont donc pas utilisés pour conclure sur l’AUC, le rappel ou les fausses alertes du score.

Ce faible nombre d’annotations laisse au moins deux interprétations ouvertes : peu de routes ont été touchées, ou une partie des perturbations n’a pas été identifiable et annotable depuis l’imagerie employée. Les données disponibles ne permettent pas de départager ces explications.

#### 3.3.3 Pourquoi un tronçon reste ambigu

**La largeur du pixel.** Les produits Sentinel-1 GRD sont fournis sur une grille de 10 m, du même ordre que la largeur de nombreuses rues urbaines. Un pixel associé à un tronçon peut inclure façades, murs, véhicules et végétation : son score ne représente donc pas exclusivement la chaussée.

**La géométrie radar.** Dans une scène bâtie, le signal d’une structure élevée peut être déplacé vers le capteur et se superposer à l’emplacement cartographique d’une voie. Une anomalie affectée à la route peut provenir d’un bâtiment voisin. Celui-ci pourrait aussi gêner l’accès en s’effondrant, mais le signal seul ne permet ni d’attribuer le changement à cet objet, ni d’établir que la voie est réellement bloquée.

**La diversité des obstacles.** Des gravats, un glissement de terrain et un pont effondré n’ont ni la même taille ni la même réponse radar. Un changement important le long d’un axe peut justifier une vérification ; son absence ne démontre pas que l’axe est praticable.

### 3.4 Pourquoi les outils exécutables restent rares

Livrer un produit et maintenir un outil imposent des engagements différents. Une carte est calculée dans les conditions d’une activation donnée ; un outil doit continuer à fonctionner lorsque changent les catalogues d’images, les interfaces de programmation et les versions des logiciels. Il doit aussi rendre explicites les choix de méthode que le producteur d’une carte pourrait laisser en arrière-plan.

La contrepartie est une plus grande autonomie pour l’organisation utilisatrice. Une cellule d’évaluation n’a pas seulement besoin de consulter les dommages de la crise précédente : elle doit pouvoir relancer un calcul sur **son emprise, sa date et sa base de bâtiments**, puis comprendre les limites de la sortie. C’est cette exigence, autant que la performance d’une méthode, qui a orienté le développement de l’outil.

### 3.5 Pourquoi retenir le PWTT

Le choix du PWTT s’est construit autour de trois arguments. Premièrement, son implémentation était manipulable avant la publication de l’article : il a été possible de l’essayer plutôt que de juger uniquement des cartes produites par un tiers. Deuxièmement, son caractère non supervisé permettait de tester le même principe sur un cyclone et un séisme, sans supposer acquise sa performance sur ces événements.

Troisièmement, la méthode avait déjà des usages proches du contexte humanitaire étudié. Le PNUE mentionne, dans son travail sur les gravats au Venezuela, « a pixel-wise temporal t-test (PWTT), adapted to a z-score formulation »⁸ ; IMPACT Initiatives⁹ décrit une construction apparentée. Ce rapprochement situe le projet parmi des pratiques existantes, sans faire de ces usages une validation de nos propres résultats. Les sections suivantes exposent donc le calcul effectivement retenu, puis confrontent ses sorties aux références disponibles.

## 4 Le test t par pixel : mesurer un changement inhabituel

Le radar n’est pas une photographie. Même sans catastrophe, la rétrodiffusion d’un pixel varie avec l’humidité, la végétation, la pluie, la géométrie d’acquisition ou les activités humaines. La question utile n’est donc pas seulement de savoir si le signal a changé, mais si le changement dépasse ce que ce pixel varie habituellement.

Le Pixel-Wise T-Test (PWTT) de Ballinger répond à cette question en comparant, pixel par pixel, la moyenne du signal avant l’événement à celle observée après. L’écart est rapporté à la variabilité habituelle du pixel : une variation importante sur un pixel stable reçoit donc davantage d’attention que la même variation sur un pixel naturellement instable.

Cette propriété compte particulièrement en ville. Véhicules, stocks, travaux et humidité peuvent modifier le signal d’un aéroport, d’une gare ou d’une zone industrielle sans qu’un dommage se soit produit. Le PWTT ne cherche donc pas à signaler toute différence entre deux dates : il cherche une différence inhabituelle au regard de l’historique local.

### 4.1 Comparer le signal avant et après l'événement

La série Sentinel-1 est séparée autour de la date de l’événement :

- une période de référence pré-événement, notée τ₀ ;
- une période d'inférence post-événement, notée τ₁.

Dans la configuration proposée par Ballinger, la période de référence couvre environ un an, soit approximativement trente acquisitions Sentinel-1. Cette durée vise à couvrir un cycle saisonnier complet : humidité des sols, végétation, pluie ou autres évolutions environnementales susceptibles de modifier la rétrodiffusion sans qu'il y ait de dommage. La période post-événement couvre environ deux mois, soit approximativement cinq images. Elle doit être assez longue pour constituer un échantillon, mais suffisamment courte pour ne pas mélanger l'événement étudié avec des changements ultérieurs.

Pour chaque pixel x, chaque combinaison d'orbite ω, de polarisation π et de période τ, la moyenne de la rétrodiffusion est calculée ainsi :

$$\bar{x}(\omega,\pi,\tau) = \frac{1}{n} \sum_{i=1}^{n} x_i(\omega,\pi,\tau) \tag{1}$$

L'écart-type associé est :

$$s(\omega,\pi,\tau) = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} \bigl(x_i(\omega,\pi,\tau) - \bar{x}(\omega,\pi,\tau)\bigr)^2} \tag{2}$$

où n désigne le nombre de scènes Sentinel-1 valides disponibles pour le pixel, l'orbite, la polarisation et la période considérés.

n est compté pixel par pixel, et non pour la scène entière. Deux pixels voisins peuvent donc reposer sur un nombre différent d’observations valides, par exemple en bord de fauchée, dans une ombre radar ou près d’un masque d’eau. Les statistiques reflètent ainsi la couverture réellement disponible.

Avec les deux sens de passage de Sentinel-1, ascendant et descendant, et les deux polarisations VV et VH, la méthode peut obtenir jusqu'à quatre statistiques par pixel. Ces quatre vues ne sont pas parfaitement redondantes : selon l'orientation des bâtiments, le relief ou la géométrie d'acquisition, une orbite peut révéler un changement que l'autre perçoit peu ou pas.

### 4.2 La statistique publiée

L’article écrit une statistique qui n’impose pas la même dispersion aux deux périodes : chaque variance est rapportée à son propre effectif. La littérature statistique l’identifie comme la forme de Welch, même si l’article ne la nomme pas ainsi :

$$t(\omega,\pi) = \frac{\bar{x}(\omega,\pi,\tau_0) - \bar{x}(\omega,\pi,\tau_1)}{\sqrt{\dfrac{s^2(\omega,\pi,\tau_0)}{n(\omega,\pi,\tau_0)} + \dfrac{s^2(\omega,\pi,\tau_1)}{n(\omega,\pi,\tau_1)}}} \tag{3}$$

Le numérateur mesure le déplacement du signal entre les deux périodes. Le dénominateur mesure l'incertitude associée à cet écart, en tenant compte séparément de la variance et du nombre d'images de chacune des périodes.

Cette forme est particulièrement adaptée au problème étudié. La période de référence couvre environ une année, donc plusieurs saisons, tandis que la période post-événement couvre seulement quelques semaines. Ces deux ensembles n'ont aucune raison d'avoir ni le même nombre d'images ni la même variance. Le test de Welch est précisément conçu pour comparer des moyennes lorsque les variances sont inégales.

Le résultat est sans unité. Une valeur absolue élevée indique que l’observation postérieure s’écarte fortement du comportement historique du pixel, compte tenu de la variabilité mesurée.

Le signe n’est pas une classe de dommage. Un effondrement peut augmenter ou diminuer la rétrodiffusion selon la structure concernée et sa géométrie radar. Un grand bâtiment à toiture plate peut devenir plus brillant après un effondrement, lorsque la réflexion spéculaire laisse place à une diffusion plus rugueuse. À l'inverse, une maison qui produisait un double rebond peut devenir moins brillante lorsque sa structure disparaît. Dans les deux cas, il y a changement potentiellement lié au dommage.

Les quatre statistiques possibles sont donc combinées en retenant la plus forte valeur absolue :

$$T = \max_{(\omega,\pi)} \bigl| t(\omega,\pi) \bigr| \tag{4}$$

Cette opération conserve la vue la plus discriminante lorsqu’une orbite révèle un changement que l’autre perçoit peu. Elle évite de diluer un signal local en moyennant des vues de qualité différente.

### 4.3 Ce que calcule le code publié : la variance regroupée

Le code diffusé avec l’article n’évalue pas l’équation (3) lorsqu’il dispose de plusieurs images postérieures : il calcule un test t de Student à variance regroupée. L’outil reprend cette forme. La différence documentée oppose donc la formule écrite dans l’article au code publié avec celui-ci, et non le code du projet au code de référence.

La variance regroupée est :

$$s_p = \sqrt{\frac{s^2_{\text{pré}}\,(n_{\text{pré}}-1) + s^2_{\text{post}}\,(n_{\text{post}}-1)}{n_{\text{pré}} + n_{\text{post}} - 2}} \tag{5}$$

La statistique effectivement calculée est ensuite :

$$t_{\text{Student}} = \frac{\bigl| \bar{x}_{\text{post}} - \bar{x}_{\text{pré}} \bigr|}{s_p \sqrt{\dfrac{1}{n_{\text{pré}}} + \dfrac{1}{n_{\text{post}}}}} \tag{6}$$

Le test de Student suppose des variances égales. Cette hypothèse est discutable ici : la période antérieure couvre plusieurs saisons, tandis que la période postérieure est courte et peut présenter une dispersion modifiée par l’événement.

Une version ultérieure du code de référence, publiée le 25 juin 2026, retient le test de Welch par défaut et conserve la variance regroupée en option, que son propre commentaire désigne comme la forme d'origine. Les deux formes ont donc été comparées, dans la configuration exacte de l'outil et sur deux catastrophes : la variance regroupée l'emporte de 0,013 d'AUC sur le cyclone jamaïcain, et le test de Welch de 0,004 sur le séisme vénézuélien. Ces valeurs décrivent les échantillons évalués ; elles établissent qu'aucune des deux formes ne domine l'autre, sans démontrer de supériorité générale.

La combinaison des orbites par maximum, quant à elle, suit littéralement l'équation (4) de l'article ; c'est la version ultérieure du code de référence qui lui a substitué une somme de Stouffer pondérée par √df, laquelle rapporte 0,004 d'AUC. L'outil reproduit donc le code diffusé avec l'article sur les trois points : la variance regroupée, la combinaison des orbites par maximum, et le rayon de dix mètres du filtre médian.

Ce dernier point résulte d'un choix explicite. Un rayon de vingt mètres a été essayé, et mesuré : il rapporte 0,015 d'AUC sur le cyclone jamaïcain et n'en coûte aucune sur le séisme vénézuélien. Un argument instrumental le soutenait même — Sentinel-1 est livré en mode IW GRDH sur une grille de dix mètres alors que sa résolution spatiale avoisine vingt mètres en distance et vingt-deux en azimut, de sorte que deux pixels voisins ne sont pas deux mesures indépendantes. Le rayon de dix mètres a néanmoins été retenu, afin que l'outil ne s'écarte de la méthode publiée sur aucun point : un gain de quinze millièmes d'AUC ne compense pas la perte de comparabilité qu'introduirait une divergence, fût-elle motivée. L'essai est conservé parmi les variantes, en annexe.

Enfin, ces deux formulations partagent la même condition de validité, appliquée après le calcul : au moins trois acquisitions antérieures et au moins deux acquisitions postérieures par trace orbitale. Aucune ne permet donc de produire un résultat à partir d'une acquisition unique, ce qui motive la statistique distincte présentée en section suivante.

### 4.4 Tester une configuration à image unique

Le test t complet nécessite plusieurs images post-événement pour estimer la moyenne et la variance de la période τ₁. Or cette condition entre en tension avec l'objectif de produire une information dans les premiers jours après une catastrophe. Il faut attendre plusieurs passages Sentinel-1 de la même trace orbitale pour obtenir une série post-événement exploitable.

Avec une seule image post-événement, la variance de la période postérieure n’est pas estimable. Ni Welch ni Student ne peuvent alors être appliqués dans leur forme complète. L’outil produit donc un score de type z, qui mesure l’écart de l’image unique par rapport à l’historique du pixel :

$$z(\omega,\pi) = \frac{x_{\text{post}}(\omega,\pi) - \bar{x}(\omega,\pi,\tau_0)}{s(\omega,\pi,\tau_0)} \tag{7}$$

où x_post(ω,π) est la valeur du pixel sur l'unique acquisition post-événement, x̄(ω,π,τ₀) la moyenne historique avant l'événement et s(ω,π,τ₀) l'écart-type correspondant.

Comme pour le test t, les valeurs obtenues selon les différentes orbites et polarisations peuvent être combinées en retenant l'écart le plus fort :

$$Z = \max_{(\omega,\pi)} \bigl| z(\omega,\pi) \bigr| \tag{8}$$

Le score z ne fournit pas la même information que le test t. Il ne compare pas deux distributions : il mesure l’éloignement d’une observation unique par rapport à la distribution historique. Il renonce à estimer la variabilité post-événement, mais permet de produire un premier signal dès la première acquisition utile.

![Figure 5](figures/figure_5.png)

**Figure 5 — Une seule image après l'événement suffit-elle ? Le losange rouge est le score obtenu avec une seule image postérieure ; les points suivent l'accumulation des acquisitions suivantes. Calcul en variance regroupée et orbites combinées par maximum, comme dans l'outil ; évaluation sur Open Buildings en Jamaïque et Overture au Venezuela, appariement strict. La figure compare, sur dix zones réparties dans quatre pays et deux types d'aléas, l'AUC d'un z-test à une image post-événement avec celle obtenue lorsque le nombre d'images postérieures utilisées dans le test t augmente de trois à neuf. Les losanges représentent le score à image unique ; les courbes représentent le meilleur score disponible à mesure que les acquisitions post-événement s'accumulent.**

Les résultats ne montrent pas qu'une image unique est systématiquement suffisante. Ils montrent plutôt que le délai de l'image compte davantage que le type d'aléa. Les scores calculés avec une image acquise moins d'un jour après l'événement restent proches du hasard dans plusieurs zones : 0,465 à Catia la Mar, 0,470 à AOI25 et 0,485 à La Guaira. À l'inverse, les images uniques disponibles à partir d'environ deux jours et demi après le cyclone jamaïcain donnent des AUC comprises entre 0,553 et 0,628 ; elles sont proches de la performance atteinte avec plusieurs images postérieures dans les mêmes zones.

La zone colombienne AOI02 constitue un cas différent : une image unique à J+4,5 produit une AUC de 0,739, supérieure à la meilleure valeur obtenue par le test à plusieurs images. Ce résultat indique qu'une image tardive peut déjà contenir un signal stabilisé et discriminant ; il ne suffit pas, à lui seul, à établir une règle générale.

La conclusion opérationnelle est donc prudente. Une première image post-événement peut fournir un classement utile, mais elle ne le fait pas immédiatement ni de manière garantie. Dans l'échantillon étudié, le classement devient plus régulièrement exploitable lorsque l'image unique est acquise environ deux jours après l'événement. Cette tendance repose sur seulement dix zones, quatre délais distincts et plusieurs zones jamaïcaines qui partagent la même orbite ; elle doit être lue comme un repère expérimental, non comme un seuil universel.

Le z-test à une image et le test t à plusieurs images répondent ainsi à deux temporalités différentes :

- le z-test vise un signal précoce, dès que la première image utile est disponible ;
- le test t sur plusieurs images vise une consolidation, lorsque plusieurs acquisitions ont permis d'estimer la variabilité post-événement.

### 4.5 Quelle durée de référence avant l'événement ?

La fenêtre pré-événement impose un compromis analogue. Une période courte est proche de la catastrophe, mais offre moins d’observations et décrit moins bien les variations ordinaires. Une période longue renforce l’échantillon et couvre plusieurs saisons, au risque d’intégrer des changements anciens ou des états moins comparables à la situation juste avant l’événement.

La Figure 6 examine cette question sur les cinq emprises dont la prévalence reste comprise entre 5 et 95 %, bornes en dehors desquelles une aire sous la courbe ne mesure plus rien. La fenêtre post-événement est fixée à trois images, tandis que la ligne de base pré-événement varie de 3 à 24 mois : 3, 6, 9, 12, 18 et 24 mois.

![Figure 6](figures/figure_6.png)

**Figure 6 — Quelle longueur de ligne de base ? Cinq emprises, celles dont la prévalence autorise une aire sous la courbe. Fenêtre post fixée à trois images. Balayage sur des lignes de base de 3, 6, 9, 12, 18 et 24 mois.**

Les résultats ne désignent pas une durée optimale valable partout, et les emprises se séparent nettement. Trois d'entre elles gagnent beaucoup à l'allongement de la référence : White House passe de 0,511 à trois mois à 0,759 à douze mois puis 0,782 à vingt-quatre ; Caraballeda de 0,488 à 0,625 puis 0,671 ; Catia La Mar de 0,419 à 0,528 puis 0,582. Les deux autres n'en tirent rien : Bartons reste plate, de 0,524 à 0,520, et Arlington décline, de 0,530 à 0,496.

La tendance centrale ne plafonne pas. La moyenne des cinq emprises, tracée en noir sur la figure, passe de 0,494 avec une ligne de base de trois mois à 0,591 à douze mois, puis continue de croître : 0,602 à dix-huit mois et 0,610 à vingt-quatre. Dans cet échantillon, allonger la référence au-delà d'une année améliore donc encore le classement moyen, d'environ deux centièmes d'AUC entre douze et vingt-quatre mois.

Une ligne de base de douze mois est néanmoins retenue par défaut, pour la même raison que le rayon de dix mètres du filtre médian : c'est la configuration de la méthode publiée, et l'outil ne s'en écarte sur aucun point. Le balayage indique cependant qu'une référence plus longue mériterait d'être évaluée sur un échantillon plus large, et que le gain n'est pas réparti uniformément — il se concentre sur les emprises dont la prévalence est faible, là où la période de référence courte ne suffit pas à décrire les variations ordinaires. Le paramètre reste réglable dans l'outil.

### 4.6 De la statistique au signal cartographique

Le résultat du test est d'abord un raster de valeurs continues. Il ne constitue pas encore une carte de bâtiments détruits. Il indique des pixels dont la rétrodiffusion s'écarte de manière inhabituelle de leur comportement passé.

Avant le calcul statistique, les images Sentinel-1 sont manipulées en rétrodiffusion linéaire, puis filtrées avant passage au logarithme. Cet ordre importe : appliquer un filtre sur des valeurs exprimées en décibels reviendrait à moyenner des logarithmes, ce qui n'a pas la même signification statistique que le filtrage sur l'échelle linéaire. Le filtre de Lee est utilisé pour réduire le speckle, bruit multiplicatif propre à l'imagerie radar cohérente. La configuration applique une fenêtre de 3×3 pixels et un nombre équivalent de vues de 5.

Pour associer le score pixel à une empreinte de bâtiment, l'outil peut agréger les pixels couverts par cette empreinte. Ballinger utilise la moyenne. L'implémentation de ce projet utilise par défaut le maximum, parce que cette agrégation a donné une AUC de 0,749 sur le séisme vénézuélien, contre 0,726 avec la moyenne. Un bâtiment partiellement atteint peut en effet contenir quelques pixels fortement anormaux, que la moyenne dilue dans un ensemble de pixels peu modifiés.

Cette préférence ne doit cependant pas être généralisée. Sur le cyclone jamaïcain, l'ordre entre les méthodes d'agrégation s'inverse et l'ampleur de l'écart n'est pas stable. L'agrégation doit donc demeurer un paramètre ajustable de l'outil, non une propriété présentée comme universellement optimale.

Enfin, la sortie cartographique ne doit pas être assimilée mécaniquement à un seuil statistique de significativité. Ballinger propose des seuils absolus de T, par exemple T > 2,7 à n = 40 pour un niveau de confiance donné dans son cadre de calcul. L'outil étudié utilise plutôt des seuils exprimés en centiles, afin de stabiliser la charge de travail à relire malgré les effets de saison. Dans les essais menés, un seuil absolu faisait varier cette charge de douze points entre saisons, alors qu'un seuil exprimé en centile maintenait ce volume constant.

Le gain opérationnel est clair : demander « les 1 % les plus suspects » donne à l'utilisateur un volume d'objets à examiner maîtrisé. La contrepartie est tout aussi claire : un centile n'est pas une probabilité de dommage ni un niveau de confiance statistique. Il indique une position relative dans la distribution des scores de l'emprise et de la date considérées.

### 4.7 Ce que la méthode permet, et ne permet pas, de dire

Cette section fixe ainsi le statut de la sortie produite. Le PWTT produit un indicateur continu de changement anormal, calculé par pixel à partir d'une comparaison avec le comportement historique du signal radar. Le résultat peut servir à classer et à prioriser des bâtiments ou des secteurs pour une analyse complémentaire.

En revanche, il ne permet pas, à lui seul, d'affirmer qu'un bâtiment est détruit, d'associer un score à une probabilité universelle de dommage, ou de transformer un seuil en niveau de confiance, faute d'une calibration qui relierait la valeur de T à une probabilité de dommage.

Ce cadre méthodologique permet maintenant d'examiner deux questions complémentaires : d'une part, comment le signal varie selon le type d'aléa et le délai d'acquisition ; d'autre part, si l'ajout de la cohérence interférométrique apporte une information distincte de celle de l'intensité radar.

## 5 Résultats : délai, signature et agrégation

Le délai opérationnel ne se résume pas au temps de calcul. Il comprend l’attente de l’image post-événement, son traitement et l’interprétation du résultat. Une méthode rapide peut donc rester trop tardive si la première acquisition exploitable arrive plusieurs jours après la catastrophe.

Une image unique peut donc fournir un premier classement, mais pas nécessairement dans les premières heures. Dans l’échantillon étudié, les acquisitions disponibles autour de deux jours après l’événement sont plus régulièrement utiles que celles arrivées avant un jour. Deux questions sont examinées séparément : que vaut ce signal précoce, et quel délai faut-il accepter pour disposer de plusieurs images de la même trace ?

### 5.1 Le délai de l'image compte davantage que son nombre

Huit zones ont été comparées selon deux configurations :

- un z-score calculé sur une seule image postérieure, disponible à environ 2,5 jours après l'événement ;
- un test t calculé sur trois images de la même orbite, dont la dernière devient disponible environ 8,5 jours après l'événement.

La comparaison porte donc sur un arbitrage concret : obtenir rapidement un premier résultat ou attendre davantage d’images pour mieux caractériser la période postérieure.

Le z-score à image unique est calculé à partir de l'écart entre l'observation postérieure et la moyenne historique, normalisé par l'écart-type de la période de référence :

$$z = \frac{x_{\text{post}} - \bar{x}_{\text{pré}}}{s_{\text{pré}}}$$

Le test t sur plusieurs images utilise au contraire les moyennes des deux périodes et leurs variances :

$$t = \frac{\bar{x}_{\text{post}} - \bar{x}_{\text{pré}}}{\sqrt{\dfrac{s^2_{\text{post}}}{n_{\text{post}}} + \dfrac{s^2_{\text{pré}}}{n_{\text{pré}}}}}$$

Le premier score est donc disponible plus tôt, mais avec une seule observation postérieure. Le second bénéficie d'une estimation de la variabilité post-événement, mais exige plusieurs passages de la même orbite.

![Figure 7](figures/figure_7.png)

**Figure 7 — Une seule image après l'événement : l'arbitrage, chiffré. À gauche, ce que l'image unique coûte zone par zone (AUC du z-score à 1 image contre le test de Welch à 3 images). À droite, ce que le passage d'une à trois images rapporte en délai : 2,5 jours contre 8,5 jours, pour une cible opérationnelle de 48 heures.**

La figure montre que l'image unique ne produit pas systématiquement le meilleur classement. À AOI02, par exemple, le z-score obtient une AUC d'environ 0,74, tandis que le test de Welch atteint environ 0,72. À l'inverse, dans plusieurs zones, l'utilisation de trois images postérieures améliore légèrement le classement. Les différences restent toutefois limitées et varient selon les zones.

Le gain du test à plusieurs images doit être mis en regard de son coût temporel. Dans l'expérience représentée à droite, le passage d'une image à trois images retarde le résultat d'environ 2,5 jours à environ 8,5 jours. Le délai supplémentaire est donc de l'ordre de six jours, alors que l'amélioration de l'AUC n'est ni systématique ni suffisamment importante pour justifier automatiquement cette attente dans une situation de première évaluation.

Pour une cellule qui doit agir dans les 24 à 48 heures, le score à image unique est le plus compatible avec le délai. Il doit être présenté comme un premier indicateur, puis enrichi ou corrigé lorsque les acquisitions suivantes deviennent disponibles.

Le test à plusieurs images conserve un intérêt pour une phase de consolidation. Il peut confirmer ou nuancer le premier classement, notamment lorsque la première image est affectée par une observation atypique, une condition météorologique résiduelle ou une variation locale difficile à interpréter. La chaîne doit donc être conçue comme progressive :

1. produire un premier signal dès qu'une image post-événement exploitable est disponible ;

2. le comparer à la référence historique ;

3. actualiser le classement lorsque de nouvelles images arrivent ;

4. confronter les secteurs prioritaires à l'imagerie optique, à l'observation aérienne ou aux informations de terrain.

Le radar ne remplace donc pas l’évaluation détaillée ; il permet de commencer à hiérarchiser les secteurs avant que cette évaluation soit disponible.

### 5.2 La méthode est-elle transposable aux cyclones, aux séismes et aux laves torrentielles ?

La figure compare deux bâtiments visiblement très endommagés après des catastrophes différentes. À Black River, après le cyclone Melissa, la rétrodiffusion radar baisse ; à Catia La Mar, après le séisme du 24 juin 2026, elle augmente. Il serait pourtant faux d'attribuer un signe à chaque type de catastrophe : d'autres bâtiments étudiés après Melissa présentent une hausse, et d'autres bâtiments étudiés après le séisme présentent une baisse. La planche illustre donc une propriété de la méthode (chercher un changement dans les deux sens) et non une signature propre au cyclone ou au séisme.

À Black River, les images postérieures montrent la disparition de la toiture et des débris autour du bâtiment ; UNOSAT l'avait signalé comme dommage à évaluer. Pour l'orbite 150, la moyenne de rétrodiffusion passe de +0,98 dB avant le cyclone à −8,34 dB après, soit −9,32 dB. La rupture persiste dans les acquisitions suivantes. L'autre orbite couvrant le site ne présente pas une baisse comparable. Cette différence entre directions de visée est compatible avec la disparition d'un mécanisme de réflexion lié à la géométrie d'une façade, sans permettre de l'identifier avec certitude.

À Catia La Mar, le bâtiment est classé *Destroyed* par Copernicus EMS. La variation observée sur l'orbite 25 est inverse : la moyenne passe de −13,0 dB à −8,8 dB, soit +4,22 dB. Une modification de la rugosité et de la disposition des matériaux après l'effondrement peut contribuer à cette hausse. Ici encore, l'image radar mesure le changement de la scène ; elle ne dit pas, à elle seule, quelle partie du bâtiment l'a produit.

![Figure 8](figures/figure_8.png)

**Figure 8 — Deux bâtiments fortement endommagés, deux sens de variation radar.** En haut, Black River après le cyclone Melissa : −9,32 dB sur l'orbite 150. En bas, Catia La Mar après le séisme du 24 juin 2026 : +4,22 dB sur l'orbite 25. Les courbes montrent la rétrodiffusion VV avant et après chaque événement ; la bande verte représente la moyenne et un écart-type de la période antérieure, le trait rouge la moyenne postérieure. Sources : calculs de l'auteur ; images Maxar Open Data et 2026 © Vantor Open Data ; orthophotographie Atlas Logistique / UNDAC.

Ces exemples justifient l’emploi de la valeur absolue : ni une hausse ni une baisse ne peut être écartée a priori. Ils ne démontrent pas que tous les cyclones et séismes sont détectés avec la même fiabilité. À l'échelle du bâtiment, l'interprétation dépend encore de l'orbite, de la résolution et de ce que le pixel inclut autour de la construction. La comparaison avec les images et les observations de terrain reste indispensable.

**Hypothèse d'interprétation.** À Black River, la forte baisse de rétrodiffusion sur l'orbite 150, absente sur l'orbite 113, est compatible avec la perte d'un double rebond entre une façade orientée vers le radar et le sol. La persistance de la baisse plusieurs mois après le cyclone rend moins convaincante l'hypothèse d'une simple nappe d'eau temporaire. Ni l'une ni l'autre de ces observations ne permet toutefois d'attribuer avec certitude le signal à la façade : les pixels couvrent aussi les abords du bâtiment, et d'autres changements de surface peuvent modifier la rétrodiffusion. À Catia La Mar, la hausse pourrait, à l'inverse, être liée à des surfaces devenues plus rugueuses après l'effondrement, notamment des gravats. Cette explication reste elle aussi une hypothèse, et non une identification directe des matériaux par Sentinel-1.

Une troisième catastrophe, d'un type encore différent, a été examinée. Le 26 août 2026, une vidange brutale de lac glaciaire a déclenché une lave torrentielle dans les districts de Rasuwa et Nuwakot, au Népal — activation Copernicus EMSR927. Le mode de destruction n'est ici ni le vent ni la secousse : la coulée emporte et ensevelit, et elle transforme la scène entière sur son passage.

Le relief y est par ailleurs extrême. La pente médiane de la zone atteint 32,7 degrés, et 28,5 % du terrain dépasse 39 degrés, soit l'angle d'incidence de Sentinel-1 ; au-delà, le radar replie le relief sur lui-même et le pixel ne mesure plus une surface stable. La méthode y fonctionne néanmoins, et mieux que sur les deux autres aléas — l'aire sous la courbe atteint 0,85 à 0,90 sur les routes et les ponts, dont la section 5.6 rend compte. Ce résultat ne doit pas se lire comme une supériorité du radar en montagne, mais comme l'effet d'un aléa qui modifie la totalité de la surface qu'il traverse.

La première image Sentinel-1 exploitable arrive à J+2,52, c'est-à-dire au même délai qu'en Jamaïque. Cette campagne ne renseigne donc pas sur le seuil de délai étudié en section 5.1 ; elle renseigne sur la transposition à un troisième mode de destruction.

### 5.3 Effet du mode d'agrégation dans les cas étudiés

Le score est calculé au pixel, mais l’objet évalué est le bâtiment. Il faut donc résumer les valeurs contenues dans chaque emprise sans perdre le type de signal que l’on cherche à conserver. Plusieurs options ont été comparées :

- la moyenne des pixels ;
- le maximum ;
- le centile 75 ;
- le centile 90.

Si Tᵢ désigne la valeur du score pour le pixel i appartenant à un bâtiment, les agrégations principales s'écrivent :

$$T_{\text{moy}} = \frac{1}{m} \sum_{i=1}^{m} T_i$$

$$T_{\max} = \max_{1 \le i \le m} T_i$$

Les centiles T₇₅ et T₉₀ correspondent respectivement aux valeurs en dessous desquelles se situent 75 % et 90 % des scores de pixels de l'emprise.

![Figure 10](figures/figure_10.png)

**Figure 10 — Sur le bâti, l'ordre des modes d'agrégation change d'une campagne à l'autre.** À gauche, le séisme du Venezuela, évalué sur 288 677 bâtiments répartis dans deux communes et plus : le maximum devance la moyenne de 0,023. À droite, le cyclone Melissa en Jamaïque, sur deux zones UNOSAT seulement : les quatre modes tiennent dans 0,005, et l'écart n'est pas significatif. Le réglage se décide donc par type d'objet et non par aléa — le maximum l'emporte aussi sur les ponts népalais, la moyenne sur les routes, sur les deux campagnes mesurables. Les valeurs sont portées par des points et non par des barres : une barre se lit par sa longueur et devrait partir de zéro, ce qu'un axe resserré sur cinq millièmes ne permet pas. Ces chiffres sont antérieurs à la réévaluation du 1er octobre 2026 et restent à reprendre dans la convention actuelle. Calculs de l'auteur.

Dans l’échantillon vénézuélien, qui comprend 288 677 bâtiments répartis dans au moins deux communes, le maximum obtient l’AUC la plus élevée : 0,749. Il est suivi du centile 90, à 0,742, du centile 75, à 0,735, puis de la moyenne, à 0,726.

Le maximum semble ici favoriser la détection de bâtiments dont une partie seulement de l'emprise est fortement modifiée. Si un bâtiment s'effondre de manière partielle, quelques pixels peuvent porter l'essentiel du signal, tandis que la moyenne de l'emprise dilue ces valeurs dans des pixels restés relativement stables.

La Jamaïque donne un résultat légèrement différent. Sur les deux zones UNOSAT disponibles, la moyenne atteint 0,607, devant le centile 75 (0,605), le centile 90 (0,603) et le maximum (0,602). L'écart entre la meilleure et la moins bonne méthode n'est que de 0,005 et il est indiqué comme non significatif dans la figure.

Cette hiérarchie ne permet donc pas de retenir une agrégation universelle. Le maximum est favorable au séisme étudié, mais la moyenne est légèrement meilleure sur le cyclone jamaïcain. Cette différence peut s'expliquer par la nature spatiale des dommages. Un séisme peut produire des changements localisés dans l'emprise d'un bâtiment, alors qu'un cyclone peut affecter plus largement la toiture, les abords, la végétation et les surfaces voisines. Dans ce second cas, une moyenne peut mieux représenter le changement général qu'un seul pixel extrême.

L'agrégation doit donc rester paramétrable. Il serait méthodologiquement incorrect de choisir le maximum parce qu'il produit le meilleur score sur le Venezuela, puis de présenter ce choix comme valable pour tous les événements. Le résultat justifie plutôt une analyse par scénario et une comparaison systématique des agrégations.

Cet ordre ne se transpose pas aux objets linéaires, et c'est un résultat en soi. Sur les ponts népalais il se retrouve intact — le maximum l'emporte, puis le centile 90, le centile 75 et la moyenne. Sur les routes il s'inverse exactement, et il s'inverse sur les deux campagnes où la mesure est possible : quelque cinq cents tronçons au Népal, trois mille en Jamaïque. Dans les quatre cas la progression est strictement monotone, ce qui écarte l'hypothèse d'un accident d'échantillonnage.

Une explication mécanique en rend compte. Le maximum de *n* valeurs bruitées croît avec *n* : plus un objet recouvre de pixels, plus il a de chances d'en contenir un seul anormalement brillant, que le maximum remonte alors en fausse alarme. Un bâtiment couvre un à quatre pixels de dix mètres, un pont quelques-uns, un tronçon de route dix à vingt. L'hypothèse concurrente — que la longueur commande à elle seule — a été testée et les données la refusent, mais le seul cas qui semblait la soutenir ne compte que vingt tronçons exploitables.

L'enjeu n'est pas du même ordre selon l'objet : un centième d'AUC sur un bâtiment, cinq au Népal et sept en Jamaïque sur une route. La recommandation est donc de régler l'agrégation **par type d'objet** — maximum pour les bâtiments et les ponts, moyenne pour les routes — plutôt que de la déduire automatiquement de la taille mesurée des objets, ce qui ferait basculer le réglage au bruit.

### 5.4 Ce que les sources permettent réellement de valider

Les Planches A et B montrent également que la validation ne consiste pas à rechercher une concordance artificielle entre toutes les sources. Chaque source n'observe pas exactement le même objet ni à la même échelle :

- l'optique très haute résolution décrit directement la forme et l'état visible du bâtiment ;
- le radar mesure une variation de rétrodiffusion ou de cohérence ;
- les produits Copernicus ou UNOSAT fournissent un classement réalisé par des analystes ;
- les signalements ChatMap documentent une observation de terrain, parfois localisée à proximité plutôt que sur le centroïde exact ;
- les produits OSU, NASA, EOS-RS ou autres correspondent à leurs propres méthodes et emprises.

Dans le cas de Black River, la convergence est forte : le classement UNOSAT, l'imagerie optique, l'avion, le drone et le signal radar décrivent tous un changement majeur. Dans le cas de Caraballeda, la convergence est plus nuancée : plusieurs sources indiquent un bâtiment endommagé, mais le signalement de terrain est décalé de 12,5 m et Copernicus ne retient pas le bâtiment. Le radar indique un changement net, mais ne permet pas à lui seul de trancher entre le bâtiment ciblé et son voisin immédiat.

Cette distinction est importante pour éviter une formulation excessive. Une source absente de la zone n'est pas une source qui conclut à l'absence de dommage. Elle peut simplement ne pas couvrir le point, ne pas avoir analysé cette emprise ou avoir retenu une autre unité spatiale. La validation porte donc simultanément sur le signal, sa localisation et le statut de la source.

### 5.5 Conséquence opérationnelle

Ces résultats conduisent à une position intermédiaire. La méthode peut produire un premier indicateur dans une fenêtre compatible avec les premières évaluations, mais elle ne doit pas être décrite comme une cartographie automatique et définitive des bâtiments endommagés.

Dans un scénario opérationnel, la sortie la plus défendable est un classement continu des emprises ou des secteurs :

- les objets présentant les variations les plus atypiques sont examinés en priorité ;
- les images optiques disponibles sont mobilisées pour confirmer la nature du changement ;
- les moyens aériens ou les observations de terrain sont orientés vers les secteurs où la décision est la plus urgente ;
- les acquisitions radar suivantes servent à mettre à jour ou à consolider le classement.

La méthode est donc utile principalement comme outil de priorisation. Sa valeur ne réside pas dans la promesse de remplacer l'expert, mais dans la possibilité de fournir rapidement une première hiérarchie lorsque l'image optique détaillée est absente, tardive ou incomplète.

La section suivante examine si l'ajout de la cohérence interférométrique améliore cette hiérarchie. Le cas de Caraballeda montre déjà que la cohérence peut révéler une rupture temporelle là où l'intensité évolue de manière ambiguë. Il reste à vérifier, à l'échelle d'un ensemble de bâtiments, si cette information apporte une capacité de classement réellement complémentaire ou si elle reproduit surtout les limites du signal d'intensité.

### 5.6 Le test t appliqué aux routes et aux ponts

Les sections 3.3 et 3.4 ont constaté un vide : le réseau routier est peu traité par les méthodes de détection de dommages, alors qu'une route coupée et un pont emporté commandent l'accès des secours autant qu'un bâtiment effondré. L'outil développé ici produit déjà une sortie pour l'un et pour l'autre, mais elle n'avait jamais pu être chiffrée. La vérité Copernicus du séisme vénézuélien ne compte que trois routes abîmées sur 24 696 entités graduées : avec trois positifs, aucune mesure de qualité n'est possible.

La lave torrentielle népalaise lève cet obstacle, et elle apporte mieux qu'un échantillon plus fourni. Copernicus y note explicitement les tronçons « sans dommage visible », et l'équipe Humanitarian OpenStreetMap y a cartographié puis noté chaque pont, debout ou emporté. **Les négatifs sont donc affirmés par un analyste, et non déduits d'une absence de signalement** — ce qui distingue cette mesure de toutes les évaluations bâtiment de ce travail, où un bâtiment non signalé est supposé intact faute de mieux.

| objet | emprise | objets | prévalence | série complète | une seule image |
|---|---|---|---|---|---|
| ponts | toutes emprises, HOT | 76 | 59,2 % | **0,885** | 0,826 |
| routes | Bidur (AOI03) | 523 | 51,6 % | **0,899** | 0,770 |
| routes | Phosretar (AOI05) | 489 | 31,9 % | **0,849** | 0,794 |
| routes | Syapru Besi (AOI01) | 20 | 70,0 % | 0,810 | 0,774 |

**Tableau 4 — Pouvoir de classement du test t sur les routes et les ponts emportés par la lave torrentielle des 26 et 27 août 2026. Les négatifs sont déclarés par l'analyste. L'image unique est celle de J+2,5. Agrégation par la moyenne pour les routes, par le maximum pour les ponts. Calculs de l'auteur.**

Ces valeurs dépassent celles mesurées sur le bâti, où ce travail se tient entre 0,50 et 0,83. Un objet linéaire est étendu et bien localisé, et une coulée l'emporte franchement, là où un bâtiment effondré peut rétrodiffuser davantage ou moins qu'avant selon sa géométrie. Avec la seule première image, acquise à J+2,5, le classement reste utile : entre 0,77 et 0,86 selon l'objet.

Deux réserves limitent cependant la portée de ce résultat. Les deux vérités sont des photo-interprétations et non des relevés de terrain ; ce ne sont pas deux sources indépendantes au sens où une visite le serait. Et la prévalence est élevée, de 32 à 77 %, parce qu'une coulée détruit tout sur son passage — la tâche de classement y est plus facile qu'après un séisme, où les dommages sont dispersés.

Une limite plus sérieuse doit enfin être posée sans détour. Sur le cyclone jamaïcain, les quatre modes d'agrégation placent l'aire sous la courbe entre 0,29 et 0,36, c'est-à-dire **sous le tirage au sort** : le classement y est inversé. Le même outil atteint 0,85 au Népal. Changer d'agrégation n'y change rien. Tant que cette inversion n'est pas comprise, la sortie routière ne peut pas être présentée comme une détection de dommage, mais seulement comme un repérage de tronçons dont la surface a changé.

![Figure 17](figures/figure_17.png)

**Figure 17 — Ce que le test t voit, et ce qu'il ne voit pas.** Deux tronçons détruits par la même lave torrentielle, le 26 août 2026, et notés tous deux *Destroyed* par Copernicus. Le critère de Rayleigh sépare leurs destins : une surface est lisse pour le radar si ses aspérités restent sous λ/(8·cos θ), soit environ 9 mm pour Sentinel-1 en bande C à 39° d'incidence. Le pont métallique, fort rétrodiffuseur, est remplacé par de l'eau — lisse à cette échelle, donc spéculaire : le signal perd 5,7 dB en douze jours. La piste, elle, passait sous un couvert végétal et se retrouve sous du sédiment nu, deux milieux rugueux qui renvoient autant l'un que l'autre ; son écart de +0,62 dB ne mesure rien, et tient d'ailleurs à la mousson plutôt qu'à la coulée. Imagerie : 2026 © Vantor Open Data, CC BY-NC 4.0. Calculs de l'auteur.

Cette planche porte une conséquence qu'il faut énoncer. **Le test t ne mesure pas un dommage mais un changement de rugosité de surface.** Il est aveugle lorsque la destruction substitue un milieu rugueux à un autre, même quand les dégâts sont totaux et visibles à l'œil nu — situation fréquente en vallée de montagne, où la végétation cède la place à des dépôts grossiers. Les aires sous la courbe obtenues plus haut sont donc tirées par les cas où le contraste de rugosité est fort.

Un second biais apparaît sur cette campagne. La période de référence couvrant douze mois, elle mélange les saisons ; or la rétrodiffusion de ces milieux suit la mousson, de −8,9 dB en août à −10,5 dB en saison sèche. Comparer une image d'août à cette moyenne annuelle fabrique un écart qui ne doit rien à l'événement. Sous un climat à mousson, la date d'acquisition de l'image postérieure pèse donc sur le résultat autant que le dommage lui-même.

## 6 Comparer les méthodes sur les mêmes objets

Comparer des méthodes n’a de sens que si elles sont évaluées sur les mêmes objets, avec les mêmes références et la même métrique. Une comparaison sur des emprises différentes peut en effet favoriser la méthode qui a traité le secteur le plus simple.

La question n’est donc pas seulement « quelle méthode obtient la meilleure AUC ? », mais aussi « sur quels bâtiments cette AUC a-t-elle été calculée ? ».

### 6.1 Pourquoi comparer sur une emprise commune ?

Une première lecture évalue chaque produit sur sa propre emprise. Elle décrit ce que l’utilisateur reçoit effectivement, mais ne permet pas de comparer directement les méthodes : les bâtiments, la prévalence des dommages et la difficulté d’interprétation peuvent différer.

L'expérience sur l'emprise commune restreint donc la comparaison aux bâtiments couverts par les méthodes évaluées. Les AUC sont calculées par commune, après centrage-réduction à l'intérieur de chaque unité administrative, puis agrégées pour obtenir une valeur moyenne comparable.

Cette précaution est importante ici, car la couverture du T-stat n’est pas uniforme dans l’activation. Dans les zones calculées, elle dépasse 95 %, mais l’outil n’a pas traité toutes les zones disponibles. Comparer sur l'emprise commune permet donc de distinguer deux questions :

- quelle méthode classe le mieux les bâtiments qu'elle couvre ;
- quelle couverture et quel produit sont effectivement disponibles pour l'utilisateur.

Il faut donc séparer pouvoir de classement et couverture. Une méthode peut être performante sur une zone restreinte, tandis qu’une autre couvre davantage de bâtiments avec une performance un peu différente.

### 6.2 Le classement sur l'emprise commune

L'intersection des produits à large emprise représente 148 159 bâtiments et 1 558 signalements Copernicus répartis dans 20 communes. Le classement obtenu est le suivant :

| Rang | Produit | AUC / Copernicus | AUC / ChatMap | Moyenne |
|---|---|---|---|---|
| 1 | Notre T-stat | 0,727 | 0,754 | 0,740 |
| 2 | OSU | 0,729 | 0,735 | 0,732 |
| 3 | NASA DRCS S2 | 0,713 | 0,719 | 0,716 |
| 4 | UNGSC | 0,651 | 0,600 | 0,625 |
| 5 | fAIr HOTOSM | 0,594 | 0,631 | 0,612 |
| 6 | UH SAIL | 0,658 | 0,469 | 0,563 |
| 7 | NASA DRCS S1 | 0,511 | 0,544 | 0,528 |
| 8 | IMPACT Initiatives | 0,496 | 0,487 | 0,491 |

Classement sur l'emprise commune aux produits à large couverture (148 159 bâtiments, 20 communes).

Le rang est établi sur la moyenne des deux références :

AUC_moyenne = (AUC_Copernicus + AUC_ChatMap) / 2

Cette moyenne ne signifie pas que Copernicus et ChatMap décrivent la même vérité. Copernicus correspond à une interprétation experte d'imagerie, tandis que ChatMap correspond à des signalements issus du terrain. Les deux références sont utilisées ici comme deux points de vue indépendants sur le dommage, et non comme des observations interchangeables.

La T-stat arrive première avec 0,740, devant OSU (0,732) et NASA DRCS S2 (0,716). Les trois valeurs restent proches : 0,024 sépare la première de la troisième. Le résultat établit donc une première place dans ce protocole, et non une supériorité générale.

L’ordre n’est pas le même lorsque chaque produit est évalué sur sa propre emprise : la T-stat passe du troisième rang au premier, tandis que NASA DRCS S2 passe de la première à la troisième place. L’emprise contribue donc fortement au classement.

Les produits à large emprise peuvent obtenir une AUC élevée en intégrant des communes peu touchées ou des zones où la séparation entre bâtiments endommagés et bâtiments intacts est plus simple. L'emprise commune est au contraire concentrée sur les secteurs couverts par tous les produits, et donc sur des zones où la comparaison est plus exigeante. Une partie de l'avance observée pour NASA DRCS S2 et OSU dans le classement individuel pouvait donc provenir du territoire évalué plutôt que de la seule qualité de la méthode.

### 6.3 Le face-à-face sur les mêmes bâtiments

Une seconde lecture consiste à comparer directement notre T-stat à chaque produit, en retenant uniquement les bâtiments couverts par les deux méthodes. Chaque adversaire est ainsi évalué sur une emprise commune avec notre outil.

| Adversaire | Bât. communs | T-stat / Cop. | Advers. / Cop. | T-stat / ChatMap | Advers. / ChatMap |
|---|---|---|---|---|---|
| OSU | 288 208 | 0,717 | 0,756 | 0,780 | 0,755 |
| NASA DRCS S2 | 173 381 | 0,735 | 0,724 | 0,778 | 0,748 |
| BDPM (reproduction) | 80 291 | 0,735 | 0,746 | 0,788 | 0,738 |
| UNGSC | 180 268 | 0,736 | 0,671 | 0,780 | 0,627 |
| EOS-RS | 29 641 | 0,689 | 0,631 | 0,787 | 0,689 |
| UH SAIL | 170 472 | 0,718 | 0,629 | 0,756 | 0,473 |
| fAIr HOTOSM | 197 582 | 0,727 | 0,583 | 0,791 | 0,651 |
| Microsoft AI for Good | 67 145 | 0,749 | 0,591 | 0,828 | 0,620 |
| NASA DRCS S1 | 180 148 | 0,736 | 0,506 | 0,780 | 0,557 |
| IMPACT Initiatives | 204 979 | 0,727 | 0,506 | 0,780 | 0,512 |
| DISHA | 32 834 | 0,722 | 0,373 | 0,879 | 0,415 |

Comparaison en face-à-face : notre T-stat contre chaque produit, sur les bâtiments couverts par les deux méthodes uniquement.

Dans ces face-à-face, la T-stat obtient une AUC supérieure à neuf produits sur onze. OSU et la reproduction BDPM font exception, mais aucun des deux ne la dépasse sur les deux références simultanément.

Ce résultat ne signifie pas que la T-stat est systématiquement meilleure : les produits n’utilisent ni les mêmes grandeurs, ni les mêmes données, ni nécessairement la même définition du dommage. Il montre qu’elle fournit un classement compétitif sur les bâtiments communs.

Le face-à-face avec IMPACT Initiatives est particulièrement instructif. Sur 204 979 bâtiments communs, notre T-stat atteint 0,727 contre Copernicus et 0,780 contre ChatMap, tandis qu'IMPACT atteint respectivement 0,506 et 0,512. Sur cette emprise commune, le produit IMPACT ne se distingue donc pas du hasard selon ces deux références.

Ce constat doit toutefois rester limité au protocole étudié. Il ne permet pas de conclure que le produit IMPACT est sans valeur dans tous les contextes, mais seulement qu'il ne discrimine pas correctement les bâtiments de cet échantillon selon les deux vérités utilisées.

### 6.4 Comparer uniquement les bâtiments présents dans tous les produits

Une troisième expérience impose que les douze produits couvrent simultanément les mêmes bâtiments. L’échantillon tombe à 5 489 bâtiments, 329 signalements Copernicus et cinq communes.

| Rang | Produit | AUC contre Copernicus |
|---|---|---|
| 1 | Notre T-stat | 0,715 |
| 2 | NASA DRCS S2 | 0,696 |
| 3 | BDPM | 0,679 |
| 4 | fAIr HOTOSM | 0,644 |
| 5 | EOS-RS | 0,617 |
| 6 | UNGSC | 0,608 |
| 7 | IMPACT Initiatives | 0,605 |
| 8 | Microsoft AI for Good | 0,558 |
| 9 | OSU | 0,548 |
| 10 | NASA DRCS S1 | 0,526 |
| 11 | UH SAIL | 0,465 |
| 12 | DISHA | 0,410 |

Classement sur l'intersection stricte des douze produits (5 489 bâtiments, 5 communes, prévalence ≈ 6 %).

La T-stat reste première, mais cette lecture est secondaire. L’échantillon est trop restreint et la zone commune est déterminée par les trois produits aux emprises les plus petites. La prévalence des bâtiments endommagés y atteint environ 6 %, contre 0,28 % sur l'ensemble de l'activation.

L'effondrement d'OSU à 0,548 peut suggérer que la cohérence discrimine moins bien dans une zone où les dommages sont très nombreux et spatialement concentrés. Si la cohérence est dégradée sur une grande partie de la zone, elle peut perdre sa capacité à distinguer les bâtiments réellement touchés des bâtiments voisins. Cette interprétation reste toutefois une hypothèse : cinq communes ne suffisent pas à l'établir.

### 6.5 Que peut-on conclure du classement ?

Trois conclusions peuvent être retenues.

Premièrement, le classement réalisé sur les emprises propres à chaque produit reste utile pour décrire les résultats effectivement livrés aux utilisateurs. Il ne répond toutefois pas à la question « quelle méthode est la meilleure ? », car les méthodes ne sont pas évaluées sur les mêmes bâtiments.

Deuxièmement, sur l'emprise commune, notre T-stat obtient la meilleure moyenne entre Copernicus et ChatMap, devant OSU et NASA DRCS S2. Les trois méthodes restent proches, ce qui impose une interprétation prudente.

Troisièmement, publier les deux classements est préférable à n'en publier qu'un seul. Le classement individuel mesure la performance dans le territoire traité par chaque producteur ; le classement commun mesure plus directement la différence entre méthodes à territoire comparable. Les deux informations sont nécessaires pour évaluer à la fois la qualité du signal et la couverture réellement disponible.

Cette comparaison conforte le choix de ne pas présenter le T-stat comme un outil de classification définitive. Sa valeur est celle d'une méthode ouverte, reproductible et compétitive, capable de produire un score continu sur une emprise choisie, et donc d'être évaluée et comparée de manière transparente.

La section suivante examine si les résultats peuvent être améliorés en combinant plusieurs produits ou plusieurs grandeurs radar, notamment l'intensité et la cohérence. Cette étape doit cependant respecter une règle essentielle : les poids ou les règles de fusion ne doivent pas être choisis sur la même vérité que celle utilisée pour annoncer la performance finale. Sinon, la méthode se noterait sur sa propre copie.

## 7 Ce que l’emprise d’évaluation change au classement

La section précédente comparait les produits sur une emprise commune. Ici, l’objectif est différent : mesurer dans quelle mesure le périmètre d’évaluation modifie le classement.

Le classement dépend en partie des bâtiments évalués. Chaque méthode est donc comparée selon deux configurations :

- une première fois sur sa propre emprise, c'est-à-dire sur les bâtiments effectivement couverts par le produit ;
- une seconde fois sur l'emprise commune aux méthodes comparées, soit 148 159 bâtiments.

Dans les deux cas, l'indicateur présenté est la moyenne des AUC calculées par commune pour les deux références disponibles, Copernicus EMS et ChatMap :

AUC_moyenne = (AUC_Copernicus + AUC_ChatMap) / 2

Cette moyenne ne transforme pas Copernicus EMS et ChatMap en une vérité unique. Elle résume deux évaluations distinctes : l’une fondée sur l’interprétation d’images, l’autre sur des signalements de terrain.

![Figure 11](figures/figure_11.png)

**Figure 11 — Jugés sur les mêmes bâtiments, les rangs changent. Chaque produit est représenté deux fois : noté sur son emprise propre (gris) et noté sur l'emprise commune de 148 159 bâtiments (bleu). La ligne pointillée marque le niveau du hasard (0,5). Notre T-stat, en tête, est le seul produit dont le score varie à peine entre les deux configurations.**

La figure montre que ces deux modes d’évaluation ne donnent pas toujours le même classement. Le T-stat obtient une valeur très proche dans les deux configurations, autour de 0,74. À l'inverse, OSU atteint environ 0,80 lorsqu'il est évalué sur sa propre emprise, mais environ 0,73 sur l'emprise commune. NASA DRCS S2 suit la même tendance : son score passe d'environ 0,78 sur sa propre emprise à environ 0,72 sur les bâtiments communs.

Ces écarts ne prouvent pas qu’un produit perd intrinsèquement en performance sur l’emprise commune. Ils montrent d’abord que les emprises propres n’ont pas toutes le même niveau de difficulté. Un produit évalué principalement sur des secteurs où les dommages sont plus visibles ou plus facilement séparables des bâtiments intacts peut obtenir une AUC élevée sans que cela traduise uniquement la qualité de son algorithme.

L’emprise commune modifie donc parfois le classement. Notre T-stat, qui n'est pas premier lorsqu'il est évalué dans le protocole propre à chaque produit, arrive en première position lorsque toutes les méthodes sont jugées sur les mêmes bâtiments. OSU et BDPM restent proches, tandis que plusieurs autres produits se déplacent sensiblement dans le classement.

Le cas d'OSU est particulièrement instructif. Son AUC propre est élevée, autour de 0,80, mais tombe à environ 0,73 sur l'emprise commune. Cette baisse indique que sa performance dépend fortement du territoire couvert dans son évaluation propre. Le produit reste compétitif, mais son rang initial ne peut pas être interprété indépendamment de son emprise.

La stabilité relative de la T-stat entre les deux configurations suggère une dépendance moindre à la sélection des bâtiments. Elle ne démontre pas une supériorité générale, mais rend le résultat plus stable dans cette expérience.

La ligne verticale à 0,5 représente le niveau du hasard. Les méthodes situées à droite de cette ligne discriminent mieux les bâtiments classés positifs et négatifs que ne le ferait un classement aléatoire. Les produits proches de 0,5, comme IMPACT dans la comparaison commune, ne fournissent en revanche pas de classement utile sur cet échantillon.

### 7.1 Emprise propre, emprise commune et intersection stricte : trois évaluations différentes

Les deux évaluations répondent à des questions différentes.

Le classement sur l'emprise propre répond à la question :

« Quelle performance le produit fournit-il sur le territoire qu'il a choisi ou qu'il a effectivement traité ? »

Il est utile pour évaluer l'offre réellement disponible pour un utilisateur. Il tient compte implicitement de la couverture, du masquage, des choix de production et des zones retenues par le fournisseur.

Le classement sur l'emprise commune répond à une autre question :

« Quelle méthode classe le mieux les mêmes bâtiments, lorsque les différences de territoire sont neutralisées ? »

Il est plus adapté à la comparaison algorithmique, mais il réduit nécessairement l'échantillon aux zones couvertes par tous les produits considérés.

Aucun classement ne doit être présenté seul. Publier uniquement le classement sur les emprises propres favoriserait les méthodes évaluées sur les territoires les plus favorables. Publier uniquement le classement commun masquerait une information opérationnelle importante : un produit peut obtenir une bonne performance sur l'emprise commune tout en couvrant très peu de bâtiments dans une situation réelle.

Une comparaison complète doit donc présenter simultanément :

- la performance sur l'emprise propre ;
- la performance sur l'emprise commune ;
- le nombre de bâtiments couverts ;
- le nombre de positifs disponibles pour la validation.

### 7.2 Une conséquence pour l'interprétation de l'AUC

L’AUC mesure un pouvoir de classement, pas une probabilité de dommage. Elle peut changer lorsque la population évaluée change, même si l’algorithme reste identique.

Formellement, l'AUC peut être interprétée comme la probabilité qu'un bâtiment positif reçoive un score supérieur à celui d'un bâtiment négatif tiré au hasard :

AUC = P( S⁺ > S⁻ )

où S⁺ désigne le score d'un bâtiment positif et S⁻ celui d'un bâtiment négatif.

Cela explique pourquoi deux AUC calculées sur des emprises différentes ne sont pas directement comparables. Les distributions de scores, la proportion de positifs, la nature des dommages et les conditions d'observation peuvent toutes changer.

L’emprise commune ne rend pas la comparaison parfaite, mais elle réduit une source majeure de différence : les méthodes sont évaluées sur les mêmes bâtiments et face aux mêmes références.

### 7.3 La limite de cette expérience

L'emprise commune ne constitue pas nécessairement un échantillon représentatif de tous les bâtiments de l'activation. Elle correspond aux bâtiments couverts simultanément par les méthodes comparées. Les produits à petite emprise peuvent donc réduire l'intersection à une zone particulière, parfois plus proche du cœur sinistré que le reste du territoire.

Cette limitation est visible dans l'intersection stricte des douze produits : l'échantillon tombe à 5 489 bâtiments répartis dans seulement cinq communes. Le résultat confirme le bon classement du T-stat, mais il ne peut pas être utilisé comme une validation générale en raison de la faible emprise et du nombre réduit de communes.

L'expérience ne permet donc pas d'affirmer que le T-stat est meilleur dans tous les contextes. Elle permet de dire quelque chose de plus précis : lorsque plusieurs méthodes sont comparées sur les mêmes bâtiments, le classement obtenu peut être très différent de celui produit par les emprises propres ; dans l'échantillon étudié, le T-stat devient le meilleur des produits comparés selon la moyenne des deux références.

Cette conclusion justifie la présentation des deux lectures. Elle rappelle surtout qu'un classement de méthodes de détection n'est jamais indépendant du territoire sur lequel il est calculé.

### Transition vers la section suivante

La comparaison sur emprise commune place notre T-stat parmi les méthodes les plus compétitives, mais elle ne répond pas encore à la question de savoir si plusieurs signaux peuvent être combinés. La section suivante examine donc la fusion entre l'intensité radar du T-stat et des méthodes fondées sur la cohérence interférométrique. L'objectif est de déterminer si ces deux grandeurs apportent une information complémentaire, et non simplement de produire un score plus complexe.

## 8 Fusionner les sources : le gain dépend de l’usage

Les sections précédentes comparaient les produits comme des alternatives. Cette section les considère comme des sources complémentaires : la question devient celle du gain apporté par leur combinaison et de la règle la plus utile pour l’usage visé.

L’intensité radar et la cohérence interférométrique ne classent pas exactement les mêmes bâtiments. Cette différence peut être exploitée, à condition que la fusion améliore réellement le classement plutôt que d’ajouter seulement de la complexité.

L’objectif est donc de vérifier si deux informations radar partiellement différentes classent mieux les bâtiments que chacune prise isolément.

### 8.1 Principe de la fusion

Les produits ne fournissent pas nécessairement des scores comparables sur une même échelle. Avant fusion, chaque score est donc converti en rang normalisé à l’intérieur de chaque commune et de chaque produit.

Pour un bâtiment i, si rᵢ,ₖ désigne le rang normalisé attribué par le produit k, la moyenne simple de K produits est :

$$F_{\text{moy}} = \frac{1}{K} \sum_{k=1}^{K} r_{i,k}$$

Pour deux produits, le T-stat et une méthode de cohérence, cette expression devient :

$$F_{\text{moy}} = \frac{r_{i,T} + r_{i,\text{coh}}}{2}$$

Une moyenne pondérée peut également être calculée :

$$F_{\text{pond}} = \frac{w_T\,r_{i,T} + w_{\text{coh}}\,r_{i,\text{coh}}}{w_T + w_{\text{coh}}}$$

Les poids sont proportionnels à la performance excédant le hasard, soit :

$$w_k \propto \bigl( \mathrm{AUC}_k - 0{,}5 \bigr)$$

Les poids sont calculés avec l’autre référence : une performance mesurée contre Copernicus fixe les poids évalués contre ChatMap, et inversement. Cette séparation limite le risque de régler la fusion directement sur la vérité utilisée pour la tester.

Deux règles alternatives ont également été testées : la conjonction, qui retient le score le moins élevé,

$$F_{\text{AND}} = \min\bigl( r_{i,T},\; r_{i,\text{coh}} \bigr)$$

et la disjonction, qui retient le score le plus élevé,

$$F_{\text{OR}} = \max\bigl( r_{i,T},\; r_{i,\text{coh}} \bigr)$$

La disjonction suit une logique d’alerte : une seule source suffit. La conjonction suit une logique de confirmation : les deux sources doivent aller dans le même sens.

### 8.2 La fusion ciblée du T-stat et de la cohérence

L'expérience principale porte sur la fusion du T-stat avec OSU, produit fondé sur la cohérence, sur une emprise commune de 148 159 bâtiments répartis dans 20 communes.

| Score | AUC Copernicus | AUC ChatMap | Moyenne |
|---|---|---|---|
| Fusion T-stat × OSU, moyenne pondérée | 0,752 | 0,775 | 0,764 |
| Fusion T-stat × OSU, moyenne simple | 0,752 | 0,775 | 0,763 |
| Fusion T-stat × OSU, conjonction | 0,741 | 0,777 | 0,759 |
| Notre T-stat seul | 0,727 | 0,754 | 0,740 |
| OSU seul | 0,729 | 0,735 | 0,732 |
| NASA DRCS S2 seul | 0,713 | 0,719 | 0,716 |
| Fusion T-stat × OSU, disjonction | 0,700 | 0,694 | 0,697 |

Fusion T-stat × OSU sur l'emprise commune (148 159 bâtiments, 20 communes), comparée aux produits pris isolément.

Dans cette expérience, la fusion améliore le classement par rapport à chacun des deux produits pris séparément. Par rapport au T-stat seul, le gain moyen est de :

ΔAUC = 0,7635 − 0,7403 = 0,0232

Par rapport à OSU seul, le gain est de :

ΔAUC = 0,7635 − 0,7324 = 0,0311

Le gain apparaît face aux deux références, ce qui est plus convaincant qu’un gain observé contre une seule source. Il reste cependant attaché à cette emprise et à ce protocole.

![Figure 12](figures/figure_12.png)

**Figure 12 — Deux produits radar capturent l'essentiel du gain de la fusion. La fusion des douze produits (0,772) et la fusion à deux termes T-stat × OSU (0,763) restent proches, loin devant chaque produit pris isolément.**

La fusion large de douze produits obtient une AUC moyenne de 0,7720. La fusion T-stat × OSU atteint 0,7635. L'écart entre les deux est donc seulement :

0,7720 − 0,7635 = 0,0085

Le gain du T-stat seul par rapport à sa valeur initiale est de 0,0232, tandis que le gain de la fusion à douze produits est de :

0,7720 − 0,7403 = 0,0317

Dans cette comparaison, la fusion à deux termes récupère donc environ :

(0,0232 / 0,0317) × 100 ≈ 73 %

du gain obtenu avec les douze produits. Cette proportion est importante pour l'usage opérationnel : deux sources radar gratuites, disponibles dans une chaîne maîtrisable, capturent l'essentiel de l'amélioration obtenue par une fusion beaucoup plus lourde.

### 8.3 La moyenne est préférable à la disjonction

Les trois règles de fusion ne produisent pas le même résultat.

![Figure 13](figures/figure_13.png)

**Figure 13 — Fusionner avec la cohérence : moyenner gagne, retenir le plus alarmant perd. Sur les trois paires testées (T-stat × OSU, × BDPM, × EOS-RS), la moyenne et la moyenne pondérée (en vert) dépassent systématiquement le T-stat seul ; la conjonction et la disjonction (en orange) restent en dessous.**

La moyenne simple et la moyenne pondérée donnent presque le même résultat : 0,7632 contre 0,7635, soit moins de 0,001 d’écart. Le réglage des poids apporte donc un gain négligeable dans cette configuration.

La conjonction obtient une valeur légèrement inférieure, à 0,7588, mais reste proche de la moyenne. Elle exige implicitement une confirmation par les deux méthodes et réduit donc une partie des fausses alertes, au prix d'une perte de sensibilité.

La disjonction dégrade fortement le classement : son AUC moyenne est de 0,6966, en dessous de la T-stat seule, d’OSU seul et de leur moyenne. Elle transmet en effet les faux positifs propres à chacune des méthodes.

La disjonction produit les pertes suivantes par rapport au T-stat seul :

| Configuration | T-stat seul | Disjonction | Écart |
|---|---|---|---|
| T-stat × OSU, emprise commune | 0,7403 | 0,6966 | −0,0437 |
| T-stat × OSU, emprise propre | 0,7489 | 0,6971 | −0,0518 |
| T-stat × BDPM | 0,7613 | 0,7313 | −0,0300 |
| T-stat × EOS-RS | 0,7379 | 0,7238 | −0,0141 |

Coût de la disjonction (retenir l'avis le plus alarmant) par rapport au T-stat seul, sur quatre configurations.

La règle consistant à retenir le signal le plus alarmant peut sembler prudente, mais elle confond prudence et accumulation des faux positifs. Dans une situation où la capacité de vérification est limitée, elle peut surtout augmenter le nombre d'adresses à examiner sans améliorer le classement des bâtiments réellement touchés.

### 8.4 Le gain se confirme avec plusieurs partenaires

La fusion ne repose pas uniquement sur le cas T-stat × OSU. Des expériences analogues ont été réalisées avec trois partenaires de cohérence et sur leurs emprises communes respectives.

| Paire | Bâtiments | T-stat seul | Partenaire seul | Meilleure fusion | Gain |
|---|---|---|---|---|---|
| T-stat × OSU | 288 208 | 0,749 | 0,755 | 0,772 | +0,017 |
| T-stat × BDPM | 80 291 | 0,761 | 0,742 | 0,772 | +0,010 |
| T-stat × EOS-RS | 29 641 | 0,738 | 0,660 | 0,746 | +0,009 |
| T-stat × trois partenaires | 13 832 | 0,743 | — | 0,757 | +0,014 |

Gain de la fusion avec trois partenaires de cohérence distincts, chacun sur son emprise commune avec le T-stat.

Le gain est positif dans les quatre configurations. Il reste modeste, entre environ un et deux centièmes, mais se maintient malgré les changements de partenaire et d’emprise.

La cohérence n’est donc pas toujours meilleure que l’intensité ; dans deux configurations, le partenaire seul est moins performant. Le gain vient de la complémentarité des signaux et des erreurs, non d’une supériorité générale d’une source.

### 8.5 Deux usages, deux règles de décision

Une seule AUC ne suffit pas à décrire l’utilité opérationnelle. Deux usages peuvent conduire à des réglages différents :

1. envoyer des équipes vers les bâtiments les plus suspects ;

2. parcourir une zone aussi largement que possible sans manquer trop de bâtiments touchés.

Ces deux objectifs n'impliquent pas la même règle de sélection.

![Figure 14](figures/figure_14.png)

**Figure 14 — Deux usages, deux réglages opposés. À gauche, la précision au sommet du classement (envoyer des équipes) : la fusion des douze produits domine nettement dans les premiers rangs. À droite, le rappel cumulé selon la part de zone relue (ne rien manquer) : la fusion T-stat × OSU atteint 90 % de rappel pour une part de zone à relire plus faible que le T-stat seul.**

### Envoyer des équipes : privilégier la précision au sommet

Lorsque le nombre d'adresses pouvant être vérifiées est très limité, l'objectif est de maximiser la proportion de bâtiments effectivement endommagés parmi les premières adresses visitées. La courbe de gauche représente cette précision en fonction du nombre d'adresses retenues, classées du score le plus élevé au plus faible.

La référence horizontale correspond au hasard, soit environ 1,1 % dans cet échantillon. Les méthodes restent au-dessus de cette référence lorsqu'elles ciblent prioritairement les scores les plus élevés, mais leurs comportements diffèrent dans les tout premiers rangs.

La fusion des douze produits obtient la précision la plus élevée au sommet de la courbe. Elle concentre davantage de bâtiments endommagés dans les premières adresses visitées. La fusion T-stat × OSU améliore également le T-stat seul, mais son avantage dépend du nombre d'adresses retenues. Le T-stat seul conserve une courbe plus progressive.

Cette lecture correspond à un usage de type :

« Nous ne pouvons vérifier que quelques dizaines ou quelques centaines de bâtiments : lesquels visiter en premier ? »

Dans ce cas, une fusion peut être intéressante même si son AUC globale n'est pas très supérieure, à condition que le gain se situe bien dans les premiers rangs.

### Ne rien manquer : privilégier le rappel

Lorsque l'objectif est de retrouver la majorité des bâtiments endommagés, la question devient différente : quelle proportion de bâtiments positifs est récupérée lorsque l'on accepte de relire une part croissante de la zone ?

La courbe de droite représente le rappel cumulé :

Rappel(q) = (bâtiments positifs retrouvés dans les q % premiers) / (total des bâtiments positifs)

Le point de comparaison horizontal fixé à 90 % indique la part de bâtiments endommagés retrouvée lorsque la zone entière n'est pas encore entièrement relue.

La fusion T-stat × OSU atteint environ 90 % de bâtiments retrouvés avec une part de zone relue inférieure à celle nécessaire pour le T-stat seul. Elle est donc particulièrement adaptée à un usage de balayage : réduire le volume à examiner tout en conservant une couverture élevée des bâtiments touchés.

La fusion des douze produits atteint également de bonnes performances, mais son avantage doit être rapporté à son coût de production et à la disponibilité réelle des produits. Une fusion utilisant douze sources hétérogènes peut être performante dans une analyse rétrospective, mais difficile à reproduire dans les premières heures d'une catastrophe.

### 8.6 Ce que l'expérience permet de conclure

La fusion de l'intensité et de la cohérence améliore le classement, mais le gain reste modeste. La conclusion la plus solide n'est donc pas que la fusion transforme radicalement la méthode, mais qu'elle apporte une amélioration mesurable et reproductible lorsque les deux signaux sont combinés par moyenne.

Les résultats conduisent à retenir les principes suivants :

- la moyenne des rangs est préférable à la disjonction ;
- la moyenne simple est presque aussi performante que la moyenne pondérée ;
- la conjonction peut être utile lorsqu'on cherche une confirmation stricte, mais elle réduit la sensibilité ;
- la fusion à deux termes capture environ les trois quarts du gain obtenu avec douze produits ;
- le choix du réglage dépend de l'usage : précision maximale pour envoyer des équipes, rappel maximal pour balayer une zone.

La fusion ne change toutefois pas la nature du résultat. Elle produit toujours un classement de changements radar, et non une classification certaine des bâtiments endommagés. Elle doit donc rester présentée comme un outil d'aide à la priorisation, associé à une vérification optique, aérienne ou de terrain.

## 9 Ce que mesure réellement la cohérence

La cohérence interférométrique ne mesure pas la brillance d’une surface, mais la stabilité de son organisation électromagnétique entre deux acquisitions. Lorsque les diffuseurs restent comparables, la cohérence tend à rester élevée ; lorsqu’ils changent, elle diminue.

Cette propriété paraît adaptée à la détection des remaniements. Un effondrement, une toiture disparue ou une structure déformée peuvent modifier les diffuseurs observés. Mais une baisse peut aussi venir d’un faible rapport signal sur bruit, de la géométrie, de l’humidité, de la végétation ou d’un intervalle temporel trop long.

La question n’est donc pas seulement de savoir si la cohérence baisse, mais si cette baisse permet de classer les bâtiments touchés au-dessus des autres.

### 9.1 Reproduire les méthodes publiées

Trois familles de méthodes de cohérence ont été reproduites à partir des formules publiées :

- DPM1, fondée sur une différence entre cohérence pré- et post-événement ;
- DPM2, fondée sur une mesure de rareté ou d'écart normalisé, dont une forme gaussienne correspond à la méthode employée par OSU ;
- BDPM, fondée sur la comparaison entre une cohérence pré-événement et une cohérence post-événement, avec une sortie continue ou binaire selon le réglage.

La reproduction porte sur quinze zones syriennes, 110 159 bâtiments et 2 247 signalements UNOSAT. Les huit paires utilisées ont toutes un intervalle de douze jours. Cette homogénéité évite de confondre l’effet de la durée entre acquisitions avec celui de la méthode.

Les valeurs utilisées proviennent de la cohérence ASF HyP3 à 40 m, sur une trace descendante Sentinel-1. Les méthodes sont donc évaluées dans des conditions identiques, à partir des mêmes couples d'images.

### 9.2 Ce que montrent les cartes

La Figure 15 permet de comparer visuellement les sorties.

![Figure 15](figures/figure_15.png)

**Figure 15 — Les méthodes de cohérence sur la même zone, après le séisme du 25 juin 2026 (Caraballeda, 1,4 km de côté). Les deux premières vignettes sont la donnée d'entrée ; les cinq suivantes, ce que chaque méthode en tire. Sous chacune : le nombre de valeurs distinctes, et la part de la fenêtre saturée au maximum, ce qui sépare une carte qui ordonne les bâtiments d'une carte qui les déclare tous.**

Les deux premières vignettes présentent les données d'entrée : la cohérence moyenne avant le séisme et la cohérence qui lui est postérieure. Les cinq vignettes suivantes montrent les sorties des différentes méthodes.

La cohérence brute post-événement contient de nombreuses valeurs distinctes et conserve une structure spatiale relativement riche. Elle peut donc ordonner les bâtiments selon des niveaux différents de signal. À l'inverse, certaines transformations réduisent fortement la diversité des valeurs :

- DPM2 selon la formule exacte ne conserve que six valeurs distinctes, dont 96 % des pixels atteignent la valeur maximale ;
- la forme gaussienne de DPM2 conserve davantage de valeurs, mais 76 % des pixels atteignent encore le maximum ;
- la sortie binaire publiée de BDPM ne conserve qu'une seule valeur distincte sur la zone : elle déclare les bâtiments selon une règle oui/non, sans classement continu.

Cette différence est essentielle. Une sortie binaire peut signaler des secteurs, mais elle ne permet plus d’ordonner finement les bâtiments. Or l’AUC évalue précisément cette capacité de classement.

Pour un score continu Sᵢ, l'AUC peut être interprétée comme :

AUC = P( S⁺ > S⁻ )

où S⁺ est le score d'un bâtiment positif et S⁻ celui d'un bâtiment négatif. Si presque toute la zone possède la même valeur, le score ne peut plus fournir un classement détaillé. Il devient essentiellement une déclaration uniforme.

La cohérence publiée sous une forme binaire ne doit donc pas être comparée directement à un score continu comme s'ils portaient la même quantité d'information. Une sortie binaire peut atteindre une performance utile pour une règle de décision donnée, mais elle perd l'information nécessaire pour prioriser les objets les uns par rapport aux autres.

### 9.3 Les résultats sur quinze zones

La Figure 16 présente les AUC groupées, centrées par zone, sur les quinze zones syriennes.

![Figure 16](figures/figure_16.png)

**Figure 16 — Ce que valent les méthodes de cohérence, reproduites depuis les formules publiées. La barre grise (cohérence pré-sismique seule) ne peut rien savoir de l'événement : elle donne le plancher. C'est l'écart à cette sonde, non l'AUC brute, qui mesure la détection.**

La barre grise inférieure correspond à la cohérence pré-sismique seule. Elle ne contient aucune information sur le séisme et constitue donc une sonde de confusion : si une méthode post-événement ne dépasse pas clairement cette référence, son classement peut provenir de la structure préexistante de la scène plutôt que du changement lié à l'événement.

Les résultats sont les suivants :

| Méthode | AUC groupée |
|---|---|
| DPM1 — moyenne | 0,601 |
| DPM1 — moyenne, sans appariement | 0,597 |
| DPM2 — forme gaussienne, méthode OSU | 0,595 |
| DPM2 — formule exacte | 0,593 |
| DPM1 — proche, sans appariement | 0,579 |
| DPM1 — paire la plus proche | 0,576 |
| BDPM — marge, masquée fiabilité | 0,575 |
| BDPM — marge | 0,568 |
| Cohérence co-sismique brute | 0,557 |
| BDPM — sortie binaire publiée | 0,462 |
| Cohérence pré-sismique seule | 0,458 |

AUC groupée, centrée par zone, des méthodes de cohérence reproduites sur 15 zones syriennes (110 159 bâtiments, 2 247 signalements UNOSAT).

DPM1 avec moyenne obtient la meilleure AUC, 0,601, mais le gain au-dessus du hasard reste modeste. DPM2 sous sa forme gaussienne atteint 0,595 et la cohérence co-sismique brute 0,557.

La sortie binaire publiée de BDPM obtient 0,462, donc sous le hasard dans cet échantillon. Ce résultat ne signifie pas nécessairement que la méthode est inutile dans tous les contextes. Il montre que, reproduite dans ce protocole et évaluée sur ces quinze zones, sa sortie binaire ne fournit pas un classement discriminant au-dessus des bâtiments intacts.

L’écart entre 0,601 et 0,595 est faible. Il ne justifie pas de déclarer DPM1 supérieur en général à DPM2 ou à OSU. Le résultat plus robuste est que les méthodes reproduites sont légèrement informatives, mais limitées dans cet échantillon.

### 9.4 La cohérence pré-événement comme test de confusion

La cohérence pré-sismique sert de contrôle important : elle ne connaît pas la date du séisme. Si elle classe déjà les bâtiments, une partie de l’AUC peut venir de la structure urbaine plutôt que du changement lié à l’événement.

Dans les résultats présentés, la cohérence pré-sismique seule atteint 0,458, tandis que la cohérence co-sismique brute atteint 0,557. L'écart est positif :

ΔAUC = 0,557 − 0,458 = 0,099

Les méthodes transformées atteignent des valeurs plus élevées, jusqu'à 0,601 pour DPM1 moyenne. Mais une partie de leur information peut encore provenir de la structure préexistante, de la géométrie urbaine ou de la distribution des valeurs de cohérence. La barre pré-sismique ne constitue donc pas une vérité négative parfaite, mais elle indique la performance qu'un signal sans connaissance de l'événement peut déjà obtenir.

L’AUC brute ne suffit donc pas. Il faut aussi vérifier que la méthode dépasse cette référence pré-événement et reste informative après contrôle de la structure préexistante.

### 9.5 Pourquoi la cohérence ne suffit pas

Ces résultats expliquent pourquoi la cohérence ne remplace pas l’intensité radar dans cette étude.

La cohérence mesure principalement si l’organisation des diffuseurs a changé. Elle ne mesure directement ni la quantité de matériau détruit, ni l’étendue de l’effondrement, ni la gravité du dommage. Une petite modification et une destruction complète peuvent toutes deux produire une perte importante de cohérence si la structure électromagnétique change suffisamment.

La cohérence est également sensible aux surfaces peu rétrodiffusantes. Lorsque le rapport signal sur bruit est faible, une surface peut paraître décorrélée même si le changement réel est limité. Cette limite est particulièrement importante pour les routes et les surfaces lisses, mais elle concerne aussi les bâtiments dont la signature radar est faible ou instable.

Enfin, le choix des paires d'images, du seuil de fiabilité, de la méthode d'appariement et de la transformation statistique modifie fortement la sortie. Les cartes de la Figure 15 montrent que deux méthodes appliquées aux mêmes données peuvent produire des distributions très différentes : l'une conserve un score continu, l'autre concentre presque tous les pixels sur une valeur maximale, une autre encore réduit la sortie à un binaire.

### 9.6 Conséquence pour la fusion

La cohérence apporte donc une information complémentaire, mais pas assez robuste pour être utilisée seule comme mesure générale du dommage. Cette conclusion est cohérente avec la section 8 : la fusion entre T-stat et cohérence améliore le classement, mais l'amélioration vient de la combinaison de deux signaux imparfaits, non du remplacement de l'intensité par la cohérence.

La meilleure stratégie consiste à conserver les deux grandeurs séparées jusqu'à la phase de fusion :

- l'intensité renseigne sur la variation de rétrodiffusion ;
- la cohérence renseigne sur la conservation ou la rupture de la structure électromagnétique ;
- leur combinaison produit un classement plus robuste que l'un ou l'autre signal isolé dans les expériences menées.

Il faut cependant éviter de présenter la cohérence comme une preuve indépendante du dommage. Les deux grandeurs proviennent de données Sentinel-1 et peuvent partager certaines erreurs liées à la géométrie, à l'humidité, à la végétation ou au rapport signal sur bruit. La fusion améliore le classement, mais elle ne garantit pas l'indépendance des sources.

### 9.7 Ce que l'expérience permet de conclure

Les résultats autorisent quatre conclusions :

1. Les méthodes de cohérence reproduites depuis les formules publiées sont légèrement informatives sur les quinze zones syriennes, mais leur performance reste modeste.

2. DPM1 moyenne donne le meilleur résultat de l'expérience, avec une AUC de 0,601, sans que l'écart avec DPM2 soit suffisant pour établir une supériorité générale.

3. Une sortie binaire perd une grande partie de l'information nécessaire au classement, comme le montrent la Figure 15 et l'AUC de BDPM publiée à 0,462.

4. La cohérence est utile comme information complémentaire de l'intensité, mais elle ne doit pas être présentée seule comme une mesure directe de la gravité ou de la praticabilité.

La méthode retenue dans la suite conserve donc la cohérence comme une composante complémentaire, à fusionner avec l'intensité dans les cas où les deux produits sont disponibles. Le résultat final reste un indicateur de changement et de priorisation, non une certification automatique du dommage.

## 10 Ce que le satellite permet de décider

L’analyse précise un rôle limité mais utile pour le radar. Il ne remplace ni l’image optique très haute résolution ni l’expertise de terrain, et ne produit pas automatiquement une carte certaine des bâtiments détruits. Il peut en revanche fournir un indicateur de changement sur une emprise choisie lorsque l’optique est absente, nuageuse, tardive ou trop longue à interpréter manuellement.

Le premier résultat est une complémentarité de temporalité. L’optique reste la meilleure source pour décrire visuellement un bâtiment lorsque l’image est exploitable. Mais, comme le montre la figure 3, une image très détaillée arrivée plusieurs jours après l’événement peut être moins utile pour la première priorisation qu’un signal radar moins lisible, mais disponible plus tôt et sur une emprise étendue.

Le radar répond à cette contrainte par des acquisitions de jour comme de nuit, indépendantes de la couverture nuageuse. Cet avantage de disponibilité ne constitue pas une capacité d’interprétation automatique : le signal dépend de la géométrie, de la végétation, de l’humidité et de la stabilité propre au pixel. Il doit être comparé à un historique.

### 10.1 Ce que la méthode permet de faire

Le PWTT transforme une série temporelle Sentinel-1 en score continu de changement. Dans l’implémentation décrite ici, le calcul effectivement utilisé est la forme à variance regroupée du test de Student :

$$t = \frac{\bar{x}_{\text{post}} - \bar{x}_{\text{pré}}}{s_p \sqrt{\dfrac{1}{n_{\text{pré}}} + \dfrac{1}{n_{\text{post}}}}}$$

où s_p est l'écart-type regroupé défini par l'équation (5). Le code diffusé par Ballinger emploie cette même forme ; la formule à variances séparées écrite dans l'article, celle de Welch, n'est proposée par le dépôt de référence que depuis juin 2026, et la section 4.3 compare les deux. Cette précision doit rester explicitement documentée, car elle interdit d'interpréter directement les valeurs de T comme des niveaux de confiance.

Lorsque plusieurs images post-événement ne sont pas encore disponibles, un score de type z-test peut être calculé à partir d'une seule image :

$$z = \frac{x_{\text{post}} - \bar{x}_{\text{pré}}}{s_{\text{pré}}}$$

Le score z permet un premier indicateur avec moins d’information statistique. Les essais montrent qu’une image unique peut être utile, mais que le délai d’acquisition reste déterminant ; les résultats sont plus régulièrement exploitables autour de deux jours dans l’échantillon étudié. Ce repère n’est pas un seuil universel.

Le score continu permet ensuite de classer les bâtiments ou les pixels selon leur niveau de changement. Ce choix est préférable à une classification immédiate en classes de dommage. Les résultats montrent en effet que le signal radar est plus fiable pour séparer des bâtiments ayant changé de bâtiments restés stables que pour distinguer précisément plusieurs degrés de gravité.

### 10.2 Ce que les comparaisons établissent

Sur l’emprise commune, la T-stat obtient une AUC moyenne de 0,740 contre Copernicus et ChatMap, devant OSU (0,732) et NASA DRCS S2 (0,716). Elle est donc compétitive dans ce protocole, sans être déclarée meilleure dans tous les contextes.

Ce résultat doit être interprété avec prudence. Il ne signifie pas que le T-stat est meilleur dans tous les contextes, mais que son classement est favorable dans le protocole comparatif retenu. La comparaison sur emprise commune est indispensable, car les AUC obtenues sur les emprises propres à chaque produit ne répondent pas à la même question.

La comparaison montre aussi qu’une fusion peut améliorer le classement. La fusion du T-stat avec OSU atteint une AUC moyenne de 0,7635, contre 0,7403 pour le T-stat seul. Le gain est donc :

ΔAUC = 0,7635 − 0,7403 = 0,0232

Ce gain est positif dans les quatre configurations de fusion testées avec différents partenaires de cohérence. Il reste modeste, mais il est plus convaincant qu'une amélioration isolée, car il se retrouve sur plusieurs emprises.

Dans les essais, la moyenne des rangs est la règle la plus robuste. La disjonction, qui retient le signal le plus alarmant, dégrade au contraire systématiquement le classement. Elle augmente la sensibilité aux fausses alertes et peut produire une liste trop large d'adresses à vérifier. La conjonction est plus stricte et peut convenir à une logique de confirmation, mais elle réduit le nombre de bâtiments retenus.

### 10.3 Deux usages opérationnels

Les résultats ne conduisent pas à un réglage unique, car la meilleure stratégie dépend de l'usage.

Si quelques équipes doivent être envoyées rapidement, l'objectif est de maximiser la précision parmi les premiers bâtiments visités. Il faut alors privilégier les scores les plus élevés et accepter de ne pas couvrir immédiatement l'ensemble des bâtiments touchés.

Si l'objectif est de ne manquer aucun secteur important, il faut au contraire privilégier le rappel. Le volume de bâtiments ou de zone à relire sera plus important, mais la méthode doit permettre de retrouver une proportion élevée des bâtiments positifs.

Ces deux usages peuvent être représentés par des indicateurs différents :

Précision(k) = (positifs retrouvés parmi les k premiers objets) / k

Rappel(q) = (positifs retrouvés dans les q % premiers objets) / (total des positifs)

La précision au sommet et le rappel cumulé ne mesurent donc pas la même chose. Une méthode peut être excellente pour placer quelques bâtiments endommagés en tête du classement sans être la meilleure pour couvrir toute la zone. La sortie de l'outil doit par conséquent permettre ces deux usages plutôt que d'imposer une classe ou un seuil unique.

### 10.4 Le cas particulier des routes

La transposition du raisonnement aux routes doit être formulée avec davantage de prudence. Le croisement entre une carte de changement et un réseau routier est une pratique établie, notamment dans la recommandation UN-SPIDER, qui parle de tronçons pouvant être bloqués et de forte probabilité de gravats.

Mais la mesure réalisée sur les données routières ne valide pas la détection telle quelle. Sur le Venezuela, la vérité Copernicus ne contient que trois positifs routiers parmi 24 696 entités. Aucune AUC ou mesure de rappel n'est donc interprétable pour cet événement.

Sur la Jamaïque, où la vérité routière est plus fournie, le résultat est défavorable : les tronçons classés comme endommagés présentent en moyenne des scores T-stat plus faibles que les tronçons classés comme intacts, avec une AUC d'environ 0,32 pour les positifs stricts. Le classement est donc inversé dans cet échantillon.

Ce résultat interdit de présenter la sortie comme une détection de routes endommagées, de routes coupées ou de voies impraticables. La formulation défendable est celle d'un signalement de changement le long du réseau routier ou de tronçons présentant une forte probabilité de gravats, avec une validation encore insuffisante.

Cette limite peut s'expliquer par la résolution spatiale du radar, le mélange entre chaussée et environnement immédiat, le repliement des bâtiments et l'influence de l'humidité ou de la végétation. Elle rappelle surtout que le radar mesure un changement de surface le long d'une ligne, et non directement la praticabilité d'un itinéraire.

### 10.5 Ce que l'outil ne permet pas d'affirmer

Ces résultats ne permettent pas d’affirmer que :

- chaque bâtiment signalé est endommagé ;
- le score continu constitue une probabilité de dommage ;
- une valeur de T correspond directement à un niveau de confiance statistique dans l'implémentation actuelle ;
- la méthode fournit une estimation fiable de la gravité du dommage ;
- le radar permet de mesurer directement l'accessibilité ou le temps de trajet ;
- un tronçon routier signalé est nécessairement impraticable ;
- l'inversion du score routier suffirait à rendre la fonction valide ;
- la méthode est transposable sans réserve d'un séisme à un cyclone.

Le résultat doit donc être présenté comme un indicateur automatisé, reproductible et continu de changement radar, destiné à prioriser une analyse complémentaire.

### 10.6 Positionnement retenu

La méthode est défendable à trois conditions.

La première consiste à conserver un vocabulaire proportionné au signal : changement, classement, priorité, probabilité de gravats ou observation à vérifier, plutôt que dommage certain ou praticabilité.

La deuxième consiste à conserver la sortie sous forme continue. Les seuils peuvent être exprimés en centiles selon le volume d'objets qu'une équipe est capable de vérifier, mais un centile ne doit pas être présenté comme une probabilité d'erreur.

La troisième consiste à intégrer l'outil dans une chaîne de décision et non à l'utiliser seul :

1. le radar fournit un premier classement ;

2. l'optique confirme ou précise le changement lorsque l'image est disponible ;

3. la cohérence apporte une information complémentaire ;

4. l'aérien ou le terrain vérifie les secteurs prioritaires ;

5. les nouvelles acquisitions mettent à jour le classement.

Dans cette chaîne, l’outil ne remplace pas l’expert : il aide à déterminer où mobiliser en premier l’expertise humaine ou l’observation détaillée.

La partie suivante quitte donc l'analyse des performances satellitaires pour examiner la mise en œuvre concrète de la chaîne : données utilisées, paramètres, architecture du greffon QGIS, reproductibilité, sorties produites et conditions d'emploi opérationnel.

## Limites

Les sections précédentes ont évalué le pouvoir de classement du radar à l’aide de deux références différentes : Copernicus EMS, issu d’une photo-interprétation experte, et ChatMap, qui rassemble des signalements de terrain associés à des photos ou vidéos. Aucun produit UNOSAT dédié n’a été identifié pour le Venezuela ; UNOSAT n’a servi de référence que pour la Jamaïque.

Ces références ne constituent pas une vérité terrain complète ; cette limite conditionne toute la calibration. Copernicus EMS repose sur la photo-interprétation d’imagerie optique acquise en vue quasi nadirale. Cotrufo et al. (2018) documentent la base même sur laquelle cette classification opérationnelle a été construite : une échelle dérivée et simplifiée de l’Échelle Macrosismique Européenne de 1998, précisément pour tenir compte des limites inhérentes à la télédétection. Le service prévoit d’ailleurs une classe « dommage non visible », et rappelle lui-même que ses produits constituent une estimation indirecte et non une donnée de vérité terrain.

Ces mêmes auteurs mesurent empiriquement cette limite sur le séisme italien de 2016, à Amatrice, en prenant cette fois un levé par drone comme référence. Le résultat se lit dans la précision de l’utilisateur, c’est-à-dire la proportion de bâtiments réellement dans la classe parmi ceux que la carte y a placés : elle n’atteint que 42 % pour la classe « dommage non visible » et 28 % pour « dommage possible », alors qu’elle culmine à 94 % pour « dommage » et 100 % pour « détruit ». Autrement dit, quand la vue verticale annonce une destruction elle a raison, et quand elle annonce l’absence de dommage visible elle se trompe trois fois sur cinq.

Cette limite géométrique se confirme à une tout autre échelle. Ainscoe et al. (2025) comparent, après les séismes de Kahramanmaraş en 2023, les cartes de dommages issues de l’optique et du radar aux inspections conduites au sol par environ huit mille agents, bâtiment par bâtiment, sur près de deux millions de bâtiments. Le rappel du produit radar atteint 0,59 — il retrouve donc 59 % des bâtiments réellement endommagés — quand les méthodes optiques n’en identifient que 8 à 17 %. La performance globale va dans le même sens, avec un score F1 d’environ 0,47 pour le radar contre 0,15 à 0,24 pour les produits optiques. Et l’écart de disponibilité est plus net encore : le radar a couvert l’intégralité de la zone affectée en dix jours, quand l’imagerie optique à très haute résolution n’en couvrait dans le même délai que 5,4 %, soit onze mille kilomètres carrés.

La raison est principalement géométrique. Une image prise à la verticale ne montre que ce qui est exposé au zénith : la toiture, et ce qui déborde de son emprise. Or un bâtiment ne s’effondre pas nécessairement par le haut. Il peut perdre une façade, voir ses planchers s’écraser les uns sur les autres, ou basculer sur un niveau souple, sans que sa toiture cesse d’occuper la même surface au sol. Le signal que cherche une méthode de détection de changement — une modification de l’emprise, de la texture ou de la rétrodiffusion du toit — est alors faible ou absent, alors même que le bâtiment est perdu.

Cinq cas du séisme du 24 juin 2026 documentés au sol l’illustrent, et reproduisent à l’échelle du bâtiment ce que la littérature mesure à l’échelle d’une région. Trois se trouvent à Catia La Mar, deux à Caraballeda. Les modes de ruine diffèrent — planchers effondrés les uns sur les autres, basculement sur un rez-de-chaussée écrasé, façade emportée — mais ils ont en commun de laisser la toiture en place. Sur les images aériennes acquises trois jours après l’événement, à trente-trois et trente-cinq centimètres, aucun des cinq ne se distingue nettement de son état antérieur : on devine parfois quelques débris de voirie, jamais la perte du bâtiment. À cinquante centimètres et à quatre-vingt-six centimètres, deux résolutions réellement disponibles sur la zone, il n’y a plus rien à lire ; et sur Sentinel-2 à dix mètres, le bâtiment n’existe tout simplement pas comme objet distinct. La perte n’est donc pas progressive : elle est déjà consommée à la meilleure résolution disponible.

![Figure 9](figures/figure_9_vue_verticale.png)

**Figure 9 — Ce qu’une vue verticale ne montre pas d’un effondrement latéral.** Cinq bâtiments détruits lors du séisme du 24 juin 2026, trois à Catia La Mar et deux à Caraballeda, chacun documenté au sol par une photographie. Chaque ligne présente, de gauche à droite : une acquisition aérienne avant l’événement, deux acquisitions aériennes réelles après l’événement à des résolutions différentes, l’image Sentinel-2 à 10 mètres, et la photographie prise au sol. **Toutes les vignettes sont des acquisitions réelles** : aucune n’est obtenue par dégradation d’une autre. La résolution n’est donc pas la seule variable — les dates et les angles de visée diffèrent d’une vignette à l’autre, et ils sont indiqués sous chacune — mais l’échelle ainsi formée ne montre que ce qui était effectivement disponible sur cette catastrophe. Sous chaque ligne figure le nombre de produits de cartographie des dommages ayant signalé ce bâtiment, ne l’ayant pas signalé, ou ne l’ayant pas analysé faute d’empreinte, sur les douze produits comparés. ChatMap est écarté de ce décompte : l’observation est faite au sol et non depuis l’espace, et c’est elle qui a servi à sélectionner les cinq bâtiments. Imagerie aérienne : 2026 © Vantor Open Data et 2026 © Planet Open Data, licence CC BY-NC 4.0. Sentinel-2 : *contains modified Copernicus Sentinel data (2026)*. Photographies au sol : ChatMap, Humanitarian OpenStreetMap Team.**

Le décompte des produits va dans le même sens. Sur les soixante verdicts que forment ces cinq bâtiments et les douze produits comparés, **58 % signalent le bâtiment, 35 % ne le signalent pas, et 7 % ne le couvrent pas** faute d’empreinte — soit, en ne considérant que les bâtiments effectivement analysés, **près de quatre verdicts sur dix qui manquent une destruction établie au sol**. L’écart entre cas est considérable : le bâtiment le mieux vu l’est par neuf produits sur douze, le moins bien vu — celui dont la façade est partie — par quatre seulement. Trois produits les signalent tous les cinq, Copernicus EMS, OSU et NASA DRCS S2 ; à l’inverse, NASA DRCS S1 n’en signale aucun et HOT fAIr un seul. Notre T-stat en signale quatre sur cinq.

Ce constat ne rend pas caduc le classement précédent, mais en précise l’interprétation. Un désaccord entre la méthode radar et une vérité terrain optique peut révéler une limite de la méthode aussi bien qu’une limite de la référence elle-même, et rien dans l’écart ne dit laquelle. Optique et radar ne se contredisent peut-être pas tant qu’ils ne regardent simplement pas la même chose : l’un vise le toit en nadir, l’autre atteint les façades de côté. Cotrufo et al. tranchent eux-mêmes cette hiérarchie en prenant le drone, et non l’imagerie verticale, comme référence de leur validation.

La portée de la partie 2 doit donc être formulée précisément. La méthode signale des secteurs où quelque chose a changé, et elle le fait vite, de nuit, sous les nuages et sans accès au terrain. Mais un secteur signalé n’est pas un bâtiment diagnostiqué, et un secteur non signalé n’est pas un secteur indemne. C’est l’asymétrie qui compte opérationnellement : les faux négatifs de la vue verticale ne sont pas répartis au hasard, ils se concentrent sur un mode d’effondrement particulier, celui qui laisse la toiture en place — et c’est exactement la gradation intermédiaire que nos deux cas d’étude désignaient déjà comme le point faible commun à toutes les méthodes comparées.

Cette hiérarchie justifie la démarche en entonnoir de la partie suivante : le satellite priorise, l’évaluation aérienne confirme à une résolution plus fine et sous un angle parfois oblique, et le drone referme la boucle sur les cas les plus ambigus, jusqu’à la façade elle-même. La conséquence pratique est d’ailleurs mesurable sur notre cas : entre l’image satellitaire à trente-cinq centimètres et l’observation de terrain, il n’existait sur cette catastrophe aucune acquisition intermédiaire, le catalogue ne contenant ni vol drone ni vol avion sur les zones touchées. C’est précisément ce vide que la partie suivante cherche à combler, non par une meilleure résolution verticale, mais par une vue rapprochée et parfois oblique que seul un aéronef léger peut fournir.

## ANNEXE — Dictionnaire des méthodes de cartographie des dommages

Séisme du Venezuela, juin 2026. Chaque entrée décrit la méthode employée par sa source et renvoie à ses données ou à sa documentation. Les chiffres donnés sont des paramètres de méthode, non un classement des produits.

**CEMS (Copernicus EMS)** — Photo-interprétation manuelle d’images optiques à très haute résolution avant/après. Des analystes attribuent aux bâtiments visibles les classes Destroyed, Damaged ou Possibly damaged. Sortie : bâtiments annotés.
Accès aux données / méthode : <https://mapping.emergency.copernicus.eu/activations/EMSR884/aois>

**ChatMap** — Signalements géolocalisés de terrain, accompagnés selon les cas de photos et d’observations de dommages. Sortie : points de signalement à rapprocher des bâtiments.
Accès aux données / méthode : <https://chatmap.hotosm.org/#map/e5e685ff-83eb-495b-be16-271513992cfd>

**HOTOSM / MapSwipe** — Vérification participative d’alertes sur images optiques : plusieurs volontaires examinent des zones présélectionnées et indiquent si le dommage est visible ou incertain. Sortie : secteurs ou cellules H3 validés.
Accès aux données / méthode : <https://huggingface.co/datasets/hotosm/venezuela_eq_2026>

**OSU/CUNY — Sentinel-1 CCD** — Détection d’une baisse inhabituelle de cohérence radar : chaque acquisition post-séisme est comparée à environ un an de cohérence antérieure, puis le score z est reporté sur les empreintes Overture. Un palier est attribué si le signal couvre au moins 50 % de l’empreinte : possible (z ≥ 1,5), probable (z ≥ 2) ou high confidence (z ≥ 3). Sortie : empreintes et paliers de confiance.
Accès aux données / méthode : <https://oregonstate.app.box.com/s/yrgtsbwmpqpajuhzioq0k13ihfluuneg/folder/394695539753>

**EOS-RS — Sentinel-1 DPM** — Carte de changement radar entre une série antérieure du 24 février au 13 juin et une image du 25 juin 2026. Pixels d’environ 30 m, colorés selon l’ampleur du changement de surface ; aucune classe structurelle n’est attribuée à chaque bâtiment.
Accès aux données / méthode : <https://sf.earthobservatory.sg/event/EOSRS_2026_005_VEN_EQ_202606_Caracas>

**IMPACT Initiatives — Sentinel-1 DPM** — Score z de changement d’amplitude Sentinel-1 GRD par rapport à une référence annuelle, avec deux acquisitions postérieures appariées du 25 juin. Après masquage des surfaces bâties, une empreinte Overture est retenue si au moins 50 % de sa surface recoupe le proxy radar.
Accès aux données / méthode : <https://data.humdata.org/dataset/venezuela-earthquakes-damage-assessment-using-sentinel-1-radar-data>

**NASA DRCS/Ames — Sentinel-1** — Soustraction de la rétrodiffusion VV du 18 juin à celle du 25 juin 2026 sur les zones bâties ESA WorldCover. Les baisses ≤ −8 dB, de −8 à −6 dB et de −6 à −4 dB forment des niveaux d’alerte cartographique. Sortie : pixels de changement.
Accès aux données / méthode : <https://gis.earthdata.nasa.gov/portal/home/item.html?id=b205e94bcc2c4096acf7201da3116272>

**NASA DRCS/Ames — Sentinel-2** — Détection d’une augmentation conjointe de la brillance visible et du SWIR1 entre composites pré- et post-séisme. Résolution visible 10 m, SWIR1 20 m ; moyenne, maximum et centiles du score résumés par empreinte Google Open Buildings.
Accès aux données / méthode : <https://gis.earthdata.nasa.gov/portal/home/item.html?id=27a7b4306a5e4ab68be2adb8c6ec83bd>

**Microsoft AI for Good Lab** — Modèle optique classant les pixels en bâtiment, dommage, nuage ou autre. Le pourcentage de pixels classés « dommage » est calculé dans chaque empreinte Overture et dans des tampons de 10 et 20 m. Sortie : attributs par bâtiment.
Accès aux données / méthode : <https://visualizers.aiforgood.ai/damage-assessment/venezuela_earthquake_2026_report.html>

**HOTOSM fAIr** — Deux modèles optiques : segmentation des bâtiments, puis estimation du dommage sur images avant/après. Le modèle DINOv3 de dommage attribue les classes no damage, minor, major ou destroyed, avec un score de confiance. Sortie : empreintes et classes prédites.
Accès aux données / méthode : <https://huggingface.co/hotosm/earthquake-damage-assessment-model>

**UH SAIL / QuakeDamage** — Réseau de comparaison optique siamois DINOv3 entraîné sur des images de séismes antérieurs. Il compare les vues avant/après et classe le dommage par bâtiment sur des empreintes affinées à partir d’Overture.
Accès aux données / méthode : <https://quakedamage.github.io/>

**DISHA** — Empreintes issues de Google Open Buildings et modèle d’évaluation des dommages sur images optiques à très haute résolution. Sortie : bâtiments avec prédiction automatique de dommage.
Accès aux données / méthode : <https://data.humdata.org/dataset/venezuela-building-damage-analysis-disha> ·
<https://disha.unglobalpulse.org/our-products/> ·
<https://disha.unglobalpulse.org/dishas-revamped-ai-assisted-damage-assessment-solution-enters-a-new-phase-of-growth-and-operational-impact/>

**UNEP — estimation des débris** — Combinaison d’un PWTT Sentinel-1 adapté en score z, des annotations CEMS, de l’interprétation PlanetScope et de produits optiques ou radar locaux. Les bâtiments et hauteurs modélisées du Global Building Atlas servent ensuite à estimer les débris.
Accès aux données / méthode : <https://data.humdata.org/dataset/building-debris-assessment-venezuela-earthquake-june-2026>

**T-stat** — Méthode d’anomalie temporelle appliquée à la rétrodiffusion Sentinel-1 GRD : comparaison de chaque pixel à son historique, combinaison des observations disponibles et agrégation des scores aux empreintes de bâtiments. Sortie : score continu de changement.

**BDPM (reproduction)** — Méthode de changement de cohérence reproduite à partir de la publication de Liu et al. : comparaison de cohérences avant/après, avec appariement d’histogrammes et masque de fiabilité. Sortie : score ou masque de changement selon le réglage.

**UNGSC** — Couche de changement au pixel recensée mais procédure, données d’entrée et seuils non documentés dans les sources disponibles ; aucune méthode précise ne peut être attribuée.

**WFP–LIST–CERN** — Méthode annoncée d’apprentissage profond sur images SAR avant/après, de type ResNet, pour produire une classe de dommage par bâtiment. Données non trouvées.

## Bibliographie

Les références utilisées dans cette version longue sont regroupées ci-dessous. Les travaux de la partie aérienne, qui ne sont pas nécessaires à l’argumentation satellite, restent dans la bibliographie générale de la thèse.

- Ainscoe, E. A., Swaminathan, R., Way, L., Modugno, S., Chin, S. T., Panta, N., Crevoisier, T., & Yun, S.-H. (2025). Earthquake damage mapped more comprehensively and accurately by radar satellites than optical imagery. Communications Earth & Environment, 6, 631. https://doi.org/10.1038/s43247-025-02107-1

- Ballinger, O. (2024). PWTT: Pixel-Wise T-Test for battle damage detection [Computer software]. https://github.com/oballinger/PWTT

- Ballinger, O. (2025). Open access battle damage detection via Pixel-Wise T-Test on Sentinel-1 imagery. Remote Sensing of Environment, 331, 115025. https://doi.org/10.1016/j.rse.2025.115025

- Cotrufo, S., Sandu, C., Giulio Tonolo, F., & Boccardo, P. (2018). Building damage assessment scale tailored to remote sensing vertical imagery. European Journal of Remote Sensing, 51(1), 991–1005. https://doi.org/10.1080/22797254.2018.1527662

- Dietrich, O., Peters, T., Sainte Fare Garnot, V., Sticher, V., Ton-That Whelan, T., Schindler, K., & Wegner, J. D. (2025). An open-source tool for mapping war destruction at scale in Ukraine using Sentinel-1 time series. Communications Earth & Environment. https://doi.org/10.1038/s43247-025-02183-7

- Ehrlich, D., Guo, H., Molch, K., Ma, J., & Pesaresi, M. (2009). Identifying damage caused by the 2008 Wenchuan earthquake from VHR remote sensing data. International Journal of Digital Earth, 2(4), 309–326. https://doi.org/10.1080/17538940902767401

- Ge, P., Gokon, H., & Meguro, K. (2020). A review on synthetic aperture radar-based building damage assessment in disasters. Remote Sensing of Environment, 240, 111693. https://doi.org/10.1016/j.rse.2020.111693

- Jung, J., Yun, S.-H., Kim, D., & Lavalle, M. (2018). Damage-Mapping Algorithm Based on Coherence Model Using Multitemporal Polarimetric-Interferometric SAR Data. IEEE Transactions on Geoscience and Remote Sensing, 56(3), 1520–1532. https://doi.org/10.1109/TGRS.2017.2764748

- Plank, S. (2014). Rapid Damage Assessment by Means of Multi-Temporal SAR - A Comprehensive Review and Outlook to Sentinel-1. Remote Sensing, 6(6), 4870–4906. https://doi.org/10.3390/rs6064870

- Saito, K., Spence, R. J. S., Going, C., & Markus, M. (2004). Using High-Resolution Satellite Images for Post-Earthquake Building Damage Assessment: A Study following the 26 January 2001 Gujarat Earthquake. Earthquake Spectra, 20(1), 145–169. https://doi.org/10.1193/1.1650865

- Salaheldin, A. (2026). PWTT QGIS Plugin: Pixel-Wise T-Test for building damage detection [Computer software]. QGIS Plugins. https://plugins.qgis.org/plugins/pwtt_qgis/

- Scher, C., & Van Den Hoek, J. (2025). Active InSAR monitoring of building damage in Gaza during the Israel-Hamas War. arXiv:2506.14730. https://arxiv.org/abs/2506.14730

- Scher, C., & Van Den Hoek, J. (2025). Nationwide conflict damage mapping with interferometric synthetic aperture radar: A study of the 2022 Russia-Ukraine conflict. Science of Remote Sensing, 11, 100217. https://doi.org/10.1016/j.srs.2025.100217

- Scher, C., & Van Den Hoek, J. (2026). Building Damage Assessment Portal—Open Access Satellite Conflict Damage Data. https://damage.conflict-ecology.org/

- Student. (1908). The Probable Error of a Mean. Biometrika, 6(1), 1–25. https://doi.org/10.2307/2331554

- Wang, X., Feng, G., He, L., An, Q., Xiong, Z., Lu, H., Wang, W., Li, N., Zhao, Y., Wang, Y., & Wang, Y. (2023). Evaluating Urban Building Damage of 2023 Kahramanmaras, Turkey Earthquake Sequence Using SAR Change Detection. Sensors, 23(14), 6342. https://doi.org/10.3390/s23146342

- Welch, B. L. (1947). The generalization of Student’s problem when several different population variances are involved. Biometrika, 34(1–2), 28–35. https://doi.org/10.1093/biomet/34.1-2.28

- Westrope, C., Banick, R., & Levine, M. (2014). Groundtruthing OpenStreetMap Building Damage Assessment. Procedia Engineering, 78, 29–39. https://doi.org/10.1016/j.proeng.2014.07.035

- Westrope, C., Banick, R., & Levine, M. (2014). Groundtruthing OpenStreetMap Damage Assessment Review—Interim Report. REACH Initiative / ACTED et American Red Cross. https://americanredcross.github.io/OSM-Assessment/

## Notes

[^8]: International Charter Space and Major Disasters, « About the Charter » et documentation relative aux mécanismes d'activation, consultées en septembre 2026, <https://disasterscharter.org>. La Charte coordonne la mise à disposition de données et de produits au bénéfice d'utilisateurs autorisés ; elle ne doit pas être assimilée à une banque d'images librement téléchargeables sans condition.

[^9]: Table de calcul : [`tables/charte_synthese_optique_radar.csv`](../../tables/charte_synthese_optique_radar.csv).

[^10]: Calcul de l'auteur à partir de l'heure d'activation de Copernicus EMSR847 et de l'heure de passage du cyclone Melissa retenue dans la chronologie de l'événement. Table de calcul : [`tables/cems_delais_par_activation.csv`](../../tables/cems_delais_par_activation.csv).

[^11]: Projet Signal, lancé en 2021 par Humanité & Inclusion et Atlas Logistique dans neuf pays, à partir de l'indice de vulnérabilité logistique dont la méthodologie avait été élaborée après le cyclone Idai. <https://www.hi.org/fr/actualites/signal---un-projet-innovant-pour-renforcer-la-resilience-logistique-des-communautes-vulnerables-en-contexte-fragile>

[^12]: Ballinger, O. (2025). Open access battle damage detection via Pixel-Wise T-Test on Sentinel-1 imagery. *Remote Sensing of Environment*, 331, 115025. La version preprint (arXiv:2405.06323, 2024) rapporte 0,88 et 0,81 ; la version publiée donne des valeurs légèrement inférieures. L'écart illustre la sensibilité des performances au périmètre géographique et au jeu de validation retenus.

