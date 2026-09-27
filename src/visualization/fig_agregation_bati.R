# ==============================================================================
# LE MODE D'AGREGATION DU PIXEL AU BATIMENT
# ==============================================================================
#
# POURQUOI CETTE FIGURE A ETE REFAITE
# -----------------------------------
# La version precedente portait, en titre grave dans l'image :
#
#     « Le mode d'agregation depend de la facon dont la catastrophe detruit »
#
# Cette affirmation est dementie par les mesures nepalaises, qui rattachent le
# choix au TYPE D'OBJET et non a l'alea : le maximum l'emporte sur les ponts, la
# moyenne sur les routes, et cela sur les deux campagnes ou la mesure est
# possible. Le memoire l'ecrit lui-meme en section 2.4 et en annexe G ; seule
# l'image continuait d'affirmer le contraire.
#
# Cette planche ne montre QUE du bati, sur deux campagnes. Son titre dit donc ce
# qu'elle montre, et le resultat par type d'objet est renvoye au tableau qui le
# porte.
#
# POURQUOI DES POINTS ET NON DES BARRES
# -------------------------------------
# Une barre se lit par sa longueur : elle doit donc partir de zero. Or les
# quatre valeurs jamaicaines tiennent dans cinq millieres — a axe complet, les
# barres seraient identiques, et a axe tronque leur longueur mentirait. Le point
# se lit par sa position : il supporte un axe resserre sans rien exagerer.
#
# RESERVE SUR LES CHIFFRES
# ------------------------
# Ces valeurs sont anterieures a la reevaluation du 1er octobre 2026 : aucune
# famille « agregation » ne figure dans l'experience 75. Elles restent coherentes
# avec le reste du memoire, mais une reprise du calcul dans la convention
# actuelle — Open Buildings en Jamaique, appariement strict — reste a faire.
# ==============================================================================

source("commun.R")
library(patchwork)

d <- read.csv2("agregation_bati.csv", stringsAsFactors = FALSE, dec = ".")

# L'ordre de lecture : du plus diffus au plus local, de bas en haut.
ORDRE <- c("moyenne", "p75", "p90", "maximum")
ETIQ  <- c(moyenne = "moyenne", p75 = "centile 75",
           p90 = "centile 90", maximum = "maximum")
d$agregation <- factor(ETIQ[d$agregation], levels = ETIQ[ORDRE])

# ------------------------------------------------------------------------------
# Un panneau par campagne. Le point gagnant est colore, les autres en gris :
# l'oeil trouve le gagnant sans lire les valeurs.
# ------------------------------------------------------------------------------
panneau <- function(camp, sous, teinte, decimales, note = NULL) {
  p <- d[d$campagne == camp, ]
  p$gagnante <- p$auc == max(p$auc)
  etendue <- diff(range(p$auc))
  bas  <- min(p$auc) - etendue * 0.55
  haut <- max(p$auc) + etendue * 0.55

  g <- ggplot(p, aes(x = auc, y = agregation)) +
    # Un trait fin relie chaque point au bord gauche : il guide l'oeil de
    # l'etiquette vers la valeur, sans encoder de longueur.
    geom_segment(aes(x = bas, xend = auc, yend = agregation),
                 colour = NEUTRE, linewidth = 1.6) +
    geom_point(aes(colour = gagnante), size = 4.2, show.legend = FALSE) +
    geom_text(aes(label = fr(auc, 3, signe = FALSE)), hjust = -0.45,
              size = 3.3, colour = ENCRE_2) +
    scale_colour_manual(values = c(`TRUE` = teinte, `FALSE` = "#c9c8c4")) +
    scale_x_continuous(
      labels = function(v) fr(v, decimales, signe = FALSE),
      expand = expansion(mult = c(0.02, 0.14))) +
    coord_cartesian(xlim = c(bas, haut)) +
    labs(subtitle = sous, x = "AUC par commune, moyenne des deux références",
         y = NULL) +
    theme_etude() +
    theme(plot.subtitle   = element_text(colour = ENCRE, size = 11,
                                         lineheight = 1.3),
          axis.text.y     = element_text(colour = ENCRE, size = 10.5),
          panel.grid.major.y = element_line(colour = NEUTRE, linewidth = 0.3))

  if (!is.null(note)) {
    g <- g + labs(caption = note) +
      theme(plot.caption = element_text(colour = teinte, size = 9,
                                        face = "italic", hjust = 0))
  }
  g
}

gauche <- panneau(
  "Séisme du Venezuela",
  "Séisme du Venezuela\n288 677 bâtiments, 2 communes et plus",
  BLEU, decimales = 2,
  note = "le maximum devance la moyenne de 0,023")

droite <- panneau(
  "Cyclone Melissa (Jamaïque)",
  "Cyclone Melissa, Jamaïque\n2 zones UNOSAT seulement",
  ROUGE, decimales = 3,
  note = "les quatre modes tiennent dans 0,005 : l'écart n'est pas significatif")

fig <- (gauche | droite) +
  plot_annotation(
    title = paste("Sur le bâti, l'ordre des modes d'agrégation change",
                  "d'une campagne à l'autre"),
    subtitle = paste("Le réglage se décide par type d'objet et non par aléa :",
                     "le maximum l'emporte aussi sur les ponts népalais,",
                     "la moyenne sur les routes."),
    caption = paste(
      "Chiffres antérieurs à la réévaluation du 1er octobre 2026 ;",
      "ils restent à reprendre dans la convention actuelle.",
      "\nSource : calculs de l'auteur."),
    theme = theme_etude())

ggsave("fig_agregation_bati.png", fig, width = 11, height = 4.6, dpi = 200,
       bg = FOND)
cat("écrit : fig_agregation_bati.png\n")
