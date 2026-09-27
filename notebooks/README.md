# Les carnets

Six carnets, un par résultat de l'article. Ils ne refont pas les calculs lourds —
ceux-là sont dans [`src/`](../src/) et demandent les données d'entrée — mais ils
**rejouent chaque chiffre cité** à partir des tables embarquées dans
[`data/results/`](../data/results/) et [`tables/`](../tables/).

| carnet | section de l'article | ce qu'il vérifie |
|---|---|---|
| [`01_delai_et_ligne_de_base.ipynb`](01_delai_et_ligne_de_base.ipynb) | 5.1 | le coût d'une image unique, les latences réelles d'acquisition, la longueur de ligne de base retenue |
| [`02_agregation_et_alea.ipynb`](02_agregation_et_alea.ipynb) | 5.3 | que la règle d'agrégation départage les résultats sur un séisme et pas sur un cyclone |
| [`03_emprise_et_classement.ipynb`](03_emprise_et_classement.ipynb) | 6 | le classement sur l'emprise commune — 0,7403 et 0,7324 sur 148 159 bâtiments — et le face-à-face |
| [`04_fusion_ciblee.ipynb`](04_fusion_ciblee.ipynb) | 7.6, 8.2 | le gain de la fusion à deux termes, sa part du gain à douze, et la perte due à la disjonction |
| [`05_deux_usages_et_plancher_de_rappel.ipynb`](05_deux_usages_et_plancher_de_rappel.ipynb) | 8.3 | le dénominateur, la définition du positif, et le coût d'un plancher de rappel à 90 % |
| [`06_coherence_reproduite.ipynb`](06_coherence_reproduite.ipynb) | 7.3 | que la cohérence seule reste sous 0,62, et que sa sortie binaire publiée passe sous le hasard |

## Ce que « vérifier » veut dire ici

Chaque carnet se termine par des **assertions**, pas par un affichage. Si une
table est remplacée par une version qui ne porte plus le chiffre cité dans
l'article, le carnet échoue. C'est donc un test de non-régression de l'article
lui-même, et non une illustration.

Les six ont été exécutés avant d'être publiés, et passent.

## Pour les lancer

```bash
pip install pandas jupyter
cd notebooks
jupyter lab
```

Aucun accès réseau, aucune donnée à télécharger : tout ce qu'ils lisent est dans
le dépôt. Les carnets sont versionnés **sans leurs sorties**, pour que le diff
d'une modification reste lisible.
