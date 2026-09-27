# Known limitations

## The statistic is not calibrated

The paper writes the statistic with separate pre- and post-event variances,
but the code released with it computes a pooled-variance Student t-test, and
so does the implementation evaluated here. A later version of the reference
code, released on 25 June 2026, makes Welch the default and keeps the pooled
form as an option that its own comment calls the original; the two were compared on
two disasters and neither dominates. Rankings are usable; confidence levels are
not, because the statistic has never been calibrated against a damage
probability.

## AUC compares rankings, not populations

An AUC of 0.74 on one footprint and 0.74 on another does not mean the two
populations were equally difficult. This is precisely why the common-footprint
evaluation exists.

## The strict intersection is a control, not a validation

Requiring every product to provide a usable value reduces the sample to
5 489 buildings in five communes. That is a useful consistency check and
nothing more: the sample may not represent the activation.

## Fusion gains are measured on rankings only

No precision or recall at an explicit threshold has been computed. Statements
about "fewer false alarms" therefore cannot be made from these results.

## Roads are not detected

The method produces a change signal over building footprints. It does not
identify cut or impassable roads.
