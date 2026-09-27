# ==============================================================================
# REGLAGES COMMUNS AUX FIGURES
# ==============================================================================
#
# Ce fichier ne trace rien. Il definit la palette, le theme et deux fonctions
# utilitaires, pour que toutes les figures se ressemblent et qu'un changement de
# style se fasse a un seul endroit.
#
# LA PALETTE, ET POURQUOI CELLE-CI
# --------------------------------
# Les figures montrent des ECARTS : une valeur peut etre favorable ou
# defavorable, et le zero est une frontiere qui a un sens. C'est exactement le
# cas d'usage d'une palette dite « divergente » : deux teintes opposees, une
# chaude et une froide, separees par un gris neutre.
#
# Le bleu et le rouge sont retenus parce qu'ils se lisent comme opposes, y
# compris par un daltonien : leur difference porte autant sur la clarte que sur
# la teinte. Une paire bleu/turquoise, par exemple, serait mauvaise — les deux
# etant froides, le point median ne se lirait pas comme « rien ».
#
# Ces valeurs viennent d'une palette validee ; ne pas les remplacer au jugé.
# ==============================================================================

BLEU    <- "#2a78d6"   # favorable  : la variante classe mieux que la reference
ROUGE   <- "#e34948"   # defavorable : elle classe moins bien
NEUTRE  <- "#f0efec"   # le zero, et les aplats de fond
ENCRE   <- "#0b0b0b"   # texte principal
ENCRE_2 <- "#52514e"   # texte secondaire
SOURD   <- "#898781"   # axes, grilles, legendes
FOND    <- "#fcfcfb"   # la surface du graphique

library(ggplot2)

# ------------------------------------------------------------------------------
# Le theme : tout ce qui n'est pas la donnee doit s'effacer devant elle.
# Pas de grille verticale inutile, pas de cadre, des axes discrets.
# ------------------------------------------------------------------------------
theme_etude <- function(base_size = 12) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.background    = element_rect(fill = FOND, colour = NA),
      panel.background   = element_rect(fill = FOND, colour = NA),
      panel.grid.major.y = element_blank(),
      panel.grid.minor   = element_blank(),
      panel.grid.major.x = element_line(colour = NEUTRE, linewidth = 0.4),
      axis.text          = element_text(colour = ENCRE_2),
      axis.title         = element_text(colour = ENCRE_2, size = base_size - 1),
      plot.title         = element_text(colour = ENCRE, face = "bold",
                                        size = base_size + 3),
      plot.subtitle      = element_text(colour = ENCRE_2, size = base_size - 1,
                                        lineheight = 1.2),
      plot.caption       = element_text(colour = SOURD, size = base_size - 3,
                                        hjust = 0, lineheight = 1.2),
      legend.position    = "top",
      legend.title       = element_blank(),
      legend.text        = element_text(colour = ENCRE_2, size = base_size - 1),
      plot.margin        = margin(16, 20, 12, 16)
    )
}

# ------------------------------------------------------------------------------
# Un nombre a la francaise : virgule decimale et vrai signe moins.
# ------------------------------------------------------------------------------
fr <- function(x, n = 4, signe = TRUE) {
  s <- formatC(x, format = "f", digits = n, flag = if (signe) "+" else "")
  s <- gsub("\\.", ",", s)
  gsub("-", "−", s)
}

# ------------------------------------------------------------------------------
# Lire un CSV de l'experience. Le separateur est le point-virgule, et le point
# decimal est un point : c'est ce qu'ecrit `evaluation_commune.py`.
# ------------------------------------------------------------------------------
lire_resultat <- function(nom) {
  chemin <- file.path("..", "resultats", nom)
  if (!file.exists(chemin)) {
    stop("Fichier introuvable : ", normalizePath(chemin, mustWork = FALSE),
         "\nLancez d'abord le programme d'evaluation correspondant.")
  }
  read.csv2(chemin, stringsAsFactors = FALSE, dec = ".")
}
