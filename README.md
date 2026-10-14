# The covariance spectrum, not the Koopman spectrum, sets the rank of data-driven models

Code and figure data for a paper submitted to the *Journal of Computational Physics*.

- Code repository: <https://github.com/ningwei1123/rank-scaling-diagnostic-v2>
- Archived release: <https://doi.org/10.5281/zenodo.23354867>

## What the paper claims

Practitioners choose the size of a reduced-order or operator-learning model from the decay
of a data covariance or POD spectrum, but no criterion states when that choice is sound.
The paper separates two operators that are routinely conflated: for a measure-preserving
system the Koopman operator is unitary, or an isometry for non-invertible maps, so it
never carries the decay that sets model size. That decay belongs to the covariance
operator over the invariant measure.

The central results are:

1. **A closed form for the required rank.** For an exponentially decaying covariance
   spectrum the rank reaching a relative accuracy is `r = d_eff + (1/alpha) log(1/eps)` in
   the norm convention; for an algebraically decaying spectrum it is
   `r ~ eps^{-1/(beta - 1/2)}`. The ambient dimension does not appear.
2. **An exact identity.** The error of the best rank-r linear model is exactly the tail of
   the output covariance, `min_{rank(M)<=r} E||y - Mx||^2 = sum_{k>r} lambda_k(K C K^T)`,
   so the relation is a guarantee rather than a heuristic.
3. **A checkable applicability condition.** The input spectrum reproduces that error if
   and only if the propagation operator is a scalar multiple of an orthogonal map,
   `A = cQ`. A weaker per-rank condition can be checked on a fitted operator.
4. **A computable separation of two exponents.** On generalized cat maps the resonance
   exponent is exactly half the Lyapunov top gap, to a relative error of 2e-14, while the
   measured covariance exponent varies by 0.6 percent over the same range; their ratio runs
   from 48 to 108.

Two features of the work are deliberate.

**The negative results are part of the contribution.** The width branch is not
established, and the paper explains why a power law in width is unavailable at this
generality. On real observational sea-surface temperature fields the diagnostic does not
transfer.

**The 16-of-18 classification is a consistency check, not an independent prediction.**
Both the diagnostic and the measured class are functions of the same spectrum. The
independent test is the Kuramoto-Sivashinsky slope comparison, where prediction and
measurement differ by 4 to 82 percent depending on the fitting window; that spread is
traced to the spectrum being of neither pure form, and it is reported rather than
concealed.

## Layout

```
manuscript_rank_scaling/
    README.md
    LICENSE                       MIT (code only)
    requirements.txt
    code/
        experiments/    75 scripts  the analysis that produces the results
        figures/         6 scripts  the plotting code for the ten figures
    data/
        figure_data/    29 files   every figure panel as plain text (tab-separated)
    figures/            10 PNGs    the figures as they appear in the manuscript
```

## Figure data files

Each file under `data/figure_data/` is tab-separated, carries a header line, and begins
with one or more `#` comment lines stating what the numbers are and, where relevant, the
fitting window they were computed over. They can be read with any tool.

| File | Figure | Content |
|---|---|---|
| `figure1ab_spectra.txt` | 1a, 1b | Illustrative exponential and algebraic spectra |
| `figure1c_rank_vs_accuracy.txt` | 1c | Required rank versus accuracy: closed form against direct tail sum, for exponential spectra of small and large span |
| `figure2_ks_rank_accuracy.txt` | 2 | Kuramoto-Sivashinsky measured rank-accuracy curve with both fitted forms |
| `figures1_ks_spectrum.txt` | 5 | Singular values of the Kuramoto-Sivashinsky snapshot covariance |
| `figures1_l96_spectrum.txt` | 5a | Singular values of the Lorenz-96 snapshot covariance |
| `figures1_l96_rank_accuracy.txt` | 5 | Lorenz-96 rank-accuracy curve, showing saturation at r = n |
| `figure3_dky_vs_deff.txt` | 3 | Effective dimension against system size |
| `figure3_dky_lyapunov.txt` | 3 | Effective dimension against the Kaplan-Yorke dimension |
| `figure5_controlled_exponents.txt` | 6, 2 | Predicted and measured error-width exponents for the controlled operators |
| `figure5_algebraic_branch.txt` | 6 | The controlled random field that instantiates the algebraic branch |
| `figure5_algebraic_spectra.txt` | 6 | Spectra of that random field |
| `figure6_estimator_validation.txt` | 9 | Fitted parameters and rank predictions against snapshot count |
| `figure6_l96_width_scan.txt` | 6 | Lorenz-96 width scan, test MSE against width |
| `figures3_ks_width_tau0.5.txt` | — | Kuramoto-Sivashinsky width scan at tau = 0.5 (negative result, archived) |
| `figures3_ks_width_tau0.125.txt` | — | Kuramoto-Sivashinsky width scan at tau = 0.125 (negative result, archived) |
| `c7_controlled_6seeds.txt` | 6 | Per-seed error-width exponents for the three controlled spectra |
| `c7_exact_reference.txt` | 6 | Exact truncation reference for those operators |
| `estimator_validation.txt` | 9 | Fitted parameters and rank predictions per snapshot count |
| `ks_slope_window_scan.txt` | 2 | Slope of the Kuramoto-Sivashinsky curve as a function of the fitting window |
| `real_l96_width.txt` | 6 | Lorenz-96 width scan, measured |
| `v15_alpha_res.txt` | 7 | Resonance exponent on the generalized cat maps |
| `v22_alignment2.txt` | 8 | Per-rank tail ratios for the alignment condition |
| `v26_branch_vs_n.txt` | 10 | Which branch fits better, as a function of Toeplitz order |
| `v26_toeplitz.txt` | 10 | Toeplitz spectra and their fitted exponents |
| `v27_per_r_alignment.txt` | 8 | Tail ratios at fixed ranks |
| `width_law_v6_summary.txt` | 6 | Summary of the width scans |
| `z1_exponent_recomputed.txt` | 1, 4 | Rank-law exponents recomputed from spectra |
| `tableS2_closed_form_bound.txt` | — | Closed form against enumeration over the verification grid |
| `tableS3_clean_pde.txt` | — | Controlled-PDE exponents |

## The figure code

| Script | Produces |
|---|---|
| `build_v22_figures.py` | Fig. 1 (rank-dimension law), Fig. 4 (rank laws and ceilings), Fig. 9 (estimator validation) |
| `compose_fig2.py` | Fig. 2 (measured rank-accuracy curve) |
| `v22_fig1c.py` | Fig. 1c (saturation panel) |
| `v30_new_figures.py` | Fig. 5 (diagnostics), Fig. 7 (two exponents), Fig. 8 (alignment), Fig. 10 (branch fold) |
| `build_v6_figures.py` | Fig. 6 (controlled operators) and the archived width panels |
| `v28_graphabs4.py` | the graphical abstract |

The plotting scripts were written against the intermediate JSON artifacts of the analysis
rather than against the tab-separated files in `data/figure_data/`. The tab-separated
files are the figure data and are sufficient to reproduce every plotted quantity; the
plotting scripts are included for reference and would need their loaders pointed at those
files to run as they stand.

## The experiment code

`code/experiments/` holds 75 scripts, written in the order the analysis was carried out.
They are organised by the result each produces and are not a single pipeline. The main
groups are:

**Theory and classification.** `v16_theory2.py` verifies the closed form against direct
tail sums. `v17_blind2.py` runs the blind classification over eighteen synthetic systems.
`v20_checkB2.py` and `v21_rankcap3.py` test whether a third spectral class is needed, by
four methods that share no assumption.

**Observational data.** `download_real_data.py` fetches the HadISST1 and OISST v2
sea-surface temperature fields. `v18_verify2.py` performs the pre-registered prediction
and its verification and records the noise floor of the observational spectra.

**Width and estimator experiments.** `l96_width_v6.py`, `real_l96_width.py` and
`ks_width_v6_fixed.py` run the width scans; `estimator_validation.py` produces the
estimator results.

**Conventions and conditioning.** `v20_checkD2.py` establishes that the measured class
flips with the norm; `v24_condition.py` measures the coupling between invariance defect
and conditioning.

**Algebraic branch and the exponent separation.** `v11_algebraic_branch.py` and
`v11_algebraic_branch_figure.py` instantiate the algebraic branch on a controlled random
field; `v15_alpha_res.py` and `v15_alpha_res_analytic.py` compute the resonance exponent
on the generalized cat maps; `v22_alignment_condition.py`, `v26_toeplitz.py`,
`v26_branch_vs_n.py` and `v27_per_rank_alignment.py` produce the alignment and branch
measurements.

## What was checked, and what was found

Every DOI in the reference list was resolved through the Crossref API, and every arXiv
identifier was checked against arxiv.org. The reference list holds 33 entries, all of them
cited in the text. Three errors were corrected during the final pass: the Benettin,
Galgani, Giorgilli and Strelcyn entry carried a title that does not exist and a page range
belonging to two separate papers, the Ledrappier and Young entry was missing its Part II
designation, and two DOIs pointed at unrelated papers.

The algebraic exponent of Eq. (2) was wrong in an earlier version: it read
`eps^{-1/beta}` where the paper's own random-field instantiation and its own tabulated
predictions require `eps^{-1/(beta - 1/2)}`. The discrepancy was found by comparing
Eq. (2) against the stored artifact of the algebraic-branch run, whose predicted exponents
equal `1/(p - 1/2)` to four digits.

An earlier version of this work asserted that the width-accuracy branch had been
established. On re-examination it had not: the measured exponent moves the wrong way as
the spectral exponent falls. The width branch is reported as not established, and
`data/figure_data/` retains the measurements that forced that conclusion rather than only
the ones that supported the earlier claim.

## Environment

Python 3.11 with numpy, scipy, matplotlib, python-docx, h5py, latex2mathml and
mathml2omml. See `requirements.txt`. No GPU is required; the training experiments are
small multilayer perceptrons and DeepONets trained on CPU. Plotting was done with
matplotlib at 300 dpi to meet the journal's requirement.

## Data sources

The observational fields are public and are not redistributed here:

- HadISST1 sea-surface temperature, Met Office Hadley Centre
  <https://www.metoffice.gov.uk/hadobs/hadisst/>
- OISST v2 monthly sea-surface temperature, NOAA PSL
  <https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.html>

`download_real_data.py` retrieves them. All dynamical-systems data are generated by the
scripts in `code/experiments/` from published parameters.

## Licence

MIT for the code. The manuscript text is not covered by the MIT licence.
