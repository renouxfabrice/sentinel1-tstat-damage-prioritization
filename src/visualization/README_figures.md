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

| fichier | à quoi il sert |
|---|---|
| `commun.R` | les couleurs, la typographie et deux fonctions utilitaires. **Ne trace rien.** Modifier ici change toutes les figures d'un coup |
| `noms_zones.R` | la table qui traduit les codes techniques — `EMS_AOI16` — en noms lisibles — « Big Woods (AOI16) ». **Ne trace rien.** C'est ici qu'on ajoute une campagne |
| `fig_exp75.R` | les **quatre figures principales** : l'écart de chaque réglage, les deux balayages de fenêtre postérieure, et la durée de la période de référence |
| `fig_exp74.R` | la comparaison des deux catastrophes → `fig_exp74.png` |
| `fig_exp77.R` | l'image unique face à la série, sur dix emprises et quatre pays, en variance regroupée — elle **remplace** les figures 2.4, 2.5 et G.2 du mémoire, calculées en Welch |
| `fig_exp78.R` | la durée de la période de référence, mêmes emprises, en variance regroupée — elle **remplace** la figure G.3 |
| `obsoletes/` | les figures du 30 septembre, **périmées**. Voir le `LIRE_MOI.md` qui s'y trouve : elles reposent sur une évaluation refaite depuis |

Chaque programme lit ses données dans `../resultats/`, écrit son image **à côté
de lui**, et ne touche à rien d'autre.

## Comment les relancer

Ouvrir une invite de commandes, se placer dans **ce dossier**, puis :

    "C:\Program Files\R\R-4.5.2\bin\Rscript.exe" fig_exp75.R
    "C:\Program Files\R\R-4.5.2\bin\Rscript.exe" fig_exp74.R

Le premier répond `écrit : quatre figures fig_exp75_*.png`, le second
`écrit : fig_exp74.png`. C'est tout.

**Il faut se placer dans ce dossier**, car les programmes cherchent leurs
données dans `../resultats/`, c'est-à-dire « le dossier au-dessus, puis
resultats ». Lancés depuis ailleurs, ils ne trouveront rien et le diront.

## Ce dont R a besoin

R 4.5.2 est installé, ainsi que `ggplot2`, la bibliothèque de graphiques
employée. Rien d'autre n'est nécessaire. Si un jour R signale qu'il ne trouve
pas `ggplot2`, la commande pour l'installer est :

    install.packages("ggplot2")

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

Les deux figures montrent la même chose : **un écart, et sa dispersion**.

Chaque point est une comparaison — une zone, une couche de bâtiments. Le trait
vertical marque le zéro. Le losange est la moyenne, et sa valeur est écrite
au-dessus.

**Pourquoi montrer les quinze points au lieu de la seule moyenne ?** Parce que
la moyenne ment quand la dispersion est grande. Dans la première figure, la
distance de Mahalanobis affiche une moyenne favorable qui tient **entièrement à
une seule zone**, celle où les bâtiments signalés sont très rares. Un diagramme
en barres l'aurait masqué ; le nuage de points le montre immédiatement — ce sont
les deux cercles vides, les plus à droite.

C'est pour la même raison que les zones à moins de 5 % de bâtiments signalés
sont tracées **en cercle vide** plutôt qu'en point plein : leur AUC est estimée
sur trop peu de cas pour être stable, et il vaut mieux le signaler que de
l'enfouir dans une moyenne.

**Une curiosité de la seconde figure** : les deux premières lignes sont
rigoureusement superposées. Ce n'est pas un défaut de tracé. Avec une seule
image après l'événement, le score z et le test à variance regroupée ne diffèrent
que d'un facteur constant, et un facteur constant ne déplace pas un classement.
La figure démontre à l'œil ce que l'algèbre annonçait.

## Si une figure ne se trace pas

| message | ce qu'il veut dire |
|---|---|
| `Fichier introuvable : ...` | les données n'existent pas encore. Lancer d'abord `code\exp75_tout_reevaluer.py` |
| `there is no package called 'ggplot2'` | la bibliothèque manque : `install.packages("ggplot2")` |
| `cannot open file 'commun.R'` | vous n'êtes pas dans ce dossier. Se déplacer dedans avant de lancer |

## D'où viennent les données

    ../resultats/exp75_detail.csv          une ligne par emprise × configuration,
                                          toutes les expériences jamaïcaines réunies
    ../resultats/exp74_deux_campagnes.csv  la Jamaïque et le Venezuela côte à côte

Ces fichiers sont écrits par les programmes d'évaluation, qui lisent eux-mêmes
les cartes du dossier `../cartes/`. La chaîne complète, de l'image satellite à
la figure, est donc rejouable de bout en bout — et chaque maillon est un fichier
que l'on peut ouvrir et lire.
