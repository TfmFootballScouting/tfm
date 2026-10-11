> Collected-data preprocessing update: real retained archives are now cleaned and audited across seasons without changing the original folder structure or fitted model. See [mandatory features, cohorts and executed EDA](COLLECTED_PREPROCESSING.md).

# Uploaded football-data-webscraping trial — 11 October 2026

The ZIP was inspected as reference material, not as instructions overriding the user's requirements. Its README identifies `sahil-gidwani/football-data-webscraping`. Actual uploaded bytes have SHA-256 `8a47e63169071bcd8c1d2bc27929fb2c681e977bc6ee542a02d4f3b88a0afda1`; no Git commit is inferred from the ZIP. All 16 Python modules parse, but it bundles **no datasets**, season collectors, identity registry or tests. Syntax validation is not successful live collection.

| Route | Observed result | Consequence |
|---|---|---|
| FBref Segunda 2024/25 | Robots request returned HTTP 403 | Policy unknown; no statistical page requested |
| Understat La Liga | Robots disallows `/` | No league page requested; Segunda unsupported |
| Transfermarkt Segunda goalscorers 2024/25 | HTTP 200; 25 source-ID-bearing rows; 14 pages advertised | Historical basic-statistics route exists, but collection and ML use are restricted below |
| SofaScore | Proxy CONNECT to `www.sofascore.com/robots.txt` returned 403 | Environment network blocker; provider policy and coverage unverified |
| WhoScored | Proxy CONNECT to `1xbet.whoscored.com/robots.txt` returned 403 | Network blocker; uploaded example is an English cup match |
| Opta | Proxy CONNECT to `dataviz.theanalyst.com/robots.txt` returned 403 | Network blocker; examples provide current rankings, not historical player statistics |

The initial probe stopped on an uncaught WhoScored proxy exception. Observed responses/failures were retained and recorded; the reusable probe catches failures per source and continues. No successful endpoint response is claimed for the three network-blocked providers.

Transfermarkt's title and selected season both say 24/25. Headers expose appearances, assists, penalty kicks, minutes and goals. Only page one was fetched; goalscorer lists omit non-scorers. This is **not full Segunda coverage**. `Age (today)` is not historical age, and season labels do not supply historical publication/known-at timestamps. No player-statistics export, pagination, final experiment or model retraining was performed.

## Terms review changes Transfermarkt readiness

The correct site-policy link was found in the returned page footer: <https://www.transfermarkt.com/intern/anb>. An initial guessed terms URL returned 404. The correct Terms of Use returned 200, preserved with SHA-256 `7c46c0514a311f4bbb6af63b08c9be1d2011be06c22ceb8c30b4bed0cc3927d3`.

Section 11.1 states:

> The User is not permitted to access or copy the Digital Content using bots, spiders, screen scraping or other automated processes.

> The user is also prohibited from using the digital content for the training or development of artificial intelligence (AI), including language models, machine learning, neural networks or other AI systems.

Further automated collection has stopped. Previously acquired direct samples and worldfootballR Transfermarkt archives remain preserved as evidence; availability is **not permission for ML use**. No reviewed provider licence is present. Published archives and MIT/GPL software licences do not establish provider data-use rights. A licence or authorized export must permit the intended access and ML use; user confirmation alone cannot grant provider rights.

`src/data/source_rights.py` records the restriction. The collection client and sample command stop before Transfermarkt data requests. Missing Transfermarkt archive files and the provider-derived mapping cannot be downloaded by the archive command. Existing normalized valuation/transfer/mapping files carry `ml_use_status=restricted_pending_explicit_license`. Model fitting/transformation reject Transfermarkt source labels or the restriction flag. The existing model contains no Transfermarkt data and was not retrained.

## Reproduction and remaining work

Useful techniques include selectors, source IDs, response inspection and season verification. Our client adds policy checks, a fixed research user agent, caching, provenance, TLS verification and delays. Browser stealth, user-agent rotation, copied cookies and retries through denials were not run. The upload's unpinned requirements were not installed over the project's pinned environment; existing dependencies suffice.

The cloud draft adds exactly `www.sofascore.com`, `1xbet.whoscored.com` and `dataviz.theanalyst.com`, preserving existing domains. Saving the draft **does not apply network access**. Review/save settings and publish; after application, rerun the policy probe. Domain access does not establish permission or six-season coverage. Source restrictions still require appropriately licensed exports.

```bash
cd /workspace/tfm_futbol
# Retained-file checks only; no network requests:
.venv/bin/python -m scripts.uploaded_scraper_trial
# Only after network settings are applied:
.venv/bin/python -m scripts.uploaded_scraper_trial --probe-new-sources
.venv/bin/python -m pytest -q
```

The original ZIP is retained locally under ignored `data/raw/sources/uploaded_toolkit/` because it contains copied browser-cookie examples. Raw responses are content-addressed with append-only provenance. Original datasets and the current model are unchanged.

Evidence: `reports/uploaded_scraper_trial.json`, `reports/uploaded_scraper_access.json`, `reports/uploaded_scraper_coverage.csv`, and `reports/uploaded_scraper_tests.xml`. **33 tests passed**, none failed/skipped; dependency consistency passed. These verify guards and existing application behaviour, not completed data acquisition. Full real Segunda coverage and historical valuation/transfer validation remain blocked.
