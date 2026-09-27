# ==============================================================================
# LE T-STAT SUR L'INFRASTRUCTURE — NEPAL, LAVE TORRENTIELLE D'AOUT 2026
# ==============================================================================
#
# CE QU'ELLE MONTRE
# -----------------
# Le pouvoir de classement du T-stat sur des routes et des ponts, avec la serie
# complete d'images posterieures d'un cote, et la seule premiere image — arrivee
# a J+2,52 — de l'autre.
#
# CE QUI REND CES MESURES PARTICULIERES
# -------------------------------------
# Les negatifs sont DECLARES et non deduits. Copernicus note explicitement
# « No visible damage » sur les routes, et HOT note « Standing » sur les ponts.
# Partout ailleurs dans ce travail, un objet est negatif parce que personne ne
# l'a signale — ce qui confond « intact » et « non regarde ».
#
# Les emprises dont la prevalence atteint cent pour cent sont absentes : tout y
# est detruit, et l'aire sous la courbe n'y mesure rien.
# ==============================================================================

source("commun.R")
source("noms_zones.R")

d <- lire_resultat("exp82_nepal.csv")
d <- d[d$auc != "" & !is.na(d$auc), ]
# Le greffon resume un objet par la MOYENNE du T-stat : on s'y tient.
d <- subset(d, agregation == "moyenne")
d$auc <- as.numeric(d$auc)

# Un libelle lisible : le nom de lieu pour les emprises Copernicus, le nom de la
# couche pour les ponts de HOT, qui couvrent plusieurs emprises a la fois.
d$libelle <- ifelse(d$emprise == "ensemble",
                    sub("ponts HOT, ", "ponts — ", d$objet),
                    paste0(nommer(d$emprise), " — ", d$objet))

# Du plus faible au plus fort, sur la serie complete.
ref <- d[d$configuration == "série complète", c("libelle", "auc")]
ordre <- ref$libelle[order(ref$auc)]
d$libelle <- factor(d$libelle, levels = ordre)

ecart <- merge(
  subset(d, configuration == "série complète", c("libelle", "auc")),
  subset(d, configuration == "une seule image", c("libelle", "auc")),
  by = "libelle", suffixes = c("_serie", "_une"))
ecart$texte <- fr(ecart$auc_une - ecart$auc_serie, 3)

g <- ggplot(d, aes(x = auc, y = libelle)) +
  geom_vline(xintercept = 0.5, colour = SOURD, linewidth = 0.6,
             linetype = "22") +
  geom_line(aes(group = libelle), colour = SOURD, linewidth = 0.6,
            alpha = 0.7) +
  geom_point(aes(colour = configuration), size = 3.6) +
  geom_text(data = ecart, aes(x = pmax(auc_serie, auc_une), y = libelle,
                              label = texte),
            hjust = -0.3, size = 3, colour = ENCRE_2, inherit.aes = FALSE) +
  scale_colour_manual(values = c("série complète" = BLEU,
                                 "une seule image" = ROUGE), name = NULL) +
  scale_x_continuous(labels = function(v) fr(v, 2, signe = FALSE),
                     expand = expansion(mult = c(0.06, 0.18))) +
  labs(title = "AUC du T-stat sur les routes et les ponts du Népal",
       subtitle = paste("La série complète couvre deux mois ; l'image unique",
                        "est celle de J+2,52.\nLe chiffre à droite est ce que",
                        "coûte l'image unique."),
       x = "AUC", y = NULL,
       caption = paste(
         "Lave torrentielle des 26–27 août 2026, Rasuwa et Nuwakot,",
         "activation Copernicus EMSR927.",
         "\nLes négatifs sont déclarés : « No visible damage » pour les routes",
         "chez Copernicus, « Standing » pour les ponts chez HOT.",
         "\nLe trait vertical marque 0,50. Calcul en variance regroupée,",
         "orbites combinées par maximum.",
         "\nSource : calculs de l'auteur, exp82.")) +
  theme_etude() +
  theme(legend.position = "top")

ggsave("fig_exp82_nepal_infrastructure.png", g, width = 10, height = 5.2,
       dpi = 200, bg = FOND)
cat("écrit : fig_exp82_nepal_infrastructure.png\n")
