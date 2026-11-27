# Comment ce travail a été fait

**Language / Langue :** 🇬🇧 [English](AI_USE.en.md) · 🇫🇷 Français

Ce document précise la part prise par un outil d'intelligence artificielle dans
la production de ce dépôt. Il est écrit parce qu'un lecteur qui reprend des
chiffres a le droit de savoir comment ils ont été obtenus, et parce que la
réponse — « par du code et des tables qu'on peut relire » — est plus utile
qu'un silence.

## Ce que j'ai fait

J'ai conçu l'étude et ses questions, choisi les catastrophes, les produits
comparés, les couches d'empreintes bâties et les vérités de référence. J'ai
arrêté les règles d'évaluation — AUC par commune, emprise commune, appariement
strict, bornes de prévalence — et les configurations de calcul. J'ai relu les
résultats, écarté ceux qui ne tenaient pas, et décidé de ce qui est publié.

Les interprétations, les réserves et les limites exposées dans l'étude sont les
miennes.

## Ce que l'outil a fait

Je me suis fait aider par **Claude** (Anthropic) pour :

- écrire et corriger les programmes Python et R de ce dépôt ;
- mener les calculs, c'est-à-dire lancer les expériences, lire les sorties et
  repérer les incohérences entre elles ;
- rédiger et mettre en forme la documentation, y compris ce dépôt et ses README.

L'outil n'a pas choisi les cas d'étude, les références, ni les conclusions.

## Pourquoi cela ne dispense de rien, et comment le vérifier

Un chiffre n'est pas plus sûr parce qu'un humain l'a tapé, ni moins sûr parce
qu'un programme l'a calculé. Ce qui le rend vérifiable, c'est qu'il soit
rattaché à une table et à un programme publiés. C'est la règle suivie ici :

- **les programmes sont dans [`src/`](src/)**, dans l'état où ils ont servi, les
  chemins absolus mis à part ;
- **les tables de résultats sont dans [`data/results/`](data/results/)** et les
  tables de synthèse dans [`tables/`](tables/) ;
- **les six carnets de [`notebooks/`](notebooks/)** rejouent chaque chiffre cité
  dans l'étude à partir de ces tables, et se terminent par des assertions : si
  une table ne porte plus la valeur publiée, le carnet échoue.

Une erreur introduite par l'outil et non rattrapée par ma relecture reste donc
une erreur de ma part. Si vous en trouvez une, [ouvrez une
*issue*](https://github.com/renouxfabrice/sentinel1-tstat-damage-prioritization/issues/new) :
la correction servira aux lecteurs suivants.

## Ce qui n'est pas de l'IA dans cette étude

Pour éviter une confusion fréquente : la méthode évaluée ici — le test t par
pixel sur séries temporelles Sentinel-1 — **n'est pas un modèle d'apprentissage
automatique**. C'est un test statistique classique. Plusieurs des produits
auxquels elle est comparée, eux, reposent sur de l'apprentissage profond
appliqué à l'imagerie optique ; c'est indiqué produit par produit dans le
dictionnaire des méthodes, à la fin de l'étude.
