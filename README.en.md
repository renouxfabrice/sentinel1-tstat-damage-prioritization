# Evaluating and improving Sentinel-1 damage prioritisation for buildings

**Language / Langue :** 🇬🇧 English · 🇫🇷 [Français](README.md)

After a sudden-onset disaster, the operational question is not only "where is
there damage?", but also:

> **where should we check first?**

Optical imagery often allows a detailed interpretation of buildings, roads and
debris. It may, however, be unavailable, acquired too late, or masked by cloud.
Sentinel-1 provides a radar signal independent of daylight and cloud cover.

That signal does not, however, show damage directly. It measures a change in
backscatter, whose interpretation depends among other things on radar geometry,
on the structure observed and on the nature of the change.

This repository accompanies a study on the use of Sentinel-1 to produce a
**ranking of the buildings or sectors to be checked** after a disaster.

## What the study contains

The study:

- reimplements an approach based on a per-pixel change statistic;
- then aggregates the scores at building level;
- compares that ranking with other products available after a disaster;
- harmonises the building footprints used, to make the comparisons fairer;
- reproduces several methods based on interferometric coherence;
- evaluates fusions of scores and of ranks;
- extends the measurement to roads and bridges;
- documents the limitations of the reference data and of the areas studied.

The building results cover **two case studies**, an earthquake in Venezuela and
a tropical cyclone in Jamaica. A **third campaign**, a glacial lake outburst
debris flow in Nepal, serves to test the method on roads and bridges, and to
check whether its conclusions hold on a hazard of a different nature.

In the T-stat × OSU configuration, targeted fusion raises the mean AUC from
**0.740** for the T-stat alone to **0.764**. This improvement is measured on the
building footprints and reference data described in the study. It constitutes
neither a general validation of damage detection nor a guarantee of
transferability to other disasters.

The result should therefore be read as a **prioritisation tool**, and not as an
automatic damage diagnosis.

## Reading the document

- 📄 [Full text](docs/partie_2/partie_2.en.md)
  Ten sections, 17 figures, four tables, a discussion of the limitations of the
  reference data used, and a dictionary of the methods compared.

- 📚 [Bibliography](docs/references.md)
  References cited, persistent identifiers and the source RIS file.

The sections devoted to the method present the formulas, the parameters, the
pre-processing choices, the aggregation at building level and the evaluation
rules.

## Repository layout

| Folder or file | Contents |
|---|---|
| [`docs/partie_2/figures/`](docs/partie_2/figures/) | The 17 figures of the document |
| [`tables/`](tables/) | The fourteen summary tables cited in the document, in CSV |
| [`data/results/`](data/results/) | 74 result tables: AUC, thresholds, aggregations and fusions |
| [`data/raw/produits_tiers/`](data/raw/produits_tiers/) | Third-party products and surveys used as input, with their attributions |
| [`data/inventaire_donnees.csv`](data/inventaire_donnees.csv) | Inventory of the 2,074 files used, about 134 GB |
| [`src/`](src/) | The 47 programs that compute the result tables |
| [`src/visualization/`](src/visualization/) | The nine R programs that produce the figures |
| [`notebooks/`](notebooks/) | Six notebooks that replay the figures cited |
| [`docs/datasets/data_availability.md`](docs/datasets/data_availability.md) | Data redistributed, data not redistributed, and access procedures |

## Reproducing the results

The figures are produced by R programs from the result tables. They are
therefore no longer drawn by hand: a validated change to the tables can be
propagated to the figures without graphical retouching.

Figures 5, 6 and 7 were recomputed on 1 October 2026. The earlier versions used
Welch's test and an evaluation based on OpenStreetMap, whereas the results
retained in the study use the tool's configuration and the evaluation convention
described in the document.

The six notebooks end with assertions. They verify that the tables carrying the
results do match the figures published in the document. If a table is modified
or no longer holds the expected value, the notebook fails at the final check.

## Data

The Sentinel-1 acquisitions used in the computations are open, but they are not
redistributed in this repository. The data inventory gives their origin, their
role and the information needed to retrieve the same inputs.

The tables containing the published results are, by contrast, included in the
repository. They can be consulted without downloading the radar acquisitions.

Some third-party data remain subject to their own access and reuse conditions.
The licences and attributions to be preserved are listed in
[`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

## About the t-test

The operational implementation of the per-pixel t-test is not redistributed in
this repository. It derives from code published without a licence permitting its
redistribution.

The document nonetheless provides:

- the mathematical formulation used;
- the description of the before and after periods;
- the distinction between the pooled-variance form and Welch's form;
- the processing parameters;
- what separates the formula written in the reference article from the code its
  author released with it.

The maps and results presented here use the pooled-variance form, the one the
reference repository itself calls **Pooled t-test (original)**. A later version
of that repository offers Welch by default; that setting was not adopted for the
computations presented.

## Limits of interpretation

A high score indicates a signal anomaly to be examined. It does not
automatically mean that a building is destroyed.

The test measures a **change in surface roughness**, not damage. It is blind
when destruction replaces one rough medium with another rough medium, even when
the damage is total — figure 17 shows one such case.

Interpretation also depends on:

- the date and quality of the acquisitions;
- the observation geometry;
- the season and the moisture of the scene;
- the resolution and the building footprint layer;
- the reference used for the evaluation;
- the number of buildings and areas available.

The results on roads and bridges are read the same way: they can help flag
segments to be checked, but they do not on their own support any conclusion
about whether a route is passable.

## Licence

The code and texts of this repository are distributed under the
[MIT](LICENSE) licence.

Third-party data keep their own licences. The conditions of use and the required
attributions are given in
[`tables/datasets_sources_licences.csv`](tables/datasets_sources_licences.csv).

To cite this work, see [`CITATION.cff`](CITATION.cff).

The address of a GitHub repository is not, on its own, a stable bibliographic
reference. Archiving this version in a service providing a persistent identifier
remains to be done.

## Contact and contributions

**Fabrice Renoux** — [@renouxfabrice](https://github.com/renouxfabrice)

To report an error, propose an improvement or ask for details about the
intermediate data, the best route is to open
[an issue](https://github.com/renouxfabrice/sentinel1-tstat-damage-prioritization/issues/new).
Exchanges then remain accessible to later readers and contributors.

For a private exchange, the contact form on the GitHub profile will do.
