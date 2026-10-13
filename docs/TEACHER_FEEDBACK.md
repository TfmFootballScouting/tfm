# Teacher feedback — current clean submission

Review branch: `review/teacher-submission`. This is the clean package, not an archive of every experiment. Original teaching documents remain; current code/data/evidence are documented in `DATA_SOURCES.md` and `REVIEW_GUIDE.md`.

| # | Comment | Implemented | Remaining / manual |
|---|---|---|---|
| 1 | Dependencies | 8 direct app dependencies; runtime/research locks separate; optional RDS readers separate | Native Windows check |
| 2 | Absolute paths | Current metadata uses portable project-relative paths; source fingerprints handle line endings | Production configuration remains deployment-specific |
| 3 | Expert validation | Temporal baselines/robustness and real-data blind packets/forms plus executed analysis notebook | Recruit experts, obtain consent and collect actual ratings |
| 4 | Market values | Reported dated values after ranking; no heuristic estimator, missing/zero exclusion and uncertainty labels | Verify player links and currency; values are not fees or historical affordability evidence |
| 5 | Dictionary | All prepared fields and raw-source catalog documented | Two unused team points fields remain provider-unverified |
| 6 | Process case ID | UUID scouting_request_id/case_id; repeated searches share a request | Business completion/approval policy for a real club |
| 7 | Event log | UTC timestamps, filters/styles, anonymous scout role, IDs and result counts | Individual users are not identified |
| 8 | Process variants | Directly-follows transitions, waiting times and case durations implemented | Real human sessions required; no organizational outcomes fabricated |
| 9 | Collection | Explicit Streamlit search/review/decision triggers; SQLite and JSONL/export | Test sessions excluded from human evidence |
| 10 | Operational vs MLflow | Separate operational requests/events/feedback SQLite database | Authentication, consent/retention administration and managed multi-instance DB |
| 11 | AWS evidence | Detailed official-evidence instructions and recorded blocked access attempt | Official calculator export/screenshot, date/region/currency and ECB quote; requests returned HTTP 403 |
| 12 | Cloud breakdown | Tested compute/storage/egress/backup/request/monitoring worksheet; unknown rates prevent a total | Enter dated official unit prices and verify workload/allowance/tax assumptions |
| 13 | MLflow versions | Dataset SHA and original training Git commit preserved | New retraining gets its own version/commit; no false replacement of original lineage |
| 14 | Tags | owner, dataset, environment, project and evaluation tags recorded | Completed for existing runs |
| 15 | Evaluation plots | Actual figures/CSV diagnostics retained with exact artifact hashes | Original artifact copies shared rather than duplicated |
| 16 | Synthetic separation | Real-data final pipeline; demo datasets/models/notebooks removed | Artificial unit fixtures are tests only |
| 17 | Portable MLflow | Relative artifact manifests point to current single-copy model/evaluation files | Local MLflow DB not included in clone; run training to populate a new local DB |
| 18 | Screenshots | Actual original main-run overview and artifacts captured, run ID and hashes included | No new fit is implied by the screenshots |
| 19 | Production | Auth/HTTPS/monitoring/backups/scaling described | Not claimed deployed; real infrastructure implementation is future work |

The approved A/B/C implementation is retained: dictionaries/expert tools/MLflow evidence, operational tracking and cloud formulas. No transfer-likelihood predictor or extra scenarios page was added. Use `reports/teacher_review/CLEANUP_REPORT.md` for final verification after removing obsolete files.

Manual expert collection: `expert_review/README.md`. Operational session collection/export: `OPERATIONAL_TRACKING.md`. AWS/FX capture: `evidence/cloud/README.md`. Native Windows: clean clone, Python 3.12, runtime lock, `pip check`, app filters/values/comparisons/group graph/history/shot checks.
