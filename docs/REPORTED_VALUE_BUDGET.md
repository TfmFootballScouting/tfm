Current application update: [Core and offensive serving](COLLECTED_APPLICATION.md) supersedes the legacy-default coverage snapshot below. Reported-value screening remains enabled; current coverage is in `reports/collected_application_verification.json`.

# Budget screening with reported market values

The application now attaches uploaded, dated market values to recommendation results and optionally filters by a maximum amount. This is the user's requested local screening workflow: it does not estimate missing prices, retrain a model, verify player identities, or claim historical transfer-budget validation.

In the sidebar, enable **Filtrar por valor de mercado**, choose **Fecha límite del valor reportado**, and set **Presupuesto máximo (M€)**. The default date is the latest date recorded in the uploaded history, **2025-09-11**. The player statistics still correspond to the displayed observed season; the valuation date is separate. Changing a filter refreshes the shortlist automatically. The result table shows the reported EUR amount, value date, source, availability and provisional identity status. The CSV download retains source IDs, match evidence, dates and restriction flags as well as the unscaled tactical scores.

The existing model ranks eligible football profiles first, without price fields. The price filter is applied to the complete ranked candidate set **before** truncating to the requested shortlist size. No valuation field enters model fitting, transformations or affinity scores. Model artifacts and all previous audited datasets remain unchanged. Outputs carrying the new provider values retain their source-use restriction and are marked ineligible for model use.

Prices use the latest reported event on/before the selected date. The latest event is selected before checking validity: a latest zero/unknown cannot silently inherit an older positive amount. Unknown, unmatched, nonpositive and invalid amounts are excluded when budget screening is enabled. A reported zero remains explicitly ambiguous, never a verified free transfer. Without the filter, unknown values and their statuses remain visible.

For the current legacy application dataset, exact normalized name + club + season + league bridges to a unique canonical FBref observation. Only existing one-to-one upstream ID proposals supported by normalized-name and birth-year agreement supply a source player ID. Ambiguous keys, conflicting persons and unsupported candidates are excluded. These are **provisional links**, labelled in the application and CSV; enabling this local screen does not create identity approvals.

The underlying uploaded table contains **901,429 valuation records**. At the default date, **349 of 420 application observations** have a supported provisional link; **338 have positive reported values**, **11 have ambiguous reported zero**, and **71 remain unmatched**. Coverage is not claimed for every player. See `reports/budget_screening.json` for observation/person counts and executed verification.

Market values are provider assessments, not agreed transfer fees. Original publication dates are unknown, so effective-date selection does not demonstrate that a value was available at a historical decision time. Historical-budget eligibility remains false. The provider's existing source-use restriction is retained; no model-use licence or identity approval is inferred from this display/filter feature. The user explicitly requested reported-value screening with provisional labels; the stricter historical validation importer and all model-use guards remain unchanged.

Reproduce from the repository root, with the retained raw/normalized uploaded files available:

```bash
.venv/bin/python -m streamlit run src/app/streamlit_app.py --server.headless true
.venv/bin/python -m pytest -q --junitxml=reports/budget_screening_tests.xml
.venv/bin/python -m scripts.budget_screening_audit
```

The audit uses the already-running application's health endpoint on port 8501. Verification executed **94 tests, all passed**, including the real-data application budget workflow, filter refresh, date bounds, zero handling, duplicate rejection and model-feature preservation. The existing pipeline/data/model checks also passed. All changes remain on the separate development branch; no data or code was pushed to main.
