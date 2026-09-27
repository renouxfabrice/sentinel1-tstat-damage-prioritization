# Les méthodes

Le T-stat d'intensité et les reproductions des méthodes de cohérence interférométrique publiées, chacune calculée à partir de sa formule d'origine plutôt que reprise d'un produit livré.

| script | ce qu'il calcule |
|---|---|
| [`dpm1_deux_resolutions.py`](dpm1_deux_resolutions.py) | Reproduction de la première méthode de cohérence publiée, calculée en parallèle sur deux résolutions — traitement par rafales à 20 m et scène entière à 40 m rééchantillonnée à 30 m — pour mesurer l'effet de la résolution sur le classement. |
| [`dpm1_methode1_burst20m.py`](dpm1_methode1_burst20m.py) | Reproduction de la première méthode de cohérence publiée sur les produits par rafales à 20 m : construction du raster, recherche du paramétrage contre la vérité de référence, puis projection des meilleurs paramètres sur tous les bâtiments. |
| [`dpm1_methode2_fullscene30m.py`](dpm1_methode2_fullscene30m.py) | Reproduction de la première méthode de cohérence publiée sur les produits scène entière à 40 m rééchantillonnés à 30 m, la paire antérieure la plus proche de l'événement étant retenue. |
| [`dpm2_a_enveloppe.py`](dpm2_a_enveloppe.py) | Reproduction de la seconde méthode de cohérence publiée dans sa variante en enveloppe simple, sans correction de tendance : empilement de toutes les paires antérieures, puis recherche du paramétrage et projection sur tous les bâtiments. |
