> Latest full run: [five-league preprocessing, EDA, model refits and validation](FIVE_LEAGUE_FULL_PIPELINE.md). Three new trained models and50 real-observation scenarios are complete; price identities remain provisional. Earlier reports describe earlier versions.

> Latest application: [five-league scouting and UI update](TOP_FIVE_LEAGUES.md). Real Premier League, Bundesliga, Serie A and Ligue 1 galleries are now included; models remain frozen La Liga-trained. Earlier counts below describe earlier stages.

# First-submission execution and review

The current submission works in the retained cloud workspace, with its verified raw datasets and existing model artifacts. A clean Git clone alone does not contain every private/ignored provider-derived file. Do not replace absent real data with generated samples or silently skip data-dependent tests.

## Execute from the repository root

Python 3.12 is required. Use the prepared `.venv` or install `requirements.lock.txt` into a Python 3.12 environment. Run `python -m pip check` in that environment. Retain private raw datasets, receipt files, checksum manifests and evaluated model artifacts before attempting the following commands:

```bash
.venv/bin/python -m pytest -q --junitxml=reports/submission/tests.xml
.venv/bin/python -m streamlit run src/app/streamlit_app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Start MLflow in another terminal, from the same root:

```bash
.venv/bin/python -m mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 127.0.0.1 --port 5000
```

With both services running, audit existing outputs without retraining:

```bash
.venv/bin/python -m scripts.submission_audit
```

To regenerate the scenario analysis from retained observations:

```bash
.venv/bin/python -m scripts.scouting_scenarios
.venv/bin/python -m scripts.scenario_notebook
.venv/bin/python -m scripts.verify_scouting_scenarios
```

These commands never create fallback synthetic data. Source-use and checksum failures must be diagnosed rather than bypassed. They do not download restricted providers, approve identities or establish historical publication.

## Review order

1. Read [the current completion report](COMPLETION_REPORT.md), including limitations.
2. Review source coverage, raw receipts and the dictionaries before interpreting model results.
3. Review notebooks 05–08 for preprocessing, chronological evaluation and PCA/cluster robustness; notebook 09 for practical scenarios.
4. Open the app: use Core, select an observed season, inspect all six styles, a price-screened shortlist, similar profiles and history. Execute an illustrative scenario and inspect the exclusion funnel and sensitivity.
5. Compare MLflow exports with the recorded real dataset/model versions. No application or scenario phase claims a new model experiment.

A reported value ceiling is a screening constraint. It does not establish the real transfer fee, total cost, official club budget or historical affordability. App exercise is functional verification; it is not validation of actual signing success. Formal process discovery requires genuine sessions and decisions, not test logs.

## Portability boundary

Current-instance tests and checksum verification are completed. Remote CI, clean-checkout restoration and cloud publication/restoration are unverified. Keep private uploaded data and local-only commits in the prepared workspace/snapshot; do not publish provider rows simply to make CI pass. The saved GitHub Actions workflow has not been validated with these private assets in a remote runner. Live processes must restart after environment restoration.

## Windows source fingerprint correction

Git on Windows can convert Python source from LF to CRLF. The original source-byte fingerprints then reported `Style definition fingerprint changed` despite identical code. The collected-model loader now normalizes CRLF to LF only when checking Python source; model/dataset checksums remain byte-exact, and actual source edits are still rejected. `.gitattributes` also requests LF Python files for subsequent checkouts. This was tested with CRLF copies of all five verified source files for both real models; native Windows execution remains unverified here.

Stop Streamlit, run `git pull --ff-only` on `improve/reproducible-scouting`, then restart `python -m streamlit run src/app/streamlit_app.py`. No retraining or dependency change is required. If the message persists, inspect `git diff -- src/config.py src/features/styles.py src/models/collected.py src/models/recommend.py src/data/source_rights.py` for real local changes rather than bypassing checks or regenerating artifacts.
