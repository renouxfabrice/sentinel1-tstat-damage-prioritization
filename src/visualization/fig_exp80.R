# ==============================================================================
# L'IMAGE UNIQUE SELON LE DELAI — SUR LA CONVENTION D'EVALUATION DU MEMOIRE
# ==============================================================================
#
# CE QU'ELLE REMPLACE
# -------------------
# Les figures 2.4 et 2.5 du memoire. Celles-ci comparaient le score a une image
# a un test de WELCH, et les evaluaient sur OpenStreetMap avec un accrochage des
# points a vingt metres du centroide.
#
# Deux choses ont ete refaites. Le CALCUL d'abord, en variance regroupee et
# orbites combinees par maximum, c'est-a-dire dans la configuration de l'outil
# (experience 77). L'EVALUATION ensuite, sur Open Buildings en Jamaique et
# Overture au Venezuela, avec la regle d'appariement stricte de l'annexe X
# (experience 80).
#
# CE QU'ELLE MONTRE
# -----------------
# Pour chaque emprise, ce que coute le fait de n'avoir qu'une seule image, place
# en regard du delai auquel cette image arrive.
#
# Les emprises dont la prevalence sort de l'intervalle de 5 a 95 % sont tracees
# en creux : l'aire sous la courbe n'y mesure rien de fiable, mais les retirer
# sans le dire donnerait une fausse impression de completude.
#
# LES DONNEES
#   AUC    <- exp80_une_image_reevaluee.csv
#   delais <- exp77_une_image_regroupee.csv, car les dates d'acquisition ne
#             dependent ni du test employe ni de la couche batie.
# ==============================================================================

source("commun.R")
source("noms_zones.R")

PREV_MIN <- 5
PREV_MAX <- 95

auc <- lire_resultat("exp80_une_image_reevaluee.csv")
delais <- lire_resultat("exp77_une_image_regroupee.csv")

une <- subset(auc, mode == "ztest",
              select = c("zone", "emprise", "pays", "auc", "prevalence_pct"))
names(une)[names(une) == "auc"] <- "auc_1img"

multi <- subset(auc, mode == "poole")
if (nrow(multi) == 0) stop("aucune mesure multi-images dans exp80")
meilleur <- aggregate(auc ~ zone, data = multi, FUN = max)
names(meilleur)[2] <- "auc_multi"

p <- merge(une, meilleur, by = "zone")
p$ecart <- p$auc_1img - p$auc_multi
p$fiable <- p$prevalence_pct >= PREV_MIN & p$prevalence_pct <= PREV_MAX

d1 <- subset(delais, mode == "ztest", select = c("zone", "duree_post_jours"))
names(d1)[2] <- "jours"
p <- merge(p, d1, by = "zone")
if (nrow(p) == 0) stop("aucune emprise appariée entre les deux fichiers")

# ggrepel n'est pas installe et plusieurs emprises partagent le meme delai :
# on ecarte les etiquettes a la main, d'un pas proportionnel a l'etendue.
p <- p[order(p$jours, p$ecart), ]
pas <- diff(range(p$ecart)) * 0.06
p$decalage <- 0
for (j in unique(p$jours)) {
  k <- which(p$jours == j)
  if (length(k) > 1) p$decalage[k] <- (seq_along(k) - mean(seq_along(k))) * pas
}

g <- ggplot(p, aes(x = jours, y = ecart)) +
  geom_hline(yintercept = 0, colour = SOURD, linewidth = 0.6) +
  geom_segment(aes(xend = jours, yend = ecart + decalage), colour = SOURD,
               linewidth = 0.3) +
  geom_point(aes(colour = pays, shape = fiable), size = 3.6, stroke = 1.1) +
  geom_text(aes(y = ecart + decalage, label = emprise), hjust = -0.08,
            size = 2.9, colour = ENCRE_2) +
  scale_shape_manual(values = c(`TRUE` = 16, `FALSE` = 1),
                     labels = c(`TRUE` = "prévalence entre 5 et 95 %",
                                `FALSE` = "hors de cet intervalle"),
                     name = NULL) +
  scale_x_continuous(labels = function(v) fr(v, 1, signe = FALSE),
                     expand = expansion(mult = c(0.08, 0.34))) +
  scale_y_continuous(labels = function(v) fr(v, 2)) +
  labs(title = "Écart d'AUC de l'image unique, selon le délai de la première image",
       subtitle = paste("L'écart est négatif lorsque l'image unique classe",
                        "moins bien\nque la meilleure série multi-images",
                        "disponible."),
       x = "délai de la première image utilisable, en jours",
       y = "AUC à une image moins AUC multi-images", colour = NULL,
       caption = paste(
         "Calcul en variance regroupée et orbites combinées par maximum,",
         "comme dans l'outil.",
         "\nÉvaluation sur Open Buildings en Jamaïque et Overture au Venezuela,",
         "appariement strict.",
         "\nSource : calculs de l'auteur, expériences 77 et 80.")) +
  theme_etude() +
  theme(legend.position = "top", legend.box = "vertical",
        legend.box.just = "left")

ggsave("fig_exp80_ecart_selon_delai.png", g, width = 10, height = 5.4,
       dpi = 200, bg = FOND)
cat("écrit : fig_exp80_ecart_selon_delai.png\n")
