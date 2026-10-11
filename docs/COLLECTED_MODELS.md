# Collected-data modelling and recommendation analysis

The accepted name-plus-context matching method is retained in the existing identity trial and join preview. Acceptance of the method is recorded separately from verification of individual links. The new models learn only source-separated FBref measurements and use FBref player IDs for the temporal proxy; no uncertain cross-source identity or Transfermarkt market-value field enters fitting. The same project folders are used throughout.

## Experiments

| Track | Features | Development | Validation | Holdout |
|---|---|---|---|---|
| Offensive | goals, assists, shots, shots on target, xG, xAG per 90 | 2020/21–2022/23 | 2023/24 | 2024/25 |
| Core | nine mandatory rates, excluding redundant G+A | 2020/21–2021/22 | 2022/23 | 2023/24 |
| Attack on core | six offensive features on the exact core cohort | 2020/21–2021/22 | 2022/23 | 2023/24 |

The main tracks have different holdout years, so their scores cannot establish a controlled feature comparison. The third track supplies a same-season/same-person diagnostic. It was added after the initial trials and is explicitly post hoc, not independent confirmatory validation. All cohorts use outfield player-season observations after club aggregation and a 450-minute floor. Partial 2025/26, sparse 2024/25 core observations and synthetic/legacy files are excluded.

The offensive development cohort has 1,183 observations; validation has 393 and holdout 399. The core cohort has 795 development observations, 388 validation and 393 holdout. Two offensive development observations lack xG/xAG; they use medians learned only on development. Imputers, scalers, PCA and K-means remain frozen when transforming both evaluation seasons. Repeated development seasons weight observed player-year profiles, rather than pretending each row is a different person.

## Evaluation meaning

Queries are returning players from the previous season. Candidates are all eligible outfield players in the next season; the target is the query's same FBref identity. Future profiles are used only as evaluation targets. They are unavailable at a real scouting decision, so this experiment measures profile persistence rather than transfer success, player value, forecast production or club-fit relevance.

Comparisons include standardized cosine and Euclidean profiles, two/four PCA components, cluster-restricted cosine, goals-only, goals-and-assists and a reproducible random baseline. K is chosen by training silhouette across 2–8 clusters. The profile method is selected by validation MRR before evaluating holdout. The saved recommender's neighbour representation uses that selected method; style-affinity scoring remains the existing separate expert-weighted function.

Metrics are MRR, Recall@5, Recall@10 and NDCG@10. Score ties receive expected ranks/hits under uniform tie ordering; source IDs never determine whether a zero-goals target gets a good baseline rank. Cluster-excluded targets get zero reciprocal rank/hits. Query counts, returning-player fraction, candidate count and target availability are reported. Confidence intervals use 200 paired query bootstrap replicates and are conditional on the archive cohort; selection/survival bias remains.

## PCA, clusters and scouting interpretation

The initial main-track trials selected full standardized Euclidean distance. Offensive PC1 combines goals, shots, shots on target and xG; PC2 emphasizes assists/xAG. Core PC1 contrasts attacking rates with interceptions/tackles; PC2 mixes crossing, tackling and fouls. Component signs are arbitrary. High explained variance does not by itself justify discarding dimensions for recommendation.

The main training searches choose two clusters, separating stronger attacking output from other profiles. Position cross-tabs and standardized centroids support that description. These groups are not six validated tactical roles. Seed ARI and position/season association are reported separately from retrieval performance. Hard cluster filtering excludes some same-player targets after their profile changes between seasons, so clusters remain explanatory rather than a default eligibility filter.

Shortlists use the highest-minute reference player in each position in the last development season. Alternatives require the same broad position, age at most 27, a single known club, a different club and a different identity. Each shortlist includes measured rates, exposure and source-season context. Budgets are unapplied because eligible historical valuations are missing. Offensive-only defender similarity lacks defensive dimensions and requires particular caution when interpreting alternatives. These are historical examples, not current transfer advice.

Twenty resamples of real development observations evaluate how training-median/scaler changes affect selected-method top-five lists. PCA/cluster representations, if used, stay fixed for this preprocessing sensitivity test; independent seed tests examine K-means stability. No football observations or feature values are generated as a fallback or presented as real data.

## Reproduce and inspect

```bash
cd /workspace/tfm_futbol
.venv/bin/python -m scripts.collected_models
.venv/bin/python -m scripts.collected_model_notebook
.venv/bin/python -m pytest -q
```

The executed notebook is `notebooks/06_collected_model_analysis.ipynb`. It verifies model/output checksums and replays validation calculations with frozen saved transformations. Summary results are in `reports/collected_model_results.json`. Detailed scores, query-level outcomes, PCA loadings, cluster searches/profiles, bootstrap robustness, scouting examples, source-agreement diagnostics and figures are prefixed `collected_` inside the existing `reports/experiments/` folder.

Models are `models/real/collected_offensive_recommender.joblib`, `collected_core_recommender.joblib` and `collected_attack_on_core_recommender.joblib`. They do not overwrite the application's existing model/data. Joblib files are trusted local experiment outputs; load only trusted model files.

MLflow uses `tfm-scouting-collected-real-proxies`, separate from legacy/synthetic experiments. Runs record owner, project, dataset, environment, Git commit/source-dirty status, code hashes, features, selection parameters, metrics, model files and evaluation plots. Dataset/model manifests use relative artifact paths. Portable exports under the existing `reports/mlflow_export/` directories are downloaded from the actual finished logged runs, retaining parameters/metrics/tags and omitting machine-local artifact URIs.

## Remaining requirements

Individual cross-source identities are unverified; agreement of source goals/xG is a diagnostic, not a labelled matching-accuracy test. Complete Segunda coverage, detailed goalkeeper/pressing roles, dated budgets, actual historical transfer relevance and genuine process event validation remain unavailable. The Streamlit application still serves its previous exploratory model pending a separate integration and validation step. These experiments improve the measured-profile recommendation study; they do not complete final real-world scouting validation.
