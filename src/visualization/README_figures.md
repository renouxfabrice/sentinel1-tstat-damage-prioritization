# Les figures, en R — comment elles sont faites, comment les refaire

*Écrit pour quelqu'un qui ne pratique pas R. Chaque étape est expliquée.*

---

## Le principe, en une phrase

**Une figure n'est pas un dessin, c'est une conséquence d'un fichier de
données.** Chaque graphique est produit par un petit programme qui lit un CSV et
écrit une image. Si les calculs sont refaits, il suffit de relancer le
programme : la figure se met à jour toute seule, sans retouche.

C'est ce qui permet de répondre sereinement à la question « comment avez-vous
construit ce graphique ? » — la réponse est un fichier de vingt lignes utiles,
lisible, que l'on peut montrer.

## Ce qu'il y a dans ce dossier

Dix fichiers `.R` : deux qui ne tracent rien, et huit qui écrivent une image.

| fichier | à quoi il sert |
|---|---|
| `commun.R` | les couleurs, la typographie, et la fonction qui va chercher les tables. **Ne trace rien.** Modifier ici change toutes les figures d'un coup |
| `noms_zones.R` | la table qui traduit les codes techniques — `EMS_AOI16` — en noms lisibles — « Big Woods (AOI16) ». **Ne trace rien.** C'est ici qu'on ajoute une campagne |
| `fig_memoire.R` | les **figures 5, 6 et 7** de l'étude : l'image unique face à la série, l'arbitrage coût/délai, et la longueur de la période de référence. Écrit `fig_memoire_2_4.png`, `fig_memoire_2_5.png` et `fig_memoire_G_3.png` |
| `fig_exp75.R` | l'écart de chaque réglage à la configuration de référence, et les deux balayages de fenêtre postérieure. Écrit quatre images `fig_exp75_*.png` |
| `fig_exp77.R` | l'image unique face à la série, dans sa première version — dix emprises, quatre pays. Écrit `fig_exp77_image_unique_vs_serie.png` et `fig_exp77_ecart_selon_delai.png` |
| `fig_exp80.R` | la même comparaison après la réévaluation du 1er octobre. Écrit `fig_exp80_ecart_selon_delai.png` |
| `fig_agregation_bati.R` | la **figure 10** : l'ordre des modes d'agrégation sur les deux campagnes. Écrit `fig_agregation_bati.png` |
| `fig_exp82.R` | les routes et les ponts du Népal. Écrit `fig_exp82_nepal_infrastructure.png` |
| `fig_exp83_panneau.R` | la courbe du pont emporté, panneau de la **figure 17**. Écrit `panneau_nepal_courbe.png` |
| `fig_exp86_panneau_piste.R` | la courbe de la piste ensevelie, second panneau de la figure 17. Écrit `panneau_piste_courbe.png` |

Chaque programme lit ses données dans `../../data/results/`, écrit son image
**à côté de lui**, et ne touche à rien d'autre.

Les autres figures de l'étude — planches d'imagerie, schémas, cartes — ne sont
pas tracées en R. Leur provenance est donnée dans leur légende.

## Comment les relancer

Ouvrir une invite de commandes, se placer dans **ce dossier**, puis :

    "C:\Program Files\R\R-4.5.2\bin\Rscript.exe" fig_memoire.R
    "C:\Program Files\R\R-4.5.2\bin\Rscript.exe" fig_agregation_bati.R

Le premier répond `écrit : fig_memoire_2_4.png, fig_memoire_2_5.png,
fig_memoire_G_3.png`, le second `écrit : fig_agregation_bati.png`. C'est tout.

**Il faut se placer dans ce dossier**, car les programmes cherchent leurs
données dans `../../data/results/`, c'est-à-dire « deux dossiers au-dessus, puis
`data`, puis `results` ». Lancés depuis ailleurs, ils ne trouveront rien et le
diront.

## Ce dont R a besoin

R 4.5.2, ainsi que `ggplot2` et `patchwork`. Rien d'autre. Si R signale qu'il ne
trouve pas une bibliothèque :

    install.packages(c("ggplot2", "patchwork"))

## Comment modifier une figure

Les programmes sont commentés en français, et les endroits à modifier sont
signalés en tête de chaque fichier. Les trois modifications les plus courantes :

**Changer les couleurs.** Tout est en haut de `commun.R`, avec une ligne
d'explication par couleur. Une précaution : le bleu et le rouge ne sont pas
choisis au hasard. Ils encodent un **signe** — favorable ou défavorable — et
doivent rester lisibles par un daltonien. Deux couleurs froides, bleu et
turquoise par exemple, seraient un mauvais choix : le point médian ne se lirait
plus comme « rien ».

**Changer l'ordre ou le nom des lignes.** Dans chaque `fig_*.R`, chercher les
objets `ordre` et `noms`. Le premier fixe l'ordre d'affichage, le second les
intitulés lisibles.

**Changer la taille de l'image.** Dernière ligne du fichier, dans l'appel à
`ggsave` : `width` et `height` sont en pouces, `dpi` la résolution. Pour une
impression, monter `dpi` à 300.

## Comment ces figures sont construites, et pourquoi ainsi

Plusieurs d'entre elles montrent la même chose : **un écart, et sa dispersion**.

Chaque point est une comparaison — une zone, une couche de bâtiments. Le trait
vertical marque le zéro. Le losange est la moyenne, et sa valeur est écrite
au-dessus.

**Pourquoi montrer tous les points au lieu de la seule moyenne ?** Parce que la
moyenne ment quand la dispersion est grande. Dans la première figure de
`fig_exp75.R`, la distance de Mahalanobis affiche une moyenne favorable qui
tient **entièrement à une seule zone**, celle où les bâtiments signalés sont
très rares. Un diagramme en barres l'aurait masqué ; le nuage de points le
montre immédiatement — ce sont les deux cercles vides, les plus à droite.

C'est pour la même raison que les zones à moins de 5 % de bâtiments signalés
sont tracées **en cercle vide** plutôt qu'en point plein : leur AUC est estimée
sur trop peu de cas pour être stable, et il vaut mieux le signaler que de
l'enfouir dans une moyenne.

**Une curiosité de `fig_exp77.R`** : les deux premières lignes sont
rigoureusement superposées. Ce n'est pas un défaut de tracé. Avec une seule
image après l'événement, le score z et le test à variance regroupée ne diffèrent
que d'un facteur constant, et un facteur constant ne déplace pas un classement.
La figure démontre à l'œil ce que l'algèbre annonçait.

## Si une figure ne se trace pas

| message | ce qu'il veut dire |
|---|---|
| `Fichier introuvable : ...` | la table n'est pas là où le programme la cherche. Vérifier qu'on est bien dans ce dossier ; sinon, relancer le programme d'évaluation correspondant dans [`../reevaluation/`](../reevaluation/) |
| `there is no package called 'ggplot2'` | la bibliothèque manque : `install.packages("ggplot2")` |
| `cannot open file 'commun.R'` | vous n'êtes pas dans ce dossier. Se déplacer dedans avant de lancer |

## D'où viennent les données

Les huit programmes qui tracent lisent ces tables, toutes embarquées dans le
dépôt :

    ../../data/results/exp75_detail.csv                 une ligne par emprise × configuration
    ../../data/results/exp77_une_image_regroupee.csv    l'image unique, première version
    ../../data/results/exp80_une_image_reevaluee.csv    la même, réévaluée le 1er octobre
    ../../data/results/exp81_fenetre_pre_reevaluee.csv  la longueur de la période de référence
    ../../data/results/exp82_nepal.csv                  les routes et les ponts du Népal
    ../../data/results/exp83_serie_vv_bidur.csv         la série VV du pont emporté
    ../../data/results/exp86_serie_vv_piste.csv         la série VV de la piste ensevelie
    ../../data/results/agregation_bati.csv              les quatre modes d'agrégation

Ces fichiers sont écrits par les programmes d'évaluation de
[`../reevaluation/`](../reevaluation/), qui lisent eux-mêmes les cartes de score.
La chaîne complète, de l'image satellite à la figure, est donc rejouable de bout
en bout — et chaque maillon est un fichier que l'on peut ouvrir et lire. Seul le
module du test t n'est pas fourni : voir la section « À propos du test t » du
README.
