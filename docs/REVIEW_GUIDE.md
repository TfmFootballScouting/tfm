# Teacher review guide

Start at the root README. It retains the original sections and authors while describing the actual current system.

1. Read `modulo2_caso_uso.md` and `memoria_resumen.md` for the problem, scope and evaluation limits.
2. Inspect `data/raw/review_manifest.json` and the 15 CSVs in the three source folders. RDS-to-CSV exports are distinguished from unchanged user-provided CSVs.
3. Run `python -m src.pipeline` with research dependencies to recreate clean CSV/Parquet tables under `data/processed/review/`. The frozen gallery/model are not overwritten; parity is checked.
4. Read the three source EDA notebooks: `fbref_eda`, `understat_eda`, `transfermarkt_eda`. They execute on retained real data and include interpretation, missingness, distributions/outliers and source-specific limitations.
5. Read notebook 11 for actual chronological model selection, baselines, PCA/K-means diagnostics, stability and MLflow. Its original results are not newly fabricated for this branch.
6. Inspect `models/recommender.joblib`, `metrics.json` and `models/README.md`; open the current main run under `reports/five_league_pipeline/mlflow_export/core/`.
7. Run Streamlit and exercise the six styles, five-league filters, reported-value budget, similar players, comparisons, groups, development and shot analysis.
8. Review `src/tests/` and `reports/teacher_review/`. Full retained-workspace tests and clean-clone checks are separate claims; optional archive integrations need retained inputs.
9. Read the original Module 9 documents and `TEACHER_FEEDBACK.md` for the 19-comment matrix, approval proposals and manual evidence instructions.

Original DOCX proposal remains byte-for-byte unchanged. Historical-stage notebooks/reports/raw demo files are retained for traceability and identified as historical; they are not the current source inputs or proof of transfer outcomes. There are no fabricated expert ratings, human process sessions, AWS quotations or MLflow screenshots.
