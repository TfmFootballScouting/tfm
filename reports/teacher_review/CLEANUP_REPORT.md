# Clean teacher-review submission

Branch: `review/teacher-submission`. The previous archive-style package at `252e030` remains recoverable in Git history. This branch now omits 904 obsolete or duplicate tracked files.

## Retained structure and content

- `data/raw/`: 15 real source CSVs, acquisition/export provenance and hashes, raw README.
- `data/processed/`: the eight source-separated prepared CSV/Parquet tables and six frozen app/gallery/value inputs.
- `docs/`: original teaching documents and current source flow, dictionary, teacher status, expert protocol, MLflow screenshots and cloud worksheet.
- `models/`: one Core serving binary and the two current comparison models; metrics and valuation integrity manifest. No historical/synthetic binaries or duplicate exported models.
- `notebooks/`: six executable notebooks: FBref/Understat/Transfermarkt EDA, current model analysis, groups, expert validation.
- `src/app`, `src/models`, `src/preprocessing`, `src/scraping`, `src/tests`: actual app/pipeline/model/original scraper implementations and current tests. Required feature/identity/process helpers remain under `src`.
- `scripts/`: seven current EDA/dictionary/training/cost/expert/alignment entry points. Acquisition and optional archive export code live under `src/scraping`.
- `reports/`: current real model evaluation and final verification only. MLflow manifests reference single-copy artifacts with exact SHA256.
- Runtime/research locks, optional archive-reader requirements, Streamlit config and CI.

## Removed

Old collected/enrichment models, synthetic/mixed samples, unused Kaggle/transfer-history stages, transfer-likelihood and scenario notebooks/code, historical stage reports, abandoned scraper trials, redundant copies of evaluation/model artifacts, obsolete tests and the root test-cache folder. Ignored original raw archives/receipts were moved outside the project checkout, preserving their bytes. Raw CSVs/provenance, original DOCX and all three current model binaries were verified unchanged.

## Executed verification

- Complete retained suite: 61 passed. Tests now use only bundled clean-submission inputs; CI runs the complete retained suite.
- `python -m src.pipeline`: rebuilt all eight real prepared tables; verified frozen-gallery numerical parity.
- All six retained notebooks re-executed successfully. Human-analysis notebook reports ratings pending.
- Separate Core training/evaluation from the bundled raw CSVs with two bootstrap trials completed. This is execution verification, not a replacement for the original 30-trial evaluation. Frozen served model unchanged; new outputs separate.
- Optional RDS archive-to-CSV export reproduced all source CSV hashes without changing their bytes.
- Actual browser group and shot graphs rendered without JavaScript errors.

Fresh checkout: 61 tests passed; all 16 CSV/Parquet outputs reproduced byte-for-byte. Browser feedback saving and two searches within one request passed with no JavaScript errors. See `verification.json` and `tests.xml`.

## Still pending

Independent expert ratings, genuine organizational sessions, official AWS/ECB evidence (network returned HTTP 403), native Windows verification, provisional player-identity and assumed currency checks. No successful-signing or transfer prediction claims were added.
