# Teacher review — clean submission

This branch contains current project inputs/code/models/notebooks and required evidence only. Historical stages and duplicate artifacts were removed; the previous snapshot remains in Git history at `252e030`.

Read in this order:

1. `README.md`: app startup, CSV cleaning and separate training commands.
2. `DATA_SOURCES.md`: acquisition, raw paths, joins, temporal handling and model code.
3. `DATA_DICTIONARY.md` and raw/prepared CSV glossaries.
4. Three source EDA notebooks, notebook 11 for current model evaluation, notebook 12 for group analysis, and `expert_validation.ipynb` for human review (ratings pending).
5. Original Module 2/9 documents and `memoria_resumen.md`.
6. `TEACHER_FEEDBACK.md`: all 19 comments and real remaining manual tasks.
7. `reports/teacher_review/CLEANUP_REPORT.md`: final clean-branch verification; `docs/evidence/mlflow/` and `docs/evidence/cloud/` for experiment/cost evidence.

Current Core is expert style affinity plus nearest-player profiles, PCA and K-means. Evaluation uses chronological same-player future-profile retrieval, not observed transfer success. Real reported values are post-ranking filters; identity matching and currency remain provisional. Human ratings, real operational sessions, official AWS pricing/FX evidence and native Windows verification remain pending.
