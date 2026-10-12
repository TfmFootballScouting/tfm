# Raw source inputs

The actual untouched inputs are stored locally in `sources/`, with content-addressed filenames. They are not the synthetic `players_raw.csv` from the original demonstration, and are not copies of cleaned output renamed as raw data.

`sources_manifest.json` identifies six FBref category archives and the La Liga Understat shot archive used by the application, plus four optional Understat archives and four private uploaded valuation/identity files. It records original providers, secondary repositories, exact URLs where available, original acquisition timestamps, SHA-256 checksums and file sizes. Original retrieval timestamps refer to the preserved snapshot, not a future download.

```bash
# From the repository root; uses Python's standard library
python -m src.scraping.raw_inputs --verify
# Restore the seven primary raw archives from their recorded secondary release URLs
python -m src.scraping.raw_inputs --download
# Include the four optional shot archives
python -m src.scraping.raw_inputs --download --include-optional
```

Missing files make verification fail. A changed release asset, download failure or checksum mismatch never causes an alternative or synthetic dataset to be substituted. Existing corrupt files are not overwritten. Optional private uploads have no verified download URL and must come from the original user-supplied files.

The seven primary archives currently occupy approximately 92 MiB. Raw provider-derived archives remain ignored by Git because their original recorded rights status permits local research but does not establish redistribution rights. A clone contains this provenance manifest and restoration utility, rather than republishing those archives. Existing local raw inputs were verified and preserved in this workspace.

Raw restoration alone does not rerun preprocessing or retrain the model. This branch serves existing verified artifacts; the complete preparation and training workflow remains on `improve/reproducible-scouting`.

See [data sources and lineage](../../docs/DATA_SOURCES.md) for dataset usage, joins, coverage and limitations.
