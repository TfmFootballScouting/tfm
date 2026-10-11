# Enriched real-data pipeline

The uploaded statistics, profiles, valuation histories and transfers now pass through an executable, source-separated cleaning and analysis pipeline. The existing folder layout is preserved. The original datasets, preprocessing artifacts and models remain unchanged; new outputs use the `collected_enrichment_` and `enrichment_` prefixes.

## Data added and cleaned

| Output | Actual rows | Meaning |
|---|---:|---|
| `collected_enrichment_player_club_seasons.parquet` | 8,252 | La Liga/Segunda source stints, 2020/21–2025/26, with parsed counts/minutes, raw text and profile context |
| `collected_enrichment_player_seasons.parquet` | 8,043 | Source player–league–season observations after safe club aggregation |
| `collected_enrichment_transfers.parquet` | 365,920 | Worldwide target-season transfer events after 37 exact duplicates are removed with lineage retained |
| `collected_enrichment_spain_transfer_context.parquet` | 8,665 | Origin/destination Spanish club-season contexts for 6,796 distinct reported events |
| `collected_enrichment_integration_review.parquet` | 3,378 | Existing FBref observations preserved; 2,757 receive proposed same-season, same-league source additions |
| `collected_enrichment_reported_price_context.parquet` | 8,043 | Backward-only reported valuation-date associations for auditing, never eligible budget prices |

These files are retained locally in `data/processed/real/` and ignored by Git because provider redistribution rights are unverified. The original ZIPs, extracted payloads and receipt checksums remain in `data/raw/sources/salimt_uploaded/histories/`. Fresh environments need the retained snapshot or the same uploaded files. Metadata and aggregate reports are committed; the individual-row source-comparison CSV remains local.

Within the uploaded source, player ID identifies the person and season/competition/club identifies the observation. Existing cross-source mapping proposals are one-to-one and joined to FBref by proposed entity, **season and league**. They remain unreviewed; no name-only overwrite or same-player season collapse occurs. Profiles join on source player ID, but current position/profile metadata is labelled as current rather than historical. Transfers join to Spanish club-season membership separately for origin and destination: contexts are not proof of player league membership and must not be counted as independent events.

Count parsing retains original strings. Missing, negative, fractional and nonfinite measurements become unknown with invalid-value flags; observed zero is preserved. Season totals require every relevant club-stint count/minute measurement to be known. Per-90 rates use complete positive minutes, and the 450-minute threshold follows aggregation. The full mandatory feature schema is present; advanced fields absent from this source are explicitly null with a source-coverage reason, never fabricated. All six original style definitions are preserved. G+A is descriptive and remains excluded from fitting as algebraically redundant.

## Findings and decisions

There are **4,731 stints with missing minutes**, including **3,420 with reported appearances**. Missingness depends on appearance exposure; complete-minute subsets are selected samples, not league-wide representative cohorts. 2025/26 is partial: only one uploaded aggregated record meets the complete 450-minute requirement across both leagues. No final-season production comparison is justified for that snapshot.

On proposed cross-source joins, goals agree in **2,520/2,542** comparable records, assists in **2,538/2,757**, and minutes in **164/1,427**. These are provider/join diagnostics, not identity-accuracy labels. The minute discrepancy prevents mixing counts from one source with the other source's minute denominator. FBref features and minutes are therefore retained unchanged.

Conservative count-consistency and extreme-value checks flagged zero stints in this subset; this does not establish that all values are correct. Additional descriptive IQR tail flags use only 2020/21–2022/23 observations meeting the minute threshold. No flags cause deletion or global winsorization. EDA includes missingness by appearance band, distributions, pairwise Spearman correlations, outlier flags, league/season comparisons and current-position groupings. Current position labels cannot validate historical tactical roles.

The cleaned transfer history has **353,561 reported zero-fee events** and **2,282 dates outside their source July–June season window**. Zero does not automatically mean a verified free transfer, particularly for loans and loan returns. Season/date conflicts are retained for offseason/source-label review. Market value and transfer fee remain distinct quantities, with claimed EUR units marked as unverified. Price associations use only reported dates on/before season end; unknown original publication dates prevent historical availability claims or budget eligibility.

## Models actually executed

The existing repository source-use guard rejects Transfermarkt-derived fitting, and the identity guard rejects unreviewed cross-source joins. The enriched tables were tested against these guards and rejected; no guard was removed or provenance relabelled. Cleaning, descriptive analysis and review preparation do not grant model-use authorization.

Three **eligible real FBref models were freshly refitted**, with new models, plots and genuine MLflow runs. Training medians/scaling/PCA/K-means use development observations only; validation selects the distance method and holdout remains chronological. Goals-only, goals+assists and seeded-random baselines, bootstrap confidence intervals, seed stability, shortlist perturbation robustness and descriptive recommendation lists are retained. This executes the model stage on eligible data; **it does not train on the newly uploaded enrichment**.

| Experiment | Holdout MRR | Recall@5 | Scope |
|---|---:|---:|---|
| Offensive | 0.085516 | 0.106996 | Six FBref attacking features |
| Core | 0.223352 | 0.337349 | Nine FBref core features, excluding redundant G+A |
| Attack on core cohort | 0.065909 | 0.084337 | Matched-cohort attacking-feature comparison |

All three select standardized Euclidean profile distance and K=2. Their holdout MRR matches the previous experiments; no enrichment gain is claimed. PCA's first two components explain approximately 87.9% for offensive and 58.1% for core. Cluster centroids, PCA loadings and position/season associations are analysed in the notebook. Clusters are descriptive statistical groupings and are not the six expert style directions. High seed agreement is not role accuracy; earlier core-PC4 instability still limits interpretation. The model target remains next-season same-player profile retrieval, not actual transfer success or club-fit relevance.

Fresh model files are `models/real/enrichment_{offensive,core,attack_on_core}_recommender.joblib`. The existing Streamlit serving model is unchanged. MLflow uses its own real-data experiment, `tfm-scouting-enrichment-eligible-real-rerun`, with owner, project, dataset, learned-dataset version, environment, Git commit and source hashes. Artifact exports were downloaded from completed runs and checksum-verified; export paths and source names are portable.

## Reproduce and review

From the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m scripts.enriched_pipeline
.venv/bin/python -m scripts.enrichment_notebook
.venv/bin/python -m pytest -q --junitxml=reports/enrichment/full_tests.xml
.venv/bin/python -m scripts.verify_enriched_pipeline
```

Run these stages sequentially: the pipeline completes its immutable artifact manifest before notebook/test verification. Reports are under `reports/enrichment/`; `pipeline.json` contains dataset/code provenance and preserved-input checksums, `dictionary.csv` defines all output columns and units, and `verification.json` records executed checks. The executed notebook is [08_enriched_data_pipeline.ipynb](../notebooks/08_enriched_data_pipeline.ipynb).

Completed: raw preservation, source-specific numeric cleaning, safe season aggregation, exact transfer deduplication, profile and reported-price associations, same-season proposed FBref enrichment, Spanish transfer contexts, executable EDA, three eligible model refits and MLflow exports. Partial: independently verified fee semantics, source publication evidence, historical roles and cross-source identities. Blocked: uploaded fields entering ML fitting under existing guards; no reviewed source-use authorization or identity approvals have been supplied. Unimplemented: a trained valuation model, enriched Segunda recommendation model, verified historical-budget scouting and transfer-outcome validation.

Final verification: **90 tests passed**, zero failures/errors/skips; the new notebook executed **9 code cells with zero errors**; **220 prior files** and **94 new outputs** were checksum-verified. Three actual finished MLflow runs and their downloaded artifacts were checked. Streamlit and MLflow health requests both returned HTTP 200; the full suite includes the existing application test.
