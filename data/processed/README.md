# Prepared data

`review/` contains source-separated CSV (large tables use `.csv.gz`) and Parquet outputs reproducible from bundled raw CSVs with `python -m src.pipeline`. Its manifest records rows/checksums and verifies that rebuilt FBref gallery keys and numerical model features match the actual frozen gallery. Rebuilding does not overwrite the served model or real dataset files.

`real/` retains the evaluated model's actual Parquet galleries/history, source-specific shots and dated valuation inputs. Streamlit verifies their original fingerprints. Earlier files under other names belong to historical stages, not the current final dataset; consult the review README before using them.

Unknown counts remain unknown. Cross-source identity proposals are separate and provisional; Understat is not merged into recommendation fitting. Transfermarkt values are applied only after ranking, with dates/currency caveats. No synthetic row enters the review pipeline.
