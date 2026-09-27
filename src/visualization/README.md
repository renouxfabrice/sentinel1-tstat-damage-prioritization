# Les figures

Les figures de ce dépôt sont désormais **produites par des programmes**, et non
composées à la main. Chacune lit une table de
[`data/results/`](../../data/results/) et écrit une image ; relancer le
programme après un recalcul met la figure à jour sans retouche.

| programme | ce qu'il produit |
|---|---|
| `commun.R` | les couleurs, la typographie et deux fonctions utilitaires. **Ne trace rien** |
| `noms_zones.R` | la table qui traduit les codes techniques en noms de lieux — « Big Woods (AOI16) ». **Ne trace rien** |
| `fig_memoire.R` | les figures 5, 6 et 7 |
| `fig_exp75.R` | l'écart de chaque réglage à la référence, et les balayages de fenêtre |
| `fig_exp77.R`, `fig_exp80.R` | l'image unique face à la série, sur dix emprises et quatre pays |
| `fig_exp82.R` | les routes et les ponts du Népal |
| `fig_exp83_panneau.R`, `fig_exp86_panneau_piste.R` | les deux courbes de la figure 17 |

Les vignettes optiques de la figure 17 sont assemblées à partir des tuiles
d'OpenAerialMap ; seules les courbes viennent de R.

Le mode d'emploi détaillé, écrit pour quelqu'un qui ne pratique pas R, se trouve
dans [`README_figures.md`](README_figures.md).

## Les figures refaites le 1er octobre 2026

Les figures 5, 6 et 7 avaient été calculées avec le test de Welch et les orbites
combinées par somme de Stouffer, puis évaluées sur OpenStreetMap avec un
accrochage des points à vingt mètres du centroïde. Ce n'est ni la configuration
de l'outil, ni la convention d'évaluation retenue. Elles ont été refaites en
variance regroupée, orbites combinées par maximum, sur Open Buildings en
Jamaïque et Overture au Venezuela, avec l'appariement strict décrit en
section 5.3. Les versions précédentes sont conservées sous
`figures/*.avant_recalcul`.
