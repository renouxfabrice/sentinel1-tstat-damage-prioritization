# ==============================================================================
# LES NOMS DES ZONES
# ==============================================================================
#
# Les fichiers de resultats designent les emprises par leur code technique —
# EMS_AOI16, catia_la_mar. Ces codes ne disent rien a un lecteur : ils servent de
# cle de jointure, pas d'etiquette.
#
# Les figures portent donc le NOM DE LIEU suivi de l'identifiant d'AOI entre
# parentheses : « Big Woods (AOI16) ». Le nom situe l'endroit, l'identifiant
# permet de retrouver l'emprise dans les activations Copernicus.
#
# Les noms viennent du champ `locality` des fichiers d'emprise. Les emprises
# UNOSAT portent deja un nom de lieu et n'ont pas d'identifiant d'AOI.
#
# DEUX PARTICULARITES, qui ne sont pas des erreurs :
#   - Cuba releve de la MEME activation que la Jamaique, EMSR847 : le cyclone
#     Melissa a touche les deux iles, et Jiguani y porte l'AOI25 ;
#   - trois emprises venezueliennes partagent l'AOI12, l'activation EMSR884 les
#     ayant decoupees a l'interieur d'une meme zone d'interet.
#
# POUR AJOUTER UNE CAMPAGNE : une ligne par emprise, dans le meme format. Rien
# d'autre a modifier, les figures lisent cette table.
# ==============================================================================

NOMS_ZONES <- c(
  # ── Jamaique — cyclone Melissa, activation EMSR847 ──────────────────────
  "EMS_AOI16"                = "Big Woods (AOI16)",
  "EMS_AOI26"                = "Arlington (AOI26)",
  "EMS_AOI29"                = "Bartons (AOI29)",
  "EMS_AOI30"                = "Darliston (AOI30)",
  "EMS_AOI36"                = "Orange Bay (AOI36)",
  "EMS_AOI38"                = "Belmont (AOI38)",
  "EMS_AOI39"                = "White House (AOI39)",
  "UNOSAT_WhiteHouse"        = "White House (UNOSAT)",
  "UNOSAT_BlackRiver"        = "Black River (UNOSAT)",
  "UNOSAT_BlackRiverVillage" = "Black River Village (UNOSAT)",

  # ── Cuba — meme cyclone, meme activation EMSR847 ────────────────────────
  "CUBA_AOI25"               = "Jiguaní (AOI25)",

  # ── Colombie — activation EMSR916 ───────────────────────────────────────
  "COL_AOI01"                = "Nord de Cali (AOI01)",
  "COL_AOI02"                = "Pereira (AOI02)",
  "COL_AOI03"                = "Centre de Cali (AOI03)",
  "COL_AOI04"                = "Centre de Quibdó (AOI04)",
  "COL_AOI05"                = "Istmina (AOI05)",
  "COL_AOI06"                = "Buenaventura (AOI06)",

  # ── Venezuela — seisme du 24 juin 2026, activation EMSR884 ──────────────
  "Caracas"                  = "Caracas (AOI02)",
  "Moron"                    = "Morón (AOI06)",
  "San_Felipe"               = "San Felipe (AOI08)",
  "la_guaira"                = "La Guaira (AOI12)",
  "catia_la_mar"             = "Catia La Mar (AOI12)",
  "caraballeda"              = "Caraballeda (AOI12)",

  # Les memes emprises, telles que les experiences 77 et 78 les nomment.
  "VENEZ_la_guaira"          = "La Guaira (AOI12)",
  "VENEZ_catia_la_mar"       = "Catia La Mar (AOI12)",
  "VENEZ_caraballeda"        = "Caraballeda (AOI12)",

  # ── Nepal — lave torrentielle du 26 aout 2026, activation EMSR927 ───────
  "NEPAL_aoi01"              = "Syapru Besi (AOI01)",
  "NEPAL_aoi02"              = "Timure (AOI02)",
  "NEPAL_aoi03"              = "Bidur (AOI03)",
  "NEPAL_aoi05"              = "Phosretar (AOI05)"
)

# Traduire un vecteur de codes. Un code inconnu est rendu tel quel plutot que
# remplace par une valeur manquante : mieux vaut une etiquette laide qu'une
# etiquette absente, qui ferait disparaitre la zone de la figure.
nommer <- function(codes) {
  out <- NOMS_ZONES[as.character(codes)]
  out[is.na(out)] <- as.character(codes)[is.na(out)]
  unname(out)
}

# Le pays, deduit du code. Sert aux figures qui distinguent les campagnes.
pays_de <- function(codes) {
  codes <- as.character(codes)
  ifelse(grepl("^CUBA_", codes), "Cuba",
  ifelse(grepl("^NEPAL_", codes), "Népal",
  ifelse(grepl("^COL_", codes), "Colombie",
  ifelse(grepl("^EMS_|^UNOSAT_", codes), "Jamaïque", "Venezuela"))))
}
