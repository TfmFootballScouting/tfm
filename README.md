# ScoutIQ — minimal runnable application

This branch keeps the original project layout and the files needed to serve the current scouting application. The complete data acquisition, cleaning, experiments, notebooks, tests and TFM documentation remain on [improve/reproducible-scouting](https://github.com/TfmFootballScouting/tfm/tree/improve/reproducible-scouting), based on research commit `a29e192933e70218de53d658e1b72b59844f751e`. No retraining is required to run this branch.

## Run

Use Python **3.12**, from the repository root:

```bash
git clone --branch minimal/scoutiq-runtime --single-branch https://github.com/TfmFootballScouting/tfm.git
cd tfm
python -m venv .venv
```

Activate the environment:

```bash
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Then:

```bash
python -m pip install -r requirements.lock.txt
python -m pip check
python -m streamlit run src/app/streamlit_app.py
```

`requirements.txt` lists direct runtime dependencies. `requirements.lock.txt` pins their resolved dependencies; platform-specific Streamlit dependencies use environment markers. MLflow, Jupyter and acquisition tools are unnecessary for serving this app.

## Files and functionality

```text
data/
  raw/                      # original layout; raw archives remain on research branch/local storage
  external/                 # original layout
  processed/real/           # real player gallery, player history and La Liga shots
models/real/                # frozen five-league model and checksum/provenance manifest
src/
  app/                      # Streamlit UI and verified data/model loaders
  data/                     # identities, source-use rules and checksums
  features/                 # six original tactical styles
  models/                   # recommender and exact training source integrity references
  preprocessing/            # exact preprocessing source integrity reference
  process/                  # genuine local scouting activity log
  scraping/                 # preserved original folder
notebooks/                  # original folder; notebooks remain on research branch
docs/                       # original folder; TFM documentation remains on research branch
tests/                      # original folder; research tests remain on research branch
```

The application supports six tactical styles; selecting one or several of La Liga, Premier League, Bundesliga, Serie A and Ligue 1; recommendations; player comparison; player development; and selectable exploratory clusters with a PCA graph. Recommendations use complete available galleries through **2023/24**, rather than pretending the source provides a current 2026 roster. Shot analysis is separate from recommendations and does not imply verified cross-source player matching.

The supplied model, gallery, history and shot dataset are unchanged real-data artifacts from the research branch. `models/real/runtime_manifest.json` records their original SHA-256 fingerprints, dataset version and research commit. Exact training/preprocessing source files are retained because the loader checks their fingerprints; training scripts, evaluation exports and duplicate models are excluded. The full branch holds source coverage, provenance records, validation limitations and original acquisition snapshots. Existing dataset rows retain their source/provenance fields; this branch performs no downloads or synthetic fallback.

## Optional local data

A clean clone runs without private valuation data. Budget screening appears only when the following locally retained files match the manifest:

- `data/processed/real/collected_salimt_values.parquet`
- `data/processed/real/europe_review_candidates.parquet`

These are provisional reported market assessments, with unverified cross-source identities and currency assumptions; they are not predicted prices, fees or proof of historical affordability. They never enter recommendation model training.

La Liga shot data is supplied. Additional four-league shot analysis needs the local `data/processed/real/four_league_clean_shots.parquet` matching the manifest. Obtain/prepare optional data using the workflows on the research branch, observing source access and licensing requirements. Optional provider-derived files are ignored by Git and are not published by this branch. Missing optional files hide their controls or show an availability message; a checksum mismatch is an error and must be investigated.

Observed scouting sessions write locally to ignored `data/events/scouting.jsonl`; `TFM_EVENT_LOG` can select another path. No simulated event log is bundled. Keep all source attribution and restrictions when using the retained artifacts. This application extends the original [tfm_futbol](https://github.com/valen28030/tfm_futbol) project.
