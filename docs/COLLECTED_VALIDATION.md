# Extended validation on collected real data

The available PCA, K-means and recommendation diagnostics have been executed on the three existing collected-data model tracks. This phase adds whole-player resampling, seasonal drift, position-specific retrieval and analysis of all six original playing styles. It preserves the existing folder structure, raw datasets, source-separated tables, identity proposals and fitted models. No provider downloads, synthetic experiment data or new holdout tuning are involved.

The analyses are **post hoc**: these validation/holdout cohorts were already examined in the model-comparison phase. Stability and identity/profile retrieval are measured; successful transfers, tactical relevance and club fit are not. The original chronological results remain unchanged.

## Design

Thirty seed-42 bootstrap replicates sample development player identities with replacement. Every observed development season of a sampled person is retained together. Duplicate draws are statistical fitting weights on real observations, not invented player records. Development rows per replicate vary because people have different numbers of seasons. Median imputation, standard scaling, PCA and K-means are refitted; K=2 and four PCA components remain fixed at their previously selected values. Validation/holdout observations never enter these fits.

The reference set is the original development cohort. Out-of-bag (OOB) players are absent from each bootstrap fit, including all their seasons. ARI compares bootstrap assignments with the original model and is invariant to cluster-label permutation. Centroids are matched after conversion to the original standardized coordinates. All 30 OOB replicates had sufficient cluster diversity in all three tracks. Players are the resampling unit; club/competition dependence is not modelled.

Bootstrap PCA score directions are converted to the original standardized coordinates, sign/order matched by absolute loading cosine, and assessed jointly with principal angles for the top-two and top-four subspaces. Explained-variance ratios refer to each replicate's standardized covariance. Full covariance eigenvalues document sensitivity around truncation boundaries. Bootstrap ranges/quantiles are conditional diagnostics, not external accuracy confidence intervals.

Neighbor and style top-five stability uses a fixed last-development-season gallery. Neighbor queries are the highest-minute historical player in each broad position, with their own identity excluded. Style lists use the original expert weight vectors and same-position galleries. These checks cover three reproducible neighbor queries and six style directions, rather than every possible scouting request.

## Executed stability results

| Track | Development people | Mean OOB cluster ARI | Minimum OOB ARI | Mean largest top-four PCA angle | Mean neighbor top-five Jaccard |
|---|---:|---:|---:|---:|---:|
| offensive | 644 | 0.9429 | 0.8133 | 4.98° | 0.9677 |
| core | 525 | 0.9731 | 0.9145 | 17.37° | 0.9444 |
| attack_on_core | 525 | 0.9305 | 0.7834 | 6.81° | 0.9926 |

The two broad clusters are relatively reproducible under changes in the sampled players, extending the earlier initialization-only check. Agreement does not validate their tactical meaning. The same-position neighbor examples are also relatively stable, conditional on this fixed gallery and selected method.

Core PCA has a material sensitivity at the four-component boundary. In replicate 19, PC4's matched loading cosine is **0.1303**, and the largest top-four subspace angle is **82.54°**. Original fourth/fifth covariance eigenvalues are 0.6718/0.5660; this replicate has 0.6002/0.5607. The weaker separation is consistent with sensitivity near the cutoff. The large principal angle shows that this change is not explained solely by a harmless sign flip or rotation within an unchanged retained subspace. Do not attach a fixed tactical label to PC4. The earlier retrieval comparison already favoured full standardized profiles over PCA compression; these diagnostics provide additional context without reselecting the model.

## Retrieval by position and season

Subgroups use the previous-season query position and the entire next-season candidate pool. Every method is paired with goals-and-assists by explicit FBref identity. Five hundred paired query bootstrap replicates report conditional MRR and difference intervals. Exploratory intervals are not corrected for multiple subgroup comparisons and cannot establish club relevance. The position-weighted summaries reconcile with the original overall holdout metrics.

Core holdout 2023/24, standardized Euclidean profiles:

| Prior position | Returning queries | MRR | Recall@5 | MRR gain over G+A | Paired 95% interval for gain |
|---|---:|---:|---:|---:|---:|
| DF | 107 | 0.2109 | 29.0% | 0.1686 | 0.1074–0.2284 |
| FW | 57 | 0.2218 | 36.8% | 0.1705 | 0.1060–0.2417 |
| MF | 85 | 0.2401 | 37.6% | 0.2131 | 0.1564–0.2745 |

Core profiles outperform the goals-and-assists baseline in all three observed position groups on this proxy. Offensive holdout subgroup difference intervals include zero for DF, FW and MF, so the aggregate improvement should not be treated as independently established within each position. Offensive and core main tracks have different holdout seasons; their scores are not a controlled feature comparison. The attack-on-core comparison remains the explicitly post-hoc matched-cohort ablation from the previous phase.

Only players returning above the 450-minute threshold have identity retrieval labels. Exits, injuries and other nonreturners are omitted. Future-season profiles are evaluation targets and are unavailable at the historical scouting cutoff. Results describe profile persistence rather than a deployable forecast.

## Seasonal drift and cluster transitions

Development transformations and cluster centres are frozen across seasons. Distribution tables report broad position composition; silhouette describes the frozen assignments without refitting or reselecting K. Transition tables match returning identities and keep the prior position.

Core clusters change for 26/270 returners in 2020/21→2021/22, 22/248 in 2021/22→2022/23 and **31/249 (12.45%)** in 2022/23→2023/24. The last number agrees with the targets removed by the hard cluster gate in the earlier core holdout experiment. Cluster membership is therefore unsuitable as a mandatory filter for every recommendation. It can change with role, observed production, exposure or roster selection; no causal tactical change is inferred.

Feature drift uses observed per-90 values, with missing counts reported separately. Histograms use fixed training quantile bins with infinite outer tails. Jensen–Shannon divergence uses base 2 and ranges from 0 to 1; there is no arbitrary alert threshold or significance test assuming independent season samples. Mean changes are expressed in development standard deviations.

The largest core differences occur in 2023/24 interceptions (JS 0.03475; mean shift −0.3638 training SD) and tackles won (JS 0.02626; +0.3689 SD). These warrant provider-definition, exposure and roster-composition review before interpreting football evolution. Offensive drift is smaller under this binning, with maximum JS 0.00809 for shots on target in 2024/25. Histograms can conceal within-bin changes, especially for zero-heavy rates. Sparse core 2024/25 and partial 2025/26 remain excluded from representative evaluation.

## The six original styles

All six original core style directions are retained and exercised: possession, high pressing, vertical play, counterattack, defensive solidity and wing play. Their measured absolute-weight fractions are 0.85, 0.85, 0.85, 0.80, 0.95 and 0.85 respectively. The existing minimum supported fraction is 0.60. Offensive tracks only support vertical play and counterattack under this rule; unsupported defensive directions are explicitly recorded.

Across the 18 core style/position combinations, mean top-five bootstrap Jaccard is **0.9026**. Vertical/FW is most sensitive (mean 0.7016, minimum 0.4286); high-pressing/MF has mean 0.7889. Pairwise shortlist overlaps are exported to expose redundancy between directions. The notebook displays historical player names, clubs, ranks and affinity scores.

These are expert-weighted proxies. Missing passing progression, pressure locations and transition tracking prevent independent validation of some tactical names. Stable rankings and shared shortlists cannot establish that the weights represent genuine playing styles. Budgets are not applied because eligible dated valuations remain absent.

## Reproduce and inspect

Use the existing checkout and Python 3.12 virtual environment. Retained raw archives and hash-matching baseline models/reports must be present; verification fails explicitly when they are missing or changed. Run from the repository root:

```bash
.venv/bin/python -m scripts.collected_validation
.venv/bin/python -m scripts.collected_validation_notebook
.venv/bin/python -m pytest -q --junitxml=reports/collected_validation_tests.xml
.venv/bin/python -m scripts.verify_collected_validation
```

The scripts use existing installed dependencies. Notebook execution uses the installed `tfm-python` kernel and repository-local Jupyter kernel path. It verifies source/model/output hashes and independently replays the first two core person-block trials in six diagnostic tables. It also reconciles position metrics and checks genuine finished MLflow runs.

Outputs stay in the existing locations:

- `src/models/validation.py`: diagnostic implementation; five additional semantic unit tests are in `tests/test_collected_validation.py`.
- `reports/experiments/collected_validation_*`: 14 CSV tables, four evaluation figures and lineage per track.
- `notebooks/07_collected_extended_validation.ipynb`: executed analysis with written interpretation.
- `reports/collected_validation_results.json`: dataset/validation versions, code/Git references, metrics and hashes.
- `reports/collected_validation_verification.json`: source preservation, result reconciliation, notebook/test and logged-artifact checks.
- `reports/mlflow_export/`: downloaded portable artifacts and `collected_validation_*_run.json` records in the existing export folders.

MLflow experiment `tfm-scouting-collected-validation` is separate from the original profile-comparison experiment and synthetic demonstrations. The three selected final validation runs reference frozen base-model runs, record owner/project/dataset/environment/Git/version/design tags and log diagnostic artifacts. Earlier development iterations remain in the local tracking store; the summary identifies the final run IDs. All **57 final logged/exported artifacts** were verified by checksum. All **62 tests passed**, with zero failures/errors/skips. Notebook 07 executed **nine code cells with zero errors**. Original source/raw/model/application files were verified unchanged; Streamlit and MLflow health checks returned HTTP 200 in the current instance.

## Completion and remaining evidence

Completed locally: extended resampling stability, PCA boundary diagnosis, seasonal drift/transitions, position-specific retrieval, six-style robustness, executed notebook, tracked/exported artifacts and verification. No collection/source rights changed.

Partial: conditional real-data recommendation analysis, heuristic style interpretation and cross-source matching proposals. Independent identity accuracy and recommendation relevance are unmeasured.

Blocked/unverified: actual historical transfer-success validation, dated budget scenarios, complete Segunda evaluation, detailed goalkeeper/tactical roles, strict historical source-availability proof and discovery from genuine scouting events. Source permissions, suitable dated records and independent labels remain prerequisites. The app still serves its earlier model; the next implementation phase can integrate the collected core/offensive models and their measured-style coverage into Streamlit. Local commits have not been pushed; fresh cloud restoration remains unverified.
