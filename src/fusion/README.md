# Les fusions

Les combinaisons à deux termes entre le T-stat et un produit de cohérence : conjonction, pondération continue, et mesure du gain en aire sous la courbe.

| script | ce qu'il calcule |
|---|---|
| [`exp43_fusion_ciblee_coherence.py`](exp43_fusion_ciblee_coherence.py) | Fusion à deux termes du T-stat d'intensité avec un produit de cohérence interférométrique, mesurée en aire sous la courbe par commune contre deux vérités de référence, sur l'emprise commune aux termes fusionnés. |
| [`fusion_tstat_coevent_filtre_osu.py`](fusion_tstat_coevent_filtre_osu.py) | Fusion par conjonction du T-stat avec la cohérence co-événement, et effet d'un filtre de confiance emprunté au produit OSU — la valeur qu'il publie, non une reproduction de sa méthode. |
| [`fusion_tstat_eos.py`](fusion_tstat_eos.py) | Fusion du T-stat avec le produit EOS-RS continu, en faisant varier les deux seuils en conjonction et en testant une pondération continue entre les deux termes. |
| [`fusion_tstat_osu.py`](fusion_tstat_osu.py) | Fusion par conjonction du T-stat avec le produit de cohérence OSU, par inclusion progressive des niveaux de confiance et contre trois définitions du positif ; produit le meilleur kappa, le meilleur F1, et le seuil qui minimise les faux positifs à rappel garanti. |
