# ==============================================================================
# LES PLANCHES DU MEMOIRE, REFAITES
# ==============================================================================
#
# POURQUOI CE PROGRAMME EXISTE
# ----------------------------
# Les figures 2.4, 2.5, G.2 et G.3 du memoire ont ete calculees en test de Welch
# avec les orbites combinees par somme de Stouffer, et evaluees sur
# OpenStreetMap avec un accrochage des points a vingt metres du centroide. Le
# texte qui les entoure a depuis ete corrige ; elles ne disaient donc plus la
# meme chose que lui.
#
# Elles sont ici refaites dans la configuration reelle de l'outil — variance
# regroupee, maximum entre orbites — et sur la convention d'evaluation decrite
# a l'annexe X : Open Buildings en Jamaique, Overture au Venezuela, appariement
# strict, filtre de prevalence borne des deux cotes.
#
# CE QU'ELLES REMPLACENT
#   fig_memoire_2_4.png   <- figure 2.4  (une image face a plusieurs)
#   fig_memoire_2_5.png   <- figures 2.5 et G.2, qui sont la meme planche
#   fig_memoire_G_3.png   <- figure G.3  (longueur de la periode de reference)
#
# Les legendes du memoire sont conservees dans leur esprit ; seuls les chiffres
# changent.
# ==============================================================================

source("commun.R")
source("noms_zones.R")
library(patchwork)

PREV_MIN <- 5
PREV_MAX <- 95

auc <- lire_resultat("exp80_une_image_reevaluee.csv")
delais <- lire_resultat("exp77_une_image_regroupee.csv")
pre <- lire_resultat("exp81_fenetre_pre_reevaluee.csv")

for (d in c("auc", "pre")) {
  x <- get(d); x$emprise <- nommer(x$zone); assign(d, x)
}

# Seules les emprises ou l'aire sous la courbe mesure quelque chose.
fiable <- function(x) subset(x, prevalence_pct >= PREV_MIN &
                                prevalence_pct <= PREV_MAX)

# ──────────────────────────────────────────────────────────────────────────────
# FIGURE 2.4 — l'image unique face aux series multi-images
# ──────────────────────────────────────────────────────────────────────────────
# Les delais viennent de l'experience 77 : une date d'acquisition ne depend ni
# du test employe ni de la couche batie.
d77 <- unique(delais[, c("zone", "mode", "n_images_post", "duree_post_jours")])
a <- merge(fiable(auc), d77, by = c("zone", "mode", "n_images_post"))

une <- subset(a, mode == "ztest")
multi <- subset(a, mode == "poole")

g24 <- ggplot(multi, aes(x = duree_post_jours, y = auc)) +
  geom_hline(yintercept = 0.5, colour = SOURD, linewidth = 0.5,
             linetype = "22") +
  geom_line(aes(group = emprise), colour = SOURD, linewidth = 0.6,
            alpha = 0.8) +
  geom_point(colour = ENCRE_2, size = 1.8) +
  geom_point(data = une, shape = 23, size = 3.6, stroke = 1.1,
             fill = ROUGE, colour = ENCRE) +
  geom_text(data = une, aes(label = paste0("J+", fr(duree_post_jours, 1,
                                                    signe = FALSE))),
            hjust = -0.35, size = 2.7, colour = ENCRE_2) +
  facet_wrap(~ emprise, ncol = 3, scales = "free_y") +
  scale_x_continuous(labels = function(v) paste0("J+", round(v)),
                     expand = expansion(mult = c(0.10, 0.06))) +
  # Trois decimales : sur une emprise dont l'AUC ne varie que de quelques
  # millemes, deux decimales donneraient trois fois la meme graduation.
  scale_y_continuous(labels = function(v) fr(v, 3, signe = FALSE)) +
  labs(title = "Une image après l'événement face à plusieurs acquisitions",
       subtitle = paste("Le losange rouge est le score à une seule image ; les",
                        "points suivent l'accumulation\ndes acquisitions",
                        "postérieures. Le trait horizontal marque 0,50."),
       x = "délai de la dernière image employée", y = "AUC",
       caption = paste(
         "Calcul en variance regroupée, orbites combinées par maximum, comme",
         "dans l'outil.",
         "\nSeules les emprises dont la prévalence reste entre 5 et 95 % sont",
         "tracées.",
         "\nSource : calculs de l'auteur, expériences 77 et 80.")) +
  theme_etude() +
  theme(strip.text = element_text(face = "bold", size = 8.5),
        panel.grid.major.y = element_line(colour = NEUTRE, linewidth = 0.4))

ggsave("fig_memoire_2_4.png", g24, width = 10, height = 6.2, dpi = 200,
       bg = FOND)

# ──────────────────────────────────────────────────────────────────────────────
# FIGURE 2.5 et G.2 — ce que l'image unique coûte, ce qu'elle fait gagner
# ──────────────────────────────────────────────────────────────────────────────
# À gauche : l'écart par emprise. À droite : le délai auquel chaque
# configuration devient disponible, et la cible des 48 heures.
trois <- subset(a, mode == "poole" & n_images_post == 3,
                select = c("zone", "emprise", "auc", "duree_post_jours"))
names(trois)[3:4] <- c("auc_3img", "jours_3img")
u <- subset(une, select = c("zone", "emprise", "pays", "auc",
                            "duree_post_jours"))
names(u)[4:5] <- c("auc_1img", "jours_1img")
p <- merge(u, trois, by = c("zone", "emprise"))
p$ecart <- p$auc_1img - p$auc_3img
p <- p[order(p$ecart), ]
p$emprise <- factor(p$emprise, levels = p$emprise)

gauche <- ggplot(p, aes(x = ecart, y = emprise)) +
  geom_vline(xintercept = 0, colour = SOURD, linewidth = 0.6) +
  geom_segment(aes(x = 0, xend = ecart, yend = emprise),
               colour = SOURD, linewidth = 0.9) +
  geom_point(aes(colour = ecart >= 0), size = 3.4) +
  geom_text(aes(label = fr(ecart, 3)),
            hjust = ifelse(p$ecart >= 0, -0.25, 1.25), size = 2.9,
            colour = ENCRE) +
  scale_colour_manual(values = c(`TRUE` = BLEU, `FALSE` = ROUGE),
                      guide = "none") +
  scale_x_continuous(labels = function(v) fr(v, 2),
                     expand = expansion(mult = 0.24)) +
  labs(title = "Ce que l'image unique coûte",
       subtitle = "écart d'AUC avec la configuration à trois images",
       x = NULL, y = NULL) +
  theme_etude()

# Le panneau de droite : la disponibilité, et la cible opérationnelle.
dispo <- data.frame(
  configuration = c("une seule image", "trois images"),
  jours = c(median(p$jours_1img), median(p$jours_3img)))

droite <- ggplot(dispo, aes(x = jours, y = configuration)) +
  geom_vline(xintercept = 2, colour = ROUGE, linewidth = 0.7,
             linetype = "22") +
  annotate("text", x = 2, y = "trois images", label = "cible : 48 h",
           hjust = -0.08, vjust = -1.6, size = 2.9, colour = ROUGE) +
  geom_segment(aes(x = 0, xend = jours, yend = configuration),
               colour = SOURD, linewidth = 0.9) +
  geom_point(size = 3.6, colour = BLEU) +
  geom_text(aes(label = paste0("J+", fr(jours, 1, signe = FALSE))),
            hjust = -0.3, size = 3, colour = ENCRE) +
  scale_x_continuous(limits = c(0, max(dispo$jours) * 1.3),
                     labels = function(v) paste0("J+", round(v))) +
  labs(title = "Ce qu'elle fait gagner",
       subtitle = "délai médian auquel le résultat devient disponible",
       x = NULL, y = NULL) +
  theme_etude()

g25 <- (gauche | droite) +
  plot_layout(widths = c(1.45, 1)) +
  plot_annotation(
    caption = paste(
      "Calcul en variance regroupée, orbites combinées par maximum.",
      "Évaluation sur Open Buildings en Jamaïque et Overture au Venezuela,",
      "\nappariement strict. La ligne des 48 heures est un objectif, non un",
      "délai atteint dans cette expérience.",
      "\nSource : calculs de l'auteur, expériences 77 et 80."),
    theme = theme_etude())

ggsave("fig_memoire_2_5.png", g25, width = 11, height = 4.8, dpi = 200,
       bg = FOND)

# ──────────────────────────────────────────────────────────────────────────────
# FIGURE G.3 — la longueur de la période de référence
# ──────────────────────────────────────────────────────────────────────────────
pf <- fiable(pre)
moy <- aggregate(auc ~ fenetre_pre_mois, data = pf, FUN = mean)
moy$etiquette <- fr(moy$auc, 3, signe = FALSE)
paliers <- sort(unique(pf$fenetre_pre_mois))

gG3 <- ggplot(pf, aes(x = fenetre_pre_mois, y = auc)) +
  geom_line(aes(group = emprise, colour = pays), linewidth = 0.6,
            alpha = 0.8) +
  geom_text(data = subset(pf, fenetre_pre_mois == max(paliers)),
            aes(label = emprise, colour = pays), hjust = -0.06, size = 2.8,
            show.legend = FALSE) +
  geom_line(data = moy, colour = ENCRE, linewidth = 1.5) +
  geom_point(data = moy, colour = ENCRE, size = 3) +
  geom_text(data = moy, aes(label = etiquette), vjust = -1.3, size = 3.1,
            colour = ENCRE) +
  scale_x_continuous(breaks = paliers,
                     expand = expansion(mult = c(0.04, 0.30))) +
  scale_y_continuous(labels = function(v) fr(v, 2, signe = FALSE)) +
  labs(title = "AUC selon la longueur de la période de référence",
       subtitle = paste("Trois images postérieures. La ligne noire est la",
                        "moyenne des emprises retenues."),
       x = "longueur de la période de référence, en mois", y = "AUC",
       colour = NULL,
       caption = paste(
         "Calcul en variance regroupée, orbites combinées par maximum, comme",
         "dans l'outil.",
         "\nSeules les emprises dont la prévalence reste entre 5 et 95 % sont",
         "tracées : ailleurs l'AUC ne mesure rien.",
         "\nSource : calculs de l'auteur, expérience 81.")) +
  theme_etude() +
  theme(legend.position = "top",
        panel.grid.major.y = element_line(colour = NEUTRE, linewidth = 0.4))

ggsave("fig_memoire_G_3.png", gG3, width = 10, height = 5.4, dpi = 200,
       bg = FOND)

cat("écrit : fig_memoire_2_4.png, fig_memoire_2_5.png, fig_memoire_G_3.png\n")
