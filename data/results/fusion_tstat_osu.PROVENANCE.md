# `fusion_tstat_osu.csv` — comment cette table a été produite

Cette table porte les chiffres cités sur le **coût d'un plancher de rappel**
dans la fusion « ET » entre le T-stat d'intensité et le produit de cohérence
interférométrique OSU. Les trois points qui commandent leur lecture — le
dénominateur, la définition du positif, le sort des bâtiments sans score OSU —
sont établis ci-dessous, vérifiés sur les couches d'origine et non déduits de
la table.

## L'échantillon

| étape | bâtiments |
|---|---|
| empreinte Overture dans l'emprise CEMS (EMSR884) | 288 374 |
| dont présents dans la table de référence CEMS | 288 374 |
| dont porteurs d'un score OSU | **287 905** |
| écartés faute de score OSU | 469 — soit 0,16 % |

Le dénominateur de toutes les matrices de confusion de cette table est donc
**287 905 bâtiments**, l'intersection des trois couches dans l'emprise de
l'activation. Les 469 bâtiments absents de la couche OSU sont **retirés de
l'évaluation** : ils ne comptent ni comme positifs ni comme négatifs. Cette
perte est négligeable — un bâtiment sur six cents — et la restriction ne peut
donc pas expliquer les écarts de rappel observés entre niveaux de confiance.

Le T-stat, lui, couvre la totalité de l'échantillon : les 287 905 bâtiments
retenus portent tous une valeur, ce que confirme l'égalité exacte entre
`tp + fp + fn + tn` et l'effectif de l'intersection sur les soixante lignes de
la table.

## La définition du positif

La vérité de référence est le champ de gradation de dommage de la cartographie
rapide Copernicus EMS. Sa répartition sur les 287 905 bâtiments retenus :

| classe CEMS | bâtiments |
|---|---|
| `not_reported` | 284 984 |
| `Possibly damaged` | 1 517 |
| `Damaged` | 772 |
| `Destroyed` | 632 |

Trois définitions du positif sont évaluées en parallèle, et la colonne
`gt_variant` indique laquelle s'applique à chaque ligne :

| `gt_variant` | positifs | prévalence |
|---|---|---|
| `Destroyed_seul` | 632 | 0,220 % |
| `Damaged_et_Destroyed` | 1 404 | 0,488 % |
| `Tout_y_compris_Possibly` | 2 921 | 1,015 % |

Les classes non retenues comme positives forment les négatifs ; aucun bâtiment
n'est écarté à ce titre, ce qui explique que le dénominateur ne varie pas d'une
définition à l'autre. **Une convention doit être explicitée : `not_reported` est
traité comme non sinistré.** C'est l'hypothèse la plus défavorable à la méthode
évaluée, la cartographie rapide n'étant pas exhaustive — un bâtiment endommagé
mais non relevé compte en faux positif. Les précisions rapportées ici sont donc
des bornes inférieures.

## Le traitement du terme OSU

La colonne `niveau_confiance_osu` désigne les valeurs du champ de confiance OSU
admises dans le terme de la fusion, par inclusion progressive :

| `niveau_confiance_osu` | valeurs admises | bâtiments admis |
|---|---|---|
| `high_seul` | `high_confidence` | 16 666 — 5,79 % |
| `high_et_probable` | + `probable` | 37 398 — 12,99 % |
| `high_probable_et_possible` | + `possible` | 55 412 — 19,25 % |
| `toutes_confidences` | + `below_floor` | 287 905 — 100 % |

`toutes_confidences` n'impose donc **aucun filtre** : les quatre valeurs
couvrent l'intégralité de l'échantillon retenu — la cinquième valeur du champ,
`NA`, n'apparaît sur aucun des 287 905 bâtiments. Les lignes portant ce niveau
décrivent par conséquent le **T-stat seul**, et servent de référence à laquelle
les trois niveaux filtrés se comparent.

## Le plafond de rappel n'est pas un effet de couverture

La fusion étant une conjonction, le rappel qu'elle peut atteindre est borné par
la part des bâtiments vraiment sinistrés que le terme OSU laisse passer, quel
que soit le seuil appliqué au T-stat. Ce plafond, mesuré directement :

| `niveau_confiance_osu` | `Destroyed_seul` | `Damaged_et_Destroyed` | `Tout_y_compris_Possibly` |
|---|---|---|---|
| `high_seul` | 350/632 — 55,4 % | 712/1 404 — 50,7 % | 1 354/2 921 — 46,4 % |
| `high_et_probable` | 516/632 — 81,6 % | 1 094/1 404 — 77,9 % | 2 151/2 921 — 73,6 % |
| `high_probable_et_possible` | 579/632 — 91,6 % | 1 237/1 404 — 88,1 % | 2 425/2 921 — 83,0 % |
| `toutes_confidences` | 632/632 — 100 % | 1 404/1 404 — 100 % | 2 921/2 921 — 100 % |

Ces plafonds rendent compte exactement des paliers déclarés inatteignables dans
la table : `high_seul` n'atteint aucun palier, même 70 % ; `high_et_probable`
s'arrête à 80 % sur `Destroyed_seul` ; `high_probable_et_possible` atteint 90 %
mais pas 95 %. Le plafond est donc une **propriété de la conjonction** — il
mesure le rappel propre du produit de cohérence au niveau de confiance retenu —
et non un artefact du recouvrement entre couches, lequel ne retire que 0,16 %
de l'échantillon.

## Ce que contiennent les lignes

Soixante lignes, quatre niveaux de confiance × trois définitions du positif ×
cinq types de sortie au plus :

- `type_resultat = balayage`, avec `critere` valant `meilleur_kappa` ou
  `meilleur_f1` : le seuil de T-stat qui maximise l'un ou l'autre indice sur un
  balayage de −1,0 à 6,0 par pas de 0,1 ;
- `type_resultat = palier_rappel`, avec `rappel_cible` parmi 0,95 / 0,90 / 0,85
  / 0,80 / 0,75 / 0,70 : parmi les seuils qui atteignent le rappel visé, celui
  qui produit le moins de faux positifs. Une combinaison dont le plafond
  ci-dessus est inférieur à la cible n'a simplement pas de ligne.

Le kappa figure dans la table mais n'est pas employé dans les conclusions : il
dépend de la prévalence, ce qui interdit de comparer deux zones de sinistralité
différente.

## Les chiffres cités

Sur `Destroyed_seul`, avec un plancher de rappel à 90 % :

| terme | seuil T-stat | liste produite | part de l'empreinte | rappel atteint | précision |
|---|---|---|---|---|---|
| T-stat seul (`toutes_confidences`) | 1,9 | 107 233 | 37,25 % | 0,902 | 0,532 % — 1 sur 188 |
| fusion (`high_probable_et_possible`) | 1,5 | 46 828 | 16,27 % | 0,903 | 1,219 % — 1 sur 82 |

À rappel égal, la conjonction avec le terme de cohérence divise par 2,3 la
longueur de la liste à inspecter et multiplie par 2,3 la densité de bâtiments
détruits qu'on y trouve. Elle interdit en revanche de viser 95 %.
