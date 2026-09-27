# ==============================================================================
# LE PANNEAU DE COURBE DU CAS NEPALAIS, POUR LE MONTAGE
# ==============================================================================
#
# La figure 2.6 du memoire est un MONTAGE : des vignettes optiques encadrent une
# courbe. Ce programme produit la courbe seule, sans titre ni legende — ceux-ci
# sont poses au montage, comme sur les deux rangees existantes.
#
# Il reprend exactement les conventions de ces rangees : bande verte pour la
# moyenne anterieure plus ou moins un ecart-type, trait rouge pour la moyenne
# posterieure, trait vertical pour l'evenement, et la mention des effectifs en
# bas a gauche.
# ==============================================================================

source("commun.R")

VERT_BANDE <- "#cfe3cb"
VERT_TRAIT <- "#4a7a44"
ROUGE_POST <- "#c0392b"
BLEU_SERIE <- "#2b4a7a"

d <- lire_resultat("exp83_serie_vv_bidur.csv")
d$jours <- as.numeric(d$jours)
d$vv_db <- as.numeric(d$vv_db)

avant <- subset(d, periode == "avant")
apres <- subset(d, periode == "après")
m_av <- mean(avant$vv_db); s_av <- sd(avant$vv_db); m_ap <- mean(apres$vv_db)


# L'acquisition radar la plus proche de l'image optique d'avant, pour que le
# lecteur sache a quelle date correspond la vignette.
DATE_OPTIQUE <- as.Date("2026-02-05")
d$date_j <- as.Date(d$date)
i_opt <- which.min(abs(as.numeric(d$date_j - DATE_OPTIQUE)))
optique <- d[i_opt, ]

bande <- data.frame(xmin = min(d$jours), xmax = max(d$jours),
                    ymin = m_av - s_av, ymax = m_av + s_av)

g <- ggplot(d, aes(x = jours, y = vv_db)) +
  geom_rect(data = bande, inherit.aes = FALSE,
            aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
            fill = VERT_BANDE, alpha = 0.8) +
  geom_hline(yintercept = m_av, colour = VERT_TRAIT, linewidth = 0.7) +
  geom_segment(x = 0, xend = max(d$jours), y = m_ap, yend = m_ap,
               colour = ROUGE_POST, linewidth = 0.9) +
  geom_vline(xintercept = 0, colour = ENCRE, linewidth = 0.7) +
  geom_line(colour = BLEU_SERIE, linewidth = 0.6) +
  geom_point(colour = BLEU_SERIE, size = 1.9) +
  geom_point(data = optique, colour = "#1f6fb4", shape = 21, size = 4.6,
             stroke = 1.4, fill = NA) +
  annotate("text", x = optique$jours, y = optique$vv_db, hjust = -0.18,
           vjust = 1.7, size = 2.9, colour = "#1f6fb4",
           label = "image optique d'avant") +

  annotate("text", x = 0, y = max(d$vv_db), hjust = 1.06, vjust = 0.2,
           label = "événement", size = 3.4, colour = ENCRE) +
  annotate("text", x = min(d$jours), y = min(d$vv_db), hjust = 0, vjust = 0,
           label = sprintf("%d avant · %d après", nrow(avant), nrow(apres)),
           size = 3.2, colour = ENCRE_2) +
  annotate("text", x = min(d$jours), y = max(d$vv_db), hjust = 0, vjust = 1.4,
           label = sprintf("moyenne avant %s dB · après %s dB",
                           fr(m_av, 1), fr(m_ap, 1)),
           size = 3.2, colour = ENCRE_2) +
  scale_x_continuous(expand = expansion(mult = 0.02)) +
  scale_y_continuous(labels = function(v) fr(v, 0),
                     expand = expansion(mult = 0.10)) +
  labs(x = NULL, y = "dB") +
  theme_etude() +
  theme(axis.text.x = element_blank(),
        axis.ticks.x = element_blank(),
        panel.grid = element_blank(),
        axis.title.y = element_text(size = 9, angle = 0, vjust = 1,
                                    hjust = 1))

ggsave("panneau_nepal_courbe.png", g, width = 7.6, height = 2.7, dpi = 220,
       bg = FOND)
cat("écrit : panneau_nepal_courbe.png\n")
