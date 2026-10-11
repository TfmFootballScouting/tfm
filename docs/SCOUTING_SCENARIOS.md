# Scouting scenarios

The evaluated collected models now support explicit club requirements in the sixth Streamlit tab. These are illustrative, adjustable requirements, not verified official club plans. Each scenario has one vacancy and returns alternative players; a reported market-value ceiling does not establish transfer affordability or total acquisition cost.

The existing folder structure and frozen models remain intact. Real FBref profiles are ranked with the selected expert style, then screened by broad historical position, known age, minimum observed minutes, every own-club stint, positive reported price availability and value ceiling. Top-N selection happens after all constraints. No automatic relaxation or estimated-price fallback occurs. Price associations retain provisional identity, restricted-use and unknown-publication metadata and never enter model transformations or fitting.

Prices are the latest reported effective record on or before June 30 of the observed season. A latest zero remains ambiguous and cannot inherit an older positive value. This season alignment does not establish original publication or historical decision availability. The app's general budget filter remains a separately adjustable reported-date screen.

Four templates: young possession midfielder (23 years, 900 minutes, €5M); defensive defender (27, 1,800, €8M); vertical forward (25, 900, €10M); broad forward used as a wing-play proxy (25, 900, €10M). Club defaults to Valencia. All requirements can be edited. Offensive offers only supported styles. Broad FW does not certify winger suitability.

## Reproduction

Run from the repository root with retained real datasets and existing evaluated model artifacts:

```bash
.venv/bin/python -m scripts.scouting_scenarios
.venv/bin/python -m scripts.scenario_notebook
.venv/bin/python -m pytest -q --junitxml=reports/scouting_scenarios/tests.xml
.venv/bin/python -m streamlit run src/app/streamlit_app.py --server.headless true
```

Ten cases use seasons after the model training period: Core 2022/23 and 2023/24, offensive 2023/24 and 2024/25. Core exposes all four templates; offensive supports vertical here. Results include strict exclusion funnels, eligible-pool baselines (goals+assists per90, goals per90, seeded random selection), six requirement perturbations and shortlist CSVs. Jaccard measures selection membership, not transfer accuracy or validated tactical relevance. Empty/empty overlap is unknown. Sensitivity changes requirements only, with no simulated player measurements.

Individual source-price shortlists are private local outputs excluded from Git. Aggregate reports and the executed notebook are retained. The batch verifies existing protected artifact checksums and records dataset version, Git commit, source fingerprints and output fingerprints. Existing MLflow model runs are unchanged; no retraining or new model experiment is claimed.

Only explicit app executions create need/search/ranking process events; explicit review creates review events. Batch execution creates no human activity. Test events use temporary files.

## Completion and limits

Completed: requirements, no-relaxation screening, downloadable app output, real-data execution, same-pool baselines, parameter sensitivity and executable analysis. One Core 2023/24 possession case returns two eligible players, fewer than the requested five. This is a feasibility result, not an implementation failure.

Partial: statistical playing-style and positional proxies; cross-source identities are not individually reviewed. Blocked: actual transfer-success validation needs reviewed identities, original publication timing, defensible outcome labels and fee/club requirements. No historic transfer-success score, official budget or estimated market value is invented. Advanced Segunda gallery coverage remains unavailable.

Current-instance validation: 101 tests passed, zero failures/errors/skips; the new notebook executed four code cells with zero errors. Run `.venv/bin/python -m scripts.verify_scouting_scenarios` to verify scenario/source fingerprints, notebook execution, test results and the running Streamlit health endpoint.
