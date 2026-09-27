# Disponibilité des données

| Source | Redistribuée ici | Comment l'obtenir |
|---|---|---|
| Scènes Sentinel-1 GRD et SLC | non | Copernicus Data Space Ecosystem et ASF Data Search, à partir des identifiants de granule de l'inventaire et de `data/results/exp63_paires_coherence.csv` |
| Empreintes de bâtiments | non | Overture, Google Open Buildings, Microsoft, OpenStreetMap — la base employée est indiquée produit par produit dans le dictionnaire des méthodes, en annexe du document |
| Gradation de dommage Copernicus EMS | non | page de l'activation EMSR884 ; conditions Copernicus EMS |
| Signalements de terrain (ChatMap) | non | conditions du propriétaire du jeu |
| Produits de dommage tiers | non | chacun à sa source : les adresses sont dans le dictionnaire des méthodes, en annexe du document |
| **Tables de résultats** | **oui** | [`data/results/`](../../data/results/) — 64 tables |
| **Tableaux du document** | **oui** | [`tables/`](../../tables/) — 14 tableaux |
| **Illustrations du document** | **oui** | [`docs/partie_2/figures/`](../partie_2/figures/) — 17 figures |
| **Produits tiers employés en entrée** | **oui** | [`data/raw/produits_tiers/`](../../data/raw/produits_tiers/) — 5 fichiers, avec leurs attributions |
| **Code des calculs** | **oui** | [`src/`](../../src/) — 46 scripts |

## Des identifiants, pas des données

Les acquisitions Sentinel-1 sont ouvertes et se récupèrent à leur source ; les
redistribuer ici n'apporterait rien et alourdirait le dépôt de plusieurs dizaines
de gigaoctets. Ce qui est publié à la place, c'est de quoi retrouver exactement
les mêmes entrées : l'identifiant de granule, l'orbite relative, la polarisation
et la date de chaque scène employée.

[`data/inventaire_donnees.csv`](../../data/inventaire_donnees.csv) recense les
2 074 fichiers de données réellement employés — 134 Go — avec leur chemin
d'origine, leur rôle, leur taille et leur date. Il est produit par balayage du
disque de travail, pas écrit à la main.

## Ce qui ne peut pas être redistribué

Plusieurs produits de référence portent des conditions de réutilisation qui
l'interdiraient, et deux d'entre eux imposent une phrase d'attribution précise.
Un produit, UNGSC, n'a publié aucune notice consultable : ses conditions restent à
établir auprès de son producteur, et le dictionnaire des méthodes le signale.

L'implémentation du test t par pixel n'est pas redistribuée non plus, pour la même
raison : elle dérive d'un code publié sans licence. La section 2.4 du document en
donne la formulation complète et chacun des écarts avec la méthode publiée.
