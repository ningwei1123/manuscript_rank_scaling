# Data documentation

Two kinds of data are distributed here.

## 1. `data/figure_data/` — the numbers behind each figure

One plain-text file per figure panel. Tab-separated, with a header line, preceded by one
or more `#` comment lines that state what the numbers are and over what window they were
computed. These files are self-contained: Figure 1c, Figure 2 and the supplementary
spectra can be replotted from them alone.

`_index.json` lists the files with their row counts.

## 2. `data/artifacts/` — the JSON artifacts the figure data are derived from

These are the intermediate results written by the experiment scripts. They are included
so that every number in the manuscript can be traced without rerunning the experiments,
which together take several hours.

| Artifact | Written by | Provides |
|---|---|---|
| `rank_law_fit.json` | Kuramoto-Sivashinsky rank-law fit | the canonical log-form and power-law fits to the measured rank-accuracy curve, and the deviation from the predicted coefficient |
| `ks_slope_window_scan.json` | window scan | the slope as a function of the fitting window (10 to 30 cut-offs), which is why the paper quotes a range rather than a single number |
| `width_law_v6_summary.json` | `l96_width_v6.py`, `ks_width_v6_fixed.py` | all width scans: Lorenz-96 and Kuramoto-Sivashinsky at two horizons, with reference baselines |
| `real_l96_width_v6.json` | `real_l96_width.py` | the raw per-seed Lorenz-96 width sweep |
| `estimator_validation.json` | `estimator_validation.py` | fitted parameters and rank predictions against snapshot count |
| `z1_exponent_recomputed.json`, `c7_controlled_6seeds.json`, `c7_exact_reference.json` | controlled-operator construction | predicted and measured error-width exponents, with the exact truncation reference |
| `v16_theory_classes.json` | `v16_theory2.py` | closed form against direct tail sum for all three spectral families |
| `v17_blind_test_v2.json` | `v17_blind2.py` | the eighteen-system blind classification, with thresholds, per-system diagnostics and the two disagreements |
| `v17_saturation_scaling.json` | `v17_scaling.py` | effective dimension against state size, Kaplan-Yorke dimension and forcing |
| `v18_verification_real_data.json` | `v18_verify2.py` | the pre-registered prediction and its verification on the sea-surface fields, including the noise floor of the observational covariance spectra and the smallest resolvable accuracy |
| `v21_rankcap_final.json` | `v21_rankcap3.py` | the four-method test of whether a third spectral class is needed |
| `v24_condition.json`, `v24_partial.json` | `v24_condition.py` | invariance defect, condition number and predictive skill for a family of dictionaries, and their partial correlations |
| `ks_spectrum.npz`, `l96_spectrum.npz` | prepared for this repository | the singular values of the two covariance spectra, so the figure data can be regenerated without rerunning the simulations |

### A note on window dependence

Several quantities in this work are reported as ranges rather than as single fitted
values, because they depend on the fitting window. `ks_slope_window_scan.json` is the
clearest case: over cut-offs from 10 to 30 the slope of the Kuramoto-Sivashinsky
rank-accuracy curve moves from 2.71 to 1.88. The manuscript quotes the range. If you
recompute the curve from the stored spectrum you will obtain a different single value
unless you adopt the same window, and that sensitivity is a result of the paper rather
than a defect of the data.

### Naming

The artifact filenames retain the internal version tags under which they were produced
(`v16`, `v17`, `v18`, `v19`, `v21`, `v24`). They refer to stages of the analysis, not to
the manuscript version. The manuscript is version v3.

## 3. Not distributed here

The two sea-surface temperature fields are public but large (about 700 MB uncompressed).
`code/experiments/download_real_data.py` retrieves them. The derived quantities needed to
reproduce every figure are in `data/figure_data/` and `data/artifacts/`.
