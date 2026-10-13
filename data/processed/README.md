# Prepared datasets — shared by the app and notebooks

This folder is the only location for prepared data. There are no `review/` or `real/` subfolders and no separate app copies of FBref statistics or market values.

| Dataset | Purpose |
|---|---|
| fbref_player_club_seasons | Player statistics per club, league and season |
| fbref_player_seasons | Season history, combining compatible club stints within each league |
| fbref_scouting_gallery | Eligible player profiles for the six-style recommender |
| understat_shots | Cleaned shot events used by the app and notebooks |
| understat_player_seasons | Player-season shot, goal and expected-goal summaries |
| understat_quarantine | Invalid shot rows retained separately; currently empty |
| transfermarkt_profiles | Cleaned uploaded player profiles |
| transfermarkt_values | Dated reported market values; same table used in EDA and app budget screening |
| player_identity_links | Included provisional FBref/Transfermarkt identity proposals |

The eight source tables have a CSV version for inspection and a Parquet version for efficient execution. Large CSVs are compressed as `.csv.gz`. These are two formats of the same table, not different datasets. Identity proposals are retained as one Parquet file; the current CSV-cleaning pipeline validates their hash rather than claiming to recreate the earlier matching audit.

`manifest.json` records table paths, counts, hashes, cleaning decisions, identity-link provenance and the pinned model-input contract. Run `python -m src.pipeline` to rebuild source tables from the included raw CSVs. The pipeline checks the raw fingerprints, identity-link integrity and expected prepared model-input hashes. A changed dataset requires an explicit new training version, not silently replacing the served model's inputs.

The app and notebooks load these same files. Before consolidation, all common columns were checked against the removed frozen copies at tolerance 1e-12; statistics and rows were equivalent. The original trained model binary and historical lineage remain unchanged. Original training-file hashes are retained in the experiment manifest; current serving inputs have their own verified paths/hashes and dataset version.
