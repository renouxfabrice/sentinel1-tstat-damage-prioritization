# Produits et relevés tiers

Les produits de tiers employés comme données d'entrée **ne sont pas redistribués
ici**. Ce dossier ne porte que le relevé de catalogue produit pour ce travail ;
les quatre autres fichiers qui s'y trouvaient renvoient désormais à leur source,
que voici.

## Ce qui reste dans ce dossier

| fichier | ce qu'il est | producteur |
|---|---|---|
| `s1_grd_20260811T0059.csv` | relevé d'acquisitions Sentinel-1 GRD, export de catalogue | Copernicus, export de l'auteur |

## Ce qu'il faut aller chercher à la source

| ce qui était ici | ce que c'est | où l'obtenir |
|---|---|---|
| `colapsos_terremoto_venezuela.csv` | registre d'immeubles effondrés, une ligne par bâtiment, chacune attribuée à son auteur et à sa source | journalisme d'investigation vénézuélien, via **[crisisvenezuela.org](https://crisisvenezuela.org)** |
| `nwcaracas_zeroshot_results.csv` | scores de dommage par bâtiment, inférence sans exemple, sur le nord-ouest de Caracas | **DISHA** — UNOPS et UN Global Pulse, **[disha.unglobalpulse.org](https://disha.unglobalpulse.org)** |
| `nwcaracas_footprint_centroids.csv` | centroïdes d'empreintes accompagnant ce produit | DISHA, même source |
| `nwcaracas_final_inference_metrics.csv` | métriques publiées par ce même produit | DISHA, même source |

## Pourquoi ils n'y sont plus

Leurs conditions de réutilisation sont celles de leurs producteurs, et non celles
de ce dépôt. Les republier reviendrait à en assumer la rediffusion sans y être
autorisé. Les **résultats calculés** à partir de ces produits — taux de
recouvrement, décomptes d'accord, aires sous la courbe — restent publiés dans
`data/results/`, parce qu'ils sont le travail de cette étude et non les produits
eux-mêmes.

Deux réserves de leurs auteurs méritent d'être rappelées. Le registre
d'effondrements porte ses propres colonnes `autor` et `fuente_url` : chaque ligne
y est attribuée, et cette attribution doit être conservée par quiconque le
réutilise. Les produits DISHA sont fournis « en l'état », sans garantie, et leurs
auteurs demandent une validation indépendante avant tout usage opérationnel.

Chacun est décrit en détail, dans les termes de son producteur, dans
[l'annexe « Dictionnaire des méthodes », en fin de document](../../../docs/partie_2/partie_2.md#annexe--dictionnaire-des-méthodes-de-cartographie-des-dommages).
