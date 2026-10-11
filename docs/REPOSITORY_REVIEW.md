# Repository walkthrough and cleanup

This review is staged so that each folder can be understood before code or evidence is removed. The first completed semantic review covers the **six tracked root files**. Every tracked file has also been indexed, but indexing is not a completed source-code or scientific review.

At the starting snapshot there are **1,001 tracked files**. The [CSV inventory](../reports/repository_review/file_inventory.csv) gives each file's path, role, description, byte size, SHA-256, Python definitions/imports where applicable, and review status. [Inventory metadata](../reports/repository_review/inventory.json) records the snapshot commit and conservatively reachable app import dependencies. New review files and later cleanup edits are outside that snapshot.

## 1. Root files — reviewed

| File | What it does | Why we keep it | Cleanup decision |
|---|---|---|---|
| `README.md` | The entry point for running and understanding the repository. | A new user should find the current app, model, data boundaries and reproduction commands here. | Replaced contradictory “latest” notices with one current account; linked historical details rather than mixing them with current status. |
| `.gitignore` | Controls which untracked files are excluded from commits. | Keeps environments, private uploads, scouting event logs and runtime MLflow stores local. It does not delete files or untrack already committed artifacts. | Removed six repeated rule lines and excess blank lines. Verified unchanged ignored-path behavior across 1,011 paths. |
| `.gitattributes` | Forces stable line endings for Python and fingerprinted report CSV/JSON files. | Windows checkout conversion previously caused model fingerprint errors. Model/data binaries keep their exact bytes. | Preserved. This is a reproducibility safeguard, not visual formatting. |
| `requirements.txt` | Pins direct project dependencies, such as pandas, scikit-learn, Streamlit and MLflow. | Explains what the project directly needs. | Preserved; no dependency change was justified by the root review. |
| `requirements.lock.txt` | Pins the tested dependency closure, including indirect dependencies. | Reproduces the environment more closely than installing only top-level packages. | Preserved. It is not a disposable duplicate of `requirements.txt`. Installed dependencies pass `pip check`. |
| `requirements-archives.txt` | Adds optional readers for retained RDS archives: pyreadr, rdata and xarray. | Needed for archive ingestion/full reproduction; ordinary app serving uses committed parquet/model files. | Preserved separately so its purpose remains explicit. |

## 2. Folder map — indexed, semantic review pending

| Folder | Tracked files at snapshot | What is inside | Review focus |
|---|---:|---|---|
| `.streamlit/` | 1 | App theme and browser telemetry configuration. | Contrast, responsive behavior, scout-facing presentation. |
| `.github/` | 1 | GitHub Actions workflow. | Full-suite hosted execution needs retained/private inputs and optional dependencies; local passing tests do not prove clean hosted CI. |
| `src/` | 45 | Application, source handling, preprocessing, features, models and event instrumentation. | Trace the active app first, then follow its data and model dependencies; distinguish compatibility paths before removing code. |
| `scripts/` | 42 | Collection, audits, experiment orchestration, notebook construction and verification commands. | Which commands reproduce current outputs versus earlier stages; source fingerprints and retained inputs. |
| `tests/` | 25 | Unit, data-contract, experiment and app integration tests. | Separate local-source prerequisites from portable tests without silently disabling meaningful checks. |
| `data/` | 161 | Raw responses, separate normalized source tables, processed versioned datasets and original legacy files. | Provenance, source rights, row grain, current serving use and immutable hashes. Original synthetic rows are retained evidence, not final training data. |
| `models/` | 14 | Serialized models and related metadata from different stages. | Identify the current Core artifact and historical comparisons; do not delete merely because the app no longer offers a selector. |
| `notebooks/` | 14 | Twelve analysis notebooks, one earlier Python notebook source and a folder marker. | Executed outputs versus blocked sections, source datasets and evidence for conclusions. |
| `reports/` | 662 | Coverage, dictionaries, diagnostics, figures, test runs, manifests and MLflow exports. | Most apparent duplication is versioned or portable experiment evidence; historical test reports are not live status. |
| `docs/` | 30 | Current instructions, stage reports and original author materials. | Current versus historical claims, links, repeated guidance and completeness of the TFM account. |

## 3. Application path to understand next

Start in `src/app/` with these files, in execution order:

1. `streamlit_app.py`: scout-facing controls, tabs, ranking, comparisons and group map.
2. `trained.py`: verifies and loads the current five-league model, gallery and history.
3. `collected.py`: the reusable service wrapper; applies frozen transforms to an observed-season gallery.
4. `scouting_views.py`: football labels and separate adjustable K-means groups.
5. `presentation.py`: theme, shortlist cards and filter reset behavior.
6. `europe_budget.py`: selects the retained five-league provisional identity candidates when available.
7. `budget.py`: joins reported dated valuations after ranking; unknown/ambiguous values are not budget-eligible.
8. `scenario_ui.py`: scout-facing requirements and scenario results.
9. `scenarios.py`: applies scenario constraints, cutoffs and analytical comparisons.
10. `fingerprints.py`: normalizes source-code line endings when verifying hashes.
11. `leagues.py`: earlier frozen La Liga-model/five-league-gallery serving retained for comparison; review tests/callers before deletion.
12. `__init__.py`: package marker.

The app currently uses the five-league **Core** model and six original expert styles. Exploratory groups reuse frozen training imputation/scaling and are fitted separately to the selected observed pool; changing their count does not refit the recommender. The map uses saved PCA coordinates. Market values remain optional provisional post-ranking context, not training features or transfer fees.

## 4. Cleanup boundaries and evidence

- Keep the existing folder structure and original author materials.
- Preserve raw data, provenance, source-use guards, historical experiment/model evidence and portable MLflow exports.
- A module absent from the app's import graph may still support ingestion, tests, notebooks or historical reproduction. Reachability alone is not a deletion criterion.
- Training source fingerprints and protected dataset/model hashes constrain refactoring. Verify their consumers before changing protected files; never rewrite expected hashes simply to hide a mismatch.
- Local `.venv`, `.jupyter`, `.pytest_cache`, `__pycache__`, MLflow runtime stores and private uploads are ignored runtime/input material, not extra tracked source folders. No runtime store or private data was deleted in this pass.

Root-pass verification: installed dependency consistency, unchanged Git ignore behavior, local README/document links and protected artifact hashes. The application and training code were not changed by this pass; no model refit or broad test rerun is required for these documentation/ignore-only edits. See `reports/repository_review/root_cleanup.json` for the recorded checks.
