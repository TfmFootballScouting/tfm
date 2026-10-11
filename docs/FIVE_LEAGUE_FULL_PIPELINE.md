# Full five-league pipeline rerun

The entire eligible five-league statistical pipeline was executed from retained real FBref archives: cleaning, season-aware aggregation, missingness/outlier analysis, EDA, three new model fits, chronological evaluation, PCA/K-means interpretation, robustness, cross-source review and reported-value scenarios. Prior raw datasets, outputs and model artifacts are unchanged. New outputs have separate filenames.

## Actual data and preprocessing

16,334 club-season records aggregate to15,948 player-league-season records. Gallery selection keeps the highest-minute league for each person-season before checking feature eligibility; competitions are never blended. There are7,398 Core gallery observations and9,198 offensive observations across available years. Core2024/25 is too sparse; partial2025/26 and unsupported Segunda advanced profiles remain excluded.

Auxiliary categories must agree with the standard exposure within source rounding tolerance; incompatible counts stay missing. Unknown stints propagate to seasonal totals. Age/count/unit checks and exact duplicate handling are executed. Outliers are flagged, never automatically removed or winsorized. Descriptive IQR bounds use2020/21–2021/22; model imputation and scaling use only each model's own training cohort. Distributions, Spearman correlations, missingness and position/season/league comparisons are saved with written analysis in notebook11.

## New real model experiments

| Model | Training | Validation | Holdout | Pooled MRR | Recall@5 |
|---|---|---|---|---:|---:|
| Core, nine independent features / six style proxies |2020/21–2021/22|2022/23|2023/24|0.095498|0.129542|
| Offensive, six attacking features |2020/21–2022/23|2023/24|2024/25|0.031223|0.038710|
| Attack features on Core cohort |2020/21–2021/22|2022/23|2023/24|0.024100|0.028436|

K=2 was selected using training silhouette; Euclidean profile distance was selected on validation for all three. Future seasons never fit preprocessing/PCA/clusters. Holdout targets are the same players in the next season, among1,810 Core candidates or1,804 offensive candidates. These are profile-persistence metrics, not transfer success, club relevance or tactical-fit accuracy. Core/offensive differ in years/cohorts and are not a controlled comparison.

### Fair comparison with the original models

The original La Liga-trained models were also evaluated on these identical five-league holdout pools and returning identities. Compared with the original frozen model on the same pool, new Core MRR increases by0.003406 (paired500-bootstrap95% interval0.000625–0.006185); offensive increases by0.000594 (0.000191–0.001151). Attack-on-Core difference0.000056 has an interval spanning zero(-0.000259–0.000422). These are small cohort-conditional retrieval differences; no signing-performance gain is claimed. Earlier single-league MRR values should not be compared directly with the larger pooled universe.

## PCA, clusters and robustness

Thirty player-block bootstraps per model retain all seasons of each sampled real player and refit imputation/scaling/PCA/clusters. All-season and out-of-bag ARI, component alignment, subspace angles, neighbor/style top-five stability, feature drift and temporal cluster transitions are recorded.

Core PCA explains57.97% in two components and80.09% in four. Its PC2/PC3 individual loading alignment is less stable(minimum cosine approximately0.71) than PC1/PC4; inspect subspace stability before assigning distinct meanings to those components. Offensive two-component variance is88.78%. Statistical clusters associate more strongly with broad position than season or league; Core position NMI0.3753 versus league NMI0.00017. This does not make the two clusters six discovered tactical styles. Original six style directions remain expert-defined proxies.

Mean neighbor top-five person-bootstrap Jaccard: Core0.9741, offensive0.9444, attack-on-Core0.9741. These are conditional stability diagnostics, not calibrated recommendation confidence.

## Cross-source review and budget scenarios

Retained upstream source-ID mapping plus exact normalized names and unambiguous birth-year agreement yields4,869 supported provisional identity pairs across five leagues. No pair is automatically approved. Private profile enrichment preserves the original FBref observation grain and is rejected by model-use guards; current DOB/profile evidence does not prove historical availability. Source restrictions remain visible.

For the2023/24 Core gallery, positive reported values on/before June30 are available for332 La Liga,344 Premier League,302 Bundesliga,350 SerieA and299 Ligue1 players. These reported market assessments use provisional identities and unknown original publication times. Unknown/latest-zero values are excluded from budget constraints; no estimated prices or fees are substituted. Neither these values nor profile fields enter model fitting.

Fifty one-vacancy illustrative scenarios were executed across the five league pools, validation/holdout seasons and supported styles. Strict position/age/minutes/own-club/value screens, same-pool baselines and six requirement perturbations are saved. Individual provisional source-price shortlists and identity review tables remain private/ignored. Offline batches create no human process events. Actual transfer-success and genuine scouting-process validation remain blocked by evidence gaps.

## MLflow and serving

Three actual real-data model-refit runs in `tfm-scouting-five-league-trained-real` are FINISHED, each with26 downloaded checksum-verified artifacts, owner/dataset/environment/project/Git tags and portable paths:

- Offensive: `77dc5b4e615245ae910aec3a75360136`.
- Core: `85b7e82117814713b9094a5385308f6f`.
- Attack-on-Core: `8c9b96e63c57430f9662f917908e571b`.

The app's five-league market offers `Entrenamiento`: new European-trained models or original La Liga-trained models. Both retain their own frozen training transforms when a serving season changes. All six Core styles remain available. The original La Liga-only and legacy galleries are preserved.

## Reproduce

From the retained repository workspace with Python3.12, main lockfile, archive readers and real raw uploads:

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MPLCONFIGDIR=/tmp/tfm-matplotlib .venv/bin/python -m scripts.five_league_pipeline
.venv/bin/python -m scripts.five_league_comparison
.venv/bin/python -m scripts.five_league_review
.venv/bin/python -m scripts.five_league_pipeline_notebook
.venv/bin/python -m pytest -q --junitxml=reports/five_league_pipeline/tests.xml
```

Each pipeline rerun creates new actual MLflow runs; raw inputs and earlier experiment paths are retained. Review/scenario stages require private uploaded sources. A clone can serve ordinary trained-model recommendations using committed galleries/models; without private inputs it cannot reproduce review/budget stages or pass all data-dependent tests. Failures never trigger synthetic data substitution. Model-fitting permissions and historical budget availability are not inferred from upload or matching.

Current code/version, dataset/output hashes, preserved-input checksums and exact metrics are in `reports/five_league_pipeline/pipeline.json`. Dictionaries cover statistical fields, with the earlier source dictionaries retained for uploaded profiles, values and histories. Notebook11 contains the executed analysis and interpretation. Prior application/submission reports describe their historical versions; this rerun supersedes their app-source fingerprints without rewriting old experiments.

Final verification: 111 tests passed, with no failures, errors or skips; all eight notebook code cells executed without errors. The audit verified 335 preserved artifacts, three finished real-data MLflow runs, 78 exported artifacts, 50 scenarios and both served galleries. See `reports/five_league_pipeline/verification.json`. With Streamlit running on port 8502, repeat the audit using `python -m scripts.verify_five_league_pipeline`.
