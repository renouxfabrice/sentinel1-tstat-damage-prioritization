# Prioritising which buildings to check after a disaster, with Sentinel-1

**Language / Langue :** 🇬🇧 English · 🇫🇷 [Français](README.md)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24601724.svg)](https://doi.org/10.5281/zenodo.24601724)

After a sudden disaster, the question is not only where the damage is. In the field, the real question is usually:

> **where should the checking start?**

Optical imagery shows buildings, roads and debris in detail. But it sometimes arrives late, or is hidden by clouds. Sentinel-1 is a radar: it acquires by day and by night, and through cloud.

Radar does not show damage directly. It measures a change in the signal returned by the ground, and that change depends on the viewing geometry, on what is being observed and on the kind of change.

This repository accompanies a study on using Sentinel-1 to **rank the buildings or areas to check first** after a disaster.

## What the study does

- it reuses a pixel-wise change detection method (t-test);
- it brings the scores down to building level;
- it compares that ranking with other products published after the same disasters;
- it uses the same building footprint layer for every product, so that the comparison is fair;
- it reproduces several methods based on interferometric coherence;
- it tests combinations (fusions) of scores and of ranks;
- it also applies the method to roads and bridges;
- it describes the limits of the reference data and of the areas studied.

The building results cover **two cases**: an earthquake in Venezuela and a tropical cyclone in Jamaica. A **third case**, a glacial lake outburst debris flow in Nepal, is used to test the method on roads and bridges, and to see whether the conclusions hold for a different kind of hazard.

Combining our t-test with the OSU coherence product (weighted mean of ranks) raises the mean AUC from **0.740** to **0.764**. This gain is measured on the building footprints and the references described in the study. It does not prove that the method works everywhere, nor that it would give the same result on another disaster.

The result is therefore a **tool for prioritising checks**, not an automatic damage diagnosis.

## Reading the study

- 📄 [Full text](docs/partie_2/partie_2.md) (in French): ten sections, 20 figures, four tables, a discussion of the limits of the references, and a dictionary of the methods compared.
- 📚 [Bibliography](docs/references.md): works cited, identifiers (DOI) and the source RIS file.

The method sections give the formulas, the parameters, the pre-processing, the move to building level and the evaluation rules.

## What is in the repository

| Folder or file | Contents |
|---|---|
| [`docs/partie_2/figures/`](docs/partie_2/figures/) | The 20 figures of the study |
| [`tables/`](tables/) | The 15 summary tables cited in the study (CSV) |
| [`data/results/`](data/results/) | 76 result tables: AUC, thresholds, aggregations and fusions |
| [`data/raw/produits_tiers/`](data/raw/produits_tiers/) | Third-party products and surveys used, with their attributions |
| [`data/inventaire_donnees.csv`](data/inventaire_donnees.csv) | Inventory of the 2,074 files used (about 134 GB) |
| [`src/`](src/) | The 61 programs that compute the result tables |
| [`src/reevaluation/`](src/reevaluation/) | The programs of the 1 October 2026 recomputation (experiments 73 to 86) |
| [`src/visualization/`](src/visualization/) | The R programs that produce the figures (8 draw a figure, 2 hold shared functions) |
| [`notebooks/`](notebooks/) | 6 notebooks that replay the figures quoted in the study |
| [`docs/datasets/data_availability.md`](docs/datasets/data_availability.md) | Data provided, data not provided, and how to obtain it |

## Redoing the calculations

The figures that carry numbers are produced by R programs from the result tables. If a table changes, rerunning the program updates the figure. The other figures — imagery plates, diagrams, maps — are described in their captions.

Figures 5, 6 and 7 were recomputed on 1 October 2026. The earlier versions used Welch's test and an evaluation against OpenStreetMap. The current versions use the settings of the tool and the evaluation method described in the study.

Each notebook ends with automatic checks: it verifies that the tables really do give the numbers published in the study. If a value no longer matches, the notebook stops with an error.

## Data

The Sentinel-1 acquisitions are openly available, but they are not copied into this repository. The data inventory gives, for every file, its origin, its role and how to find it again.

The result tables, on the other hand, are in the repository: they can be read without downloading the radar imagery.

Some third-party data carries its own access and reuse conditions. Licences and attributions are listed in [`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

## About the t-test

The t-test code used in the tool is not provided here: it derives from code published without a licence permitting redistribution.

The study nevertheless gives:

- the formula used;
- the pre-event and post-event periods;
- the difference between the pooled-variance test and Welch's test;
- the processing parameters;
- the differences between the formula in the reference paper and the code its author released.

The maps and the results use the pooled-variance test, which the reference repository itself calls **Pooled t-test (original)**. A later version of that repository offers Welch by default; it was not used here.

## Limits

A high score flags a change in the radar signal worth a closer look. It does not mean the building is destroyed.

The test measures a change in the returned signal, not damage. It can miss total destruction when one rough surface is replaced by another rough surface — a vegetated track buried under sediment, for instance. Figure 17 shows such a case.

The result also depends on:

- the date and the quality of the images;
- the viewing geometry;
- the season and the moisture;
- the resolution and the building footprint layer;
- the reference used for the evaluation;
- the number of buildings and areas available.

The same holds for roads and bridges: the scores help spot stretches worth checking, but they are not enough on their own to say whether a road is passable.

## How this work was done

I designed this study, chose the cases, the data and the references, and checked the results. To write and fix the code, run the calculations and draft the documentation, I was assisted by an artificial intelligence tool, Claude (Anthropic). I reviewed the code and the text it produced, and the published figures are checked by the notebooks described above. Any remaining errors are mine: please do report them.

The detail — what the tool did, what it did not do, and how that is verifiable — is in [`AI_USE.en.md`](AI_USE.en.md).

## Licence

The code is released under the [MIT](LICENSE) licence.

Third-party data keeps its own licences. Conditions and attributions are in [`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

This version is archived on Zenodo and citable by its persistent
identifier: **[10.5281/zenodo.24601724](https://doi.org/10.5281/zenodo.24601724)**. The full citation format is in
[`CITATION.cff`](CITATION.cff). To point not at this version but at the
latest one, whichever it is, the identifier is
[10.5281/zenodo.24601723](https://doi.org/10.5281/zenodo.24601723).

## Contact

**Fabrice Renoux** ([@renouxfabrice](https://github.com/renouxfabrice))

To report an error, suggest an improvement or ask about the data, the simplest way is to open [an issue](https://github.com/renouxfabrice/sentinel1-tstat-damage-prioritization/issues/new): the answer then stays useful to the next reader.

For a private exchange, use the contact form on the GitHub profile.
