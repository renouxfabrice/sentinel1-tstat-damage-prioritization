# ==============================================================================
# L'IMAGE UNIQUE FACE A LA SERIE, SUR QUATRE PAYS
# ==============================================================================
#
# CE QU'ELLE REMPLACE
# -------------------
# Les figures 5 et 7 du memoire comparaient le score a une image a un test de
# WELCH calcule sur trois a neuf images, les orbites etant combinees par somme
# de Stouffer. Ce n'est pas ce que calcule l'outil : il emploie la variance
# regroupee et combine par maximum, comme le code publie avec l'article.
#
# L'experience 77 refait la mesure dans la configuration de l'outil. Les deux
# termes compares ici sont donc tous deux en variance regroupee.
#
# CE QU'ELLE MONTRE
# -----------------
# Pour chaque emprise, l'AUC du score a une seule image — disponible vers J+2,5
# — et celle obtenue a mesure que les acquisitions posterieures s'accumulent.
# Le point gris le plus a droite de chaque ligne est la serie la plus longue.
#
# Les emprises sont rangees par delai de la premiere image, parce que c'est ce
# delai, et non le type d'alea, qui commande le resultat.
# ==============================================================================

source("commun.R")
source("noms_zones.R")

d <- lire_resultat("exp77_une_image_regroupee.csv")
d$zone_lisible <- nommer(d$zone)

# L'AUC a une image, et la meilleure AUC multi-images, pour chaque emprise.
une <- subset(d, mode == "ztest", select = c("zone", "zone_lisible", "pays",
                                             "alea", "auc",
                                             "delai_premiere_image_h"))
names(une)[names(une) == "auc"] <- "auc_1img"

multi <- subset(d, mode == "poole")
if (nrow(multi) == 0) stop("aucune mesure multi-images dans le fichier")
meilleur <- aggregate(auc ~ zone, data = multi, FUN = max)
names(meilleur)[2] <- "auc_multi"

p <- merge(une, meilleur, by = "zone")
p <- p[order(p$delai_premiere_image_h), ]
p$etiquette <- factor(p$zone_lisible, levels = rev(p$zone_lisible))
p$ecart <- p$auc_1img - p$auc_multi

# ------------------------------------------------------------------------------
# Figure 1 — les deux AUC cote a cote, une ligne par emprise.
# ------------------------------------------------------------------------------
long <- rbind(
  data.frame(etiquette = p$etiquette, auc = p$auc_1img, pays = p$pays,
             quoi = "une seule image"),
  data.frame(etiquette = p$etiquette, auc = p$auc_multi, pays = p$pays,
             quoi = "la meilleure série multi-images"))

g1 <- ggplot(long, aes(x = auc, y = etiquette)) +
  geom_vline(xintercept = 0.5, colour = SOURD, linewidth = 0.6,
             linetype = "22") +
  geom_line(aes(group = etiquette), colour = SOURD, linewidth = 0.6,
            alpha = 0.7) +
  geom_point(aes(colour = quoi), size = 3.4) +
  scale_colour_manual(values = c("une seule image" = BLEU,
                                 "la meilleure série multi-images" = ROUGE),
                      name = NULL) +
  scale_x_continuous(labels = function(v) fr(v, 2, signe = FALSE)) +
  labs(title = "AUC d'une seule image et de la meilleure série multi-images",
       subtitle = paste("Les deux termes sont calculés à variance regroupée et",
                        "combinés par maximum entre orbites,\ncomme dans",
                        "l'outil. Les emprises sont rangées par délai de la",
                        "première image."),
       x = "AUC", y = NULL,
       caption = paste(
         "Dix emprises réparties sur quatre pays — Jamaïque, Cuba, Colombie,",
         "Venezuela — et deux types d'aléa.\nLe trait vertical marque 0,50 :",
         "en deçà, le score classe moins bien qu'un tirage au sort.",
         "\nSource : calculs de l'auteur, exp77.")) +
  theme_etude() +
  theme(legend.position = "top")

ggsave("fig_exp77_image_unique_vs_serie.png", g1, width = 10, height = 5.6,
       dpi = 200, bg = FOND)

# ------------------------------------------------------------------------------
# Figure 2 — l'ecart, en fonction du delai de la premiere image.
# ------------------------------------------------------------------------------
p$jours <- p$delai_premiere_image_h / 24

# ggrepel n'etant pas installe, on ecarte les etiquettes a la main : les
# emprises qui partagent le meme delai sont decalees verticalement d'un pas
# proportionnel a l'etendue des ecarts, sans quoi elles se superposent.
p <- p[order(p$jours, p$ecart), ]
pas <- diff(range(p$ecart)) * 0.055
p$decalage <- 0
for (j in unique(p$jours)) {
  k <- which(p$jours == j)
  if (length(k) > 1) {
    p$decalage[k] <- (seq_along(k) - mean(seq_along(k))) * pas
  }
}

g2 <- ggplot(p, aes(x = jours, y = ecart)) +
  geom_hline(yintercept = 0, colour = SOURD, linewidth = 0.6) +
  geom_segment(aes(xend = jours, yend = ecart + decalage), colour = SOURD,
               linewidth = 0.3) +
  geom_point(aes(colour = pays), size = 3.6) +
  geom_text(aes(y = ecart + decalage, label = zone_lisible), hjust = -0.08,
            size = 2.9, colour = ENCRE_2) +
  scale_x_continuous(labels = function(v) fr(v, 1, signe = FALSE),
                     expand = expansion(mult = c(0.06, 0.34))) +
  scale_y_continuous(labels = function(v) fr(v, 2)) +
  labs(title = "Écart d'AUC de l'image unique, selon le délai de la première image",
       subtitle = paste("L'écart est négatif lorsque l'image unique classe moins bien",
                        "
que la meilleure série multi-images disponible."),
       x = "délai de la première image utilisable, en jours",
       y = "AUC à une image moins AUC multi-images",
       caption = paste(
         "Dix emprises, quatre pays, deux types d'aléa.",
         "\nSource : calculs de l'auteur, exp77.")) +
  theme_etude()

ggsave("fig_exp77_ecart_selon_delai.png", g2, width = 10, height = 5.2,
       dpi = 200, bg = FOND)

cat("écrit : fig_exp77_image_unique_vs_serie.png et fig_exp77_ecart_selon_delai.png\n")
