# How this work was done

**Language / Langue :** 🇬🇧 English · 🇫🇷 [Français](AI_USE.md)

This document sets out the part an artificial intelligence tool played in
producing this repository. It exists because a reader who reuses a figure is
entitled to know how it was obtained, and because the answer — "from code and
tables you can read" — is more useful than silence.

## What I did

I designed the study and its questions, and chose the disasters, the products
compared, the building footprint layers and the reference truths. I settled the
evaluation rules — AUC per municipality, common footprint, strict matching,
prevalence bounds — and the computation settings. I reviewed the results, set
aside those that did not hold, and decided what is published.

The interpretations, the caveats and the limits set out in the study are mine.

## What the tool did

I was assisted by **Claude** (Anthropic) to:

- write and fix the Python and R programs in this repository;
- carry out the calculations, that is run the experiments, read the outputs and
  spot inconsistencies between them;
- draft and lay out the documentation, including this repository and its
  README files.

The tool did not choose the case studies, the references, or the conclusions.

## Why that excuses nothing, and how to check

A figure is no safer for having been typed by a human, and no less safe for
having been computed by a program. What makes it verifiable is that it is tied
to a published table and a published program. That is the rule followed here:

- **the programs are in [`src/`](src/)**, in the state in which they were used,
  absolute paths aside;
- **the result tables are in [`data/results/`](data/results/)** and the summary
  tables in [`tables/`](tables/);
- **the six notebooks in [`notebooks/`](notebooks/)** replay every figure quoted
  in the study from those tables, and end with assertions: if a table no longer
  carries the published value, the notebook fails.

An error introduced by the tool and not caught by my review therefore remains my
error. If you find one, [open an
issue](https://github.com/renouxfabrice/sentinel1-tstat-damage-prioritization/issues/new):
the correction will serve the next reader.

## What is *not* AI in this study

To head off a common confusion: the method evaluated here — a pixel-wise t-test
on Sentinel-1 time series — **is not a machine learning model**. It is a
classical statistical test. Several of the products it is compared against do
rest on deep learning applied to optical imagery; this is stated product by
product in the dictionary of methods at the end of the study.
