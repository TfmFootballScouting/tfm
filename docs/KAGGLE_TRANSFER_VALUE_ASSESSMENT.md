# Kaggle transfer-value dataset: uploaded files now inspected

Candidate: [Football Transfer Value Intelligence 2024](https://www.kaggle.com/datasets/kanchana1990/football-transfer-value-intelligence-2024), uploaded by `kanchana1990`.

**Update:** The user subsequently uploaded `archive.zip`; local inspection is completed. See [the executed audit, exact coverage and remaining issues](KAGGLE_VALUE_AUDIT.md). The blocked-access account below describes the earlier online attempt, not the current local inspection status. Existing recommendation-model integration remains pending separately.

## Actual access result

On 2026-10-11, public page and dataset API requests failed at the cloud HTTPS proxy with a tunnel `403 Forbidden`. This was a cloud destination-policy failure, not a verified Kaggle authentication or dataset-permission failure. No page description, licence, file schema, rows, values, dates or coverage have been inspected. The title alone does not establish a 2024 observation date or historical coverage. See `reports/kaggle_transfer_value_assessment.json` for the exact requests and preserved model/report hashes.

The saved environment network draft adds `www.kaggle.com`, preserving all six existing explicit domains and package-manager presets. Saving the draft does not apply it to the running environment. A bounded check after saving still failed. Apply the network change through environment settings before retrying. Do not bypass the proxy. If a permitted download later redirects to another host, record and review that destination rather than guessing a wildcard allowlist. Alternatively, a user-provided dataset ZIP/CSV and its metadata/licence can be inspected locally.

## Potential project use, conditional on inspection

- Dated market assessments could supply valuation observations and, where genuinely available before a decision, budget filtering. A market assessment is not a transfer fee.
- Genuine transfer events with dates, origin/destination clubs and fees could support historical transfer analysis. A current club field alone cannot establish a transfer event.
- A price-estimation model would require real labels, sufficient independent matched players, authorised use, and an evaluation split that respects label and feature availability. Do not train or report valuation accuracy before these requirements are verified.
- Profile attributes could help identity matching. Source player IDs are preferred; names plus birth date/year and club context generate reviewable candidates, not automatic identity approval.

This dataset does not yet resolve missing prices, Segunda coverage or any model feature. No integration, price attachment, identity approval, model retraining or synthetic replacement has occurred.

## Admission checks before integration

1. Preserve the original ZIP/files, dataset version, download URL, UTC retrieval time, metadata/licence and SHA-256 checksums under the existing `data/raw/sources/` structure. Establish the original provider and data-generation method; the Kaggle host and uploader's licence declaration alone do not establish provider reuse rights or real-data authenticity.
2. Inspect all tables and produce per-source, league, season and category coverage. Separate observed values, uploader estimates and missing values. Check currency/scale, price versus fee semantics, duplicate observation keys, inconsistent dates, repeated snapshots and selection bias. Never interpret a missing amount as zero.
3. Keep this source separate from existing FBref/Understat/Transfermarkt tables. Create a data dictionary and reviewable cross-source identity candidates. Retain source IDs and use our stable canonical person key only after review; statistical observations additionally require season and club context.
4. Require explicit valuation-effective dates and credible availability evidence for historical budget decisions. Retrieval in October 2026 proves availability then, not before a 2024 scouting decision. Do not invent dates from a dataset title, season, contract expiry or transfer date. Quarantine future prices and features from historical experiments.
5. Retain applicable source-use flags. If the original provider is Transfermarkt, the existing provider restriction remains unless a reviewed licence supports the intended use. Do not relabel Kaggle copies as an unrestricted independent source.
6. Only after these checks, evaluate whether coverage materially improves the current data. Document blocked and unverified fields and preserve existing frozen experiment artifacts.

The next inspection can proceed once the network setting is applied or the files and provenance metadata are available locally. Existing recommendation-model integration remains pending separately.
