# ==============================================================================
# LES FIGURES DE L'EVALUATION COMMUNE (exp75)
# ==============================================================================
#
# Ce programme produit quatre figures a partir d'un seul fichier de donnees,
# `exp75_detail.csv`, qui contient TOUTES les cartes jamaicaines evaluees de la
# meme facon : couche Open Buildings, appariement strict, filtre de prevalence
# borne des deux cotes.
#
# Il remplace les figures fig_exp70*.R, tracees a partir d'une evaluation qui
# melangeait deux couches baties et une regle d'appariement plus lache. Elles
# sont periMEES et ne doivent plus servir.
#
# LES QUATRE FIGURES
#   1. l'ecart de chaque reglage a la configuration de reference
#   2. l'AUC selon la duree de la fenetre posterieure, toutes orbites
#   3. la meme, sur une seule trace orbitale
#   4. l'AUC selon la duree de la periode de reference
#
# LES TITRES disent ce que la figure MONTRE, pas ce qu'il faut en conclure. Un
# titre qui enonce la conclusion la fait passer pour acquise avant que le
# lecteur ait regarde, et il vieillit mal.
# ==============================================================================

source("commun.R")
source("noms_zones.R")

detail <- lire_resultat("exp75_detail.csv")
detail$zone_lisible <- nommer(detail$zone)

PREV_MIN <- 5
PREV_MAX <- 95

# ------------------------------------------------------------------------------
# Un utilitaire : les ecarts apparies a une famille de reference.
# ------------------------------------------------------------------------------
ecarts_a <- function(familles, reference) {
  sous <- subset(detail, famille %in% familles)
  ref <- subset(sous, famille == reference,
                select = c("zone", "zone_lisible", "auc", "prevalence"))
  names(ref)[names(ref) == "auc"] <- "auc_ref"
  e <- merge(subset(sous, famille != reference), ref,
             by = c("zone", "zone_lisible"))
  e$delta <- e$auc - e$auc_ref
  e$fiable <- e$prevalence.y >= PREV_MIN & e$prevalence.y <= PREV_MAX
  e
}

nuage <- function(e, ordre, noms, titre, soustitre, legende) {
  e <- subset(e, famille %in% ordre)
  e$etiquette <- factor(noms[e$famille], levels = rev(noms[ordre]))
  e$signe <- ifelse(e$delta >= 0, "au-dessus de la référence",
                    "au-dessous de la référence")
  moy <- aggregate(delta ~ etiquette, data = subset(e, fiable), FUN = mean)

  ggplot(e, aes(x = delta, y = etiquette)) +
    geom_vline(xintercept = 0, colour = SOURD, linewidth = 0.6) +
    geom_point(aes(colour = signe, shape = fiable), size = 2.8, alpha = 0.85,
               position = position_jitter(height = 0.12, width = 0, seed = 1)) +
    geom_point(data = moy, shape = 23, size = 4.2, stroke = 1.1,
               fill = FOND, colour = ENCRE) +
    geom_text(data = moy, aes(label = fr(delta, 4)), vjust = -1.4,
              size = 3.2, colour = ENCRE) +
    scale_colour_manual(values = c("au-dessus de la référence" = BLEU,
                                   "au-dessous de la référence" = ROUGE)) +
    scale_shape_manual(values = c(`TRUE` = 16, `FALSE` = 1),
                       labels = c(`TRUE` = "prévalence entre 5 et 95 %",
                                  `FALSE` = "hors de cet intervalle"),
                       name = NULL) +
    scale_x_continuous(labels = function(v) fr(v, 2)) +
    labs(title = titre, subtitle = soustitre, y = NULL,
         x = "écart d'AUC par rapport à la référence", caption = legende) +
    theme_etude() +
    # Les deux legendes empilees : sur un seul rang elles depassent la largeur
    # de l'image et la derniere etiquette se trouve tronquee.
    theme(legend.box = "vertical", legend.box.just = "left",
          legend.margin = margin(b = 0)) +
    guides(colour = guide_legend(order = 1), shape = guide_legend(order = 2))
}

COMMUN <- paste(
  "Emprises de Jamaïque, cyclone Melissa, vérités Copernicus EMS et UNOSAT,",
  "empreintes Open Buildings.")

# Legende des nuages de points : losange = moyenne, cercle vide = zone ecartee.
LEG <- paste(COMMUN,
  "\nLe losange est la moyenne des comparaisons dont la prévalence reste entre",
  "5 et 95 % ; les cercles vides sont hors de cet intervalle.",
  "\nSource : calculs de l'auteur, exp75.")

# Legende des courbes : pas de losange ni de cercle, et les zones hors de
# l'intervalle de prevalence sont retirees et non marquees.
LEG_C <- paste(COMMUN,
  "\nSeules les emprises dont la prévalence reste entre 5 et 95 % sont tracées :",
  "ailleurs l'AUC ne mesure rien.",
  "\nSource : calculs de l'auteur, exp75.")

# ── 1. les configurations ─────────────────────────────────────────────────
ordre1 <- c("welch", "mahalanobis", "lissage_20m", "orbites_stouffer",
            "sans_masque", "ztest_1img", "poole_1img", "mahalanobis_1img")
noms1 <- c(welch = "test de Welch",
           mahalanobis = "distance de Mahalanobis",
           lissage_20m = "médian focal 20 m",
           orbites_stouffer = "combinaison de Stouffer",
           sans_masque = "masque de validité levé",
           ztest_1img = "score z, une seule image",
           poole_1img = "variance regroupée, une seule image",
           mahalanobis_1img = "Mahalanobis, une seule image")

p1 <- nuage(ecarts_a(c("reference", ordre1), "reference"), ordre1, noms1,
            "Écart d'AUC de chaque réglage par rapport à la référence",
            paste("Un seul réglage change à la fois. Référence : variance",
                  "regroupée, maximum entre orbites,\nmédian focal 10 m,",
                  "masque de validité actif, fenêtre postérieure de deux mois."),
            LEG)
ggsave("fig_exp75_configurations.png", p1, width = 10, height = 5.6,
       dpi = 200, bg = FOND)

# ── 2 et 3. les fenetres posterieures ─────────────────────────────────────
courbe <- function(familles, jours, titre, soustitre, legende, fichier,
                   axe_x) {
  sous <- subset(detail, famille %in% familles)
  sous$jour <- jours[sous$famille]
  sous <- subset(sous, prevalence >= PREV_MIN & prevalence <= PREV_MAX)
  moy <- aggregate(auc ~ jour, data = sous, FUN = mean)
  moy$etiquette <- fr(moy$auc, 3, signe = FALSE)
  paliers <- sort(unique(sous$jour))

  p <- ggplot(sous, aes(x = jour, y = auc)) +
    geom_line(aes(group = zone_lisible), colour = SOURD, linewidth = 0.5,
              alpha = 0.5) +
    geom_text(data = subset(sous, jour == max(paliers)),
              aes(label = zone_lisible), hjust = -0.05, size = 2.9,
              colour = ENCRE_2) +
    geom_line(data = moy, colour = BLEU, linewidth = 1.4) +
    geom_point(data = moy, colour = BLEU, size = 3) +
    geom_text(data = moy, aes(label = etiquette), vjust = -1.3, size = 3.2,
              colour = ENCRE) +
    scale_x_continuous(breaks = paliers,
                       labels = sub("\\.", ",", format(paliers, trim = TRUE)),
                       expand = expansion(mult = c(0.04, 0.28))) +
    scale_y_continuous(labels = function(v) fr(v, 2, signe = FALSE)) +
    labs(title = titre, subtitle = soustitre, x = axe_x, y = "AUC",
         caption = legende) +
    theme_etude() +
    theme(panel.grid.major.y = element_line(colour = NEUTRE, linewidth = 0.4))
  ggsave(fichier, p, width = 10, height = 5.2, dpi = 200, bg = FOND)
}

j_fen <- c(fenetre_1img = 2.5, fenetre_07j = 7, fenetre_14j = 14,
           fenetre_21j = 21, fenetre_30j = 30, fenetre_60j = 60)
courbe(names(j_fen), j_fen,
       "AUC selon la date de fin de la fenêtre postérieure",
       paste("Toutes les traces orbitales disponibles sont combinées.",
             "Chaque ligne fine est une emprise ;\nla ligne épaisse est leur",
             "moyenne. L'axe porte le nombre de jours après l'événement."),
       LEG_C, "fig_exp75_fenetre_toutes_orbites.png",
       "fin de la fenêtre, en jours après l'événement")

j_orb <- c(orb150_1img = 2.5, orb150_07j = 7, orb150_14j = 14,
           orb150_21j = 21, orb150_30j = 30, orb150_60j = 60)
courbe(names(j_orb), j_orb,
       "AUC selon la fenêtre postérieure, sur une seule trace orbitale",
       paste("Le calcul est restreint à la trace 150. Le nombre d'orbites est",
             "donc constant,\net seule la durée de la fenêtre varie."),
       LEG_C, "fig_exp75_fenetre_une_orbite.png",
       "fin de la fenêtre, en jours après l'événement")

j_pre <- c(pre_03m = 3, pre_06m = 6, pre_09m = 9, pre_12m = 12,
           pre_18m = 18, pre_24m = 24)
courbe(names(j_pre), j_pre,
       "AUC selon la durée de la période de référence",
       paste("Durée en mois de la série antérieure à l'événement, qui définit",
             "le comportement habituel\nde chaque pixel. Une seule image",
             "postérieure, sur une seule trace orbitale."),
       LEG_C, "fig_exp75_periode_reference.png",
       "durée de la période de référence, en mois")

cat("écrit : quatre figures fig_exp75_*.png\n")

# ── 5. l'image unique, zone par zone ──────────────────────────────────────
#
# Cette figure remplace celles du memoire qui opposaient le score a une image a
# un test de WELCH. Le greffon ne calcule pas Welch : il calcule une variance
# regroupee. Les deux termes compares ici sont donc tous deux en variance
# regroupee, et la figure reflete enfin ce que l'outil fait reellement.
#
# A gauche de zero, l'image unique classe moins bien que la serie complete ; a
# droite, elle classe mieux.

paire <- ecarts_a(c("reference", "poole_1img"), "reference")
paire <- subset(paire, famille == "poole_1img" & fiable)
paire <- paire[order(paire$delta), ]
paire$zone_lisible <- factor(paire$zone_lisible, levels = paire$zone_lisible)
paire$signe <- ifelse(paire$delta >= 0, "l'image unique classe mieux",
                      "l'image unique classe moins bien")

p5 <- ggplot(paire, aes(x = delta, y = zone_lisible, colour = signe)) +
  geom_vline(xintercept = 0, colour = SOURD, linewidth = 0.6) +
  geom_segment(aes(x = 0, xend = delta, yend = zone_lisible), linewidth = 1.1) +
  geom_point(size = 3.6) +
  geom_text(aes(label = fr(delta, 4)), hjust = ifelse(paire$delta >= 0, -0.25, 1.25),
            size = 3.2, colour = ENCRE) +
  scale_colour_manual(values = c("l'image unique classe mieux" = BLEU,
                                 "l'image unique classe moins bien" = ROUGE)) +
  scale_x_continuous(labels = function(v) fr(v, 2),
                     expand = expansion(mult = 0.22)) +
  labs(title = "Écart d'AUC entre une seule image et la série complète",
       subtitle = paste("Les deux termes sont calculés à variance regroupée,",
                        "comme dans l'outil.\nLa série complète couvre deux",
                        "mois après l'événement."),
       x = "écart d'AUC de l'image unique", y = NULL, caption = LEG_C) +
  theme_etude() +
  theme(legend.position = "top")

ggsave("fig_exp75_image_unique.png", p5, width = 10, height = 4.6,
       dpi = 200, bg = FOND)
cat("écrit : fig_exp75_image_unique.png\n")
