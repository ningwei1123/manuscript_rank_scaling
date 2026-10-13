# A spectral diagnostic for rank-based scaling laws in data-driven models of chaotic systems

Code and data accompanying the manuscript submitted to the *Journal of Computational
Physics*.

## What the paper claims

Practitioners choose the size of a reduced-order or operator-learning model from the
decay of a data covariance or POD spectrum, but no criterion states when that choice is
sound. This repository contains the code that (i) derives a closed form for the required
rank under an exponential and an algebraic covariance spectrum, (ii) tests whether a
third spectral class reported in the literature is needed, (iii) classifies eighteen
synthetic systems from their covariance spectra, and (iv) applies the same criterion to
real observational sea-surface temperature fields, where it does not transfer.

Two features of the work are deliberate and are worth stating up front.

**The negative result is part of the contribution, not a failure to be hidden.** On real
observational fields the diagnostic does not transfer and the paper says so, then
identifies the domain of validity that this delimits.

**The 16-of-18 classification is a consistency check, not an independent prediction.**
Both the diagnostic and the measured class are functions of the same spectrum. The
independent test is the Kuramoto-Sivashinsky slope comparison, where prediction and
measurement differ by 19%, and the paper reports the discrepancy.

## Repository layout

```
manuscript_rank_scaling/
    README.md                     this file
    LICENSE                       MIT
    requirements.txt              Python dependencies
    data/
        figure_data/              one plain-text file per figure panel ("*.txt")
        artifacts/                the JSON artifacts that figure_data is derived from
    code/
        experiments/              scripts that produce the artifacts
        figures/                  scripts that produce the figures
        manuscript/               the manuscript generator and its validator
                                  (these live under code/, not at the top level)
    figures/                      the figures as they appear in the manuscript
```

The manuscript itself is not distributed here; it is under submission. `code/manuscript/`
contains the generator that builds it from the artifacts, so the text can be regenerated
from this repository, but the submitted document is not included.

Every file under `data/figure_data/` is tab-separated, carries a header line, and begins
with one or more `#` comment lines stating what the numbers are and, where relevant, the
fitting window they were computed over. They can be read with any tool.

## Figure data files

| File | Figure | Content |
|---|---|---|
| `figure1ab_spectra.txt` | 1a, 1b | Illustrative exponential and algebraic spectra |
| `figure1c_rank_vs_accuracy.txt` | 1c | Required rank versus accuracy, closed form against direct tail sum, for exponential spectra with small and large spectral span |
| `figure2_ks_rank_accuracy.txt` | 2 | Kuramoto-Sivashinsky measured rank-accuracy curve with both fitted forms |
| `figure2_ks_slope_windows.txt` | 2, S1 | Slope of that curve as a function of the fitting window |
| `figures1_ks_spectrum.txt` | S1 | Singular values of the Kuramoto-Sivashinsky snapshot covariance |
| `figures1_l96_spectrum.txt` | S1 | Singular values of the Lorenz-96 snapshot covariance |
| `figures1_l96_rank_accuracy.txt` | S1 | Lorenz-96 rank-accuracy curve, showing saturation at r = n |
| `figure3_dky_vs_deff.txt` | 3 | Effective dimension against system size |
| `figure3_dky_lyapunov.txt` | 3 | Effective dimension against the Kaplan-Yorke dimension |
| `figure5_controlled_exponents.txt` | 5, 3b | Predicted and measured error-width exponents for the controlled operators |
| `figure6_estimator_validation.txt` | 4 | Fitted parameters and rank predictions against snapshot count |
| `figure6_l96_width_scan.txt` | 4, S2 | Lorenz-96 width scan, test MSE against width |
| `figures3_ks_width_tau0.5.txt` | S3 | Kuramoto-Sivashinsky width scan at tau = 0.5 |
| `figures3_ks_width_tau0.125.txt` | S3 | Kuramoto-Sivashinsky width scan at tau = 0.125 |

## Reproducing the results

The scripts are organised by the artifact each one produces and are not a single
end-to-end pipeline; they were written in the order the analysis was carried out. They
fall into four groups.

**Theory and classification.** `v16_theory2.py` verifies the closed form against direct
tail sums. `v17_blind2.py` runs the blind classification over eighteen synthetic systems
and writes `v17_blind_test_v2.json`. `v20_checkB2.py` and `v21_rankcap3.py` test whether
a third spectral class is needed, by four methods that share no assumption.

**Observational data.** `download_real_data.py` fetches the HadISST1 and OISST v2
sea-surface temperature fields. `v18_verify2.py` performs the pre-registered
prediction and its verification, and records the noise floor of the observational spectra
and the smallest resolvable accuracy.

**Width and estimator experiments.** `l96_width_v6.py` and `ks_width_v6_fixed.py` run the
width scans; `estimator_validation.py` and `r3d_budget.py` produce the estimator results
and the training-budget study.

**Conventions and conditioning.** `v20_checkD2.py` establishes that the measured class
flips with the norm; `v24_condition.py` and `v24_multisig.py` measure the coupling
between invariance defect and numerical conditioning.

Figures are produced by `build_v22_figures.py` (Figures 1, 5 and the estimator panel),
`build_v6_figures.py` (the Lorenz-96 and Kuramoto-Sivashinsky width panels),
`compose_fig2.py` (Figure 2), `v10_build.py` (the Kaplan-Yorke panel) and
`v28_graphabs4.py` (the graphical abstract). Each reads from `data/artifacts/`.

The manuscript itself is generated by `code/manuscript/make_manuscript_v3_jcp.py` and
checked by `code/manuscript/validate_v3.py`. The validator enforces the structural
requirements of the journal and, separately, `verify_v6/check_tables.py` and
`verify_v6/audit_numbers_v13.py` check that no table cell is empty and that all 34
quantitative claims in the text agree with the stored artifacts.

## A note on what was checked, and what was found

Every DOI in the reference list was resolved through the Crossref API during preparation
of the revision. Two of them pointed to unrelated papers and were corrected
(`10.3934/jcd.2014.1.391` for Tu et al. and `10.1038/s41567-023-02303-0` for Thibeault
et al.), and three article numbers that were missing were obtained from Crossref. All
twenty-six DOIs now resolve.

An earlier version of this work asserted that the width-accuracy branch had been
established. On re-examination it had not: the measured exponent moves the wrong way as
the spectral exponent falls, and no spectral exponent is recovered on the real systems.
The width branch is now reported as not established, and `data/artifacts/` retains the
measurements that forced that conclusion rather than only the ones that supported the
earlier claim.

The figures in this repository are reproduced at 300 dpi to meet the journal's
requirement. The two that originally carried a DPI of 296 and 297 have been corrected.

## Environment

Python 3.11 with numpy, scipy, matplotlib and python-docx. See `requirements.txt`. The
scripts were run on Windows; paths are absolute and would need editing on another
platform. No GPU is required; the training experiments are small multilayer perceptrons
and DeepONets trained on CPU.

## Data sources

The observational fields are public:

- HadISST1 sea-surface temperature, Met Office Hadley Centre
  <https://www.metoffice.gov.uk/hadobs/hadisst/>
- OISST v2 monthly sea-surface temperature, NOAA PSL
  <https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.html>

Neither is redistributed here; `download_real_data.py` retrieves them.

All dynamical-systems data are generated by the scripts in `code/experiments/` from
published parameters and are reproducible from a fixed random seed.

## Licence

MIT for the code. The manuscript text is not covered by the MIT licence.
