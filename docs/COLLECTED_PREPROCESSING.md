# Collected data: feature contract, cleaning and EDA

The existing folder structure is preserved. Processing extends `src/preprocessing/`, `src/features/`, `src/scraping/` and `scripts/`; results use the existing `data/processed/real/`, `reports/`, `docs/` and `notebooks/` directories. The raw files, current `players.parquet`, SQLite database and fitted model remain intact. New processed filenames start with `collected_`, alongside identity-review tables.

## Mandatory project features

| Requirement | Fields | Treatment |
|---|---|---|
| Identity/provenance | source_player_id, entity_id, observation_id, player_id, player, club, league, season, source, provenance, input hash | Required keys validated; IDs stable across reruns and row order |
| Scouting filters | position, age, minutes, appearances | Source positions retained; primary position based on stint exposure; unknown age stays unknown |
| Core performance | gls_p90, ast_p90, ga_p90, sh_p90, sot_p90, crs_p90, int_p90, tklw_p90, fls_p90, fld_p90 | All ten columns preserved; unknown remains missing; G+A excluded from candidate model features because it duplicates goals/assists |
| Budget scenarios | market_value_eur, EUR currency, valuation_date, valuation_known_at, valuation_source | Required for budgets, but not available as verified historical attachments; no estimated prices |
| Player profiles | nationality, birth year/DOB, height, foot | Normalize source units; birth year is not DOB; no unreviewed cross-source enrichment |
| Additional measurements | xg_p90, xag_p90, xa_p90, passes/touches/key passes/take-ons per 90, pass completion percentage | Source definitions preserved; xAG is not substituted for missing xA |

The machine-readable contract is `reports/mandatory_features.csv`, with observed coverage by season in `reports/mandatory_feature_coverage.csv`. A complete schema does not imply every feature is measured for every player. True pressing/transition metrics and goalkeeper-specific performance are not in the selected archives; existing broad style weights are statistical proxies, not validated tactical roles.

## Results from real retained files

- 3,443 FBref club-stint rows become **3,378 player-season observations**, covering 1,451 source player IDs. There are 65 multi-club seasons.
- The existing 450-minute floor yields **1,975 historical outfield baseline candidates**. There are **1,577 candidates with all ten core features**; only one is from 2024/25.
- **45,847 Understat shot-event records** contain 45,699 attacking shots and 148 own-goal events. There are 2,769 shooter/club/season summaries; appearances, minutes, assists and xA cannot be inferred from shots.
- **2,018 Transfermarkt valuation/profile records** are audited separately: 93 unknown values, 2,016 parsed DOBs and 1,954 parsed heights. Historical valuation effective/knowledge dates are absent.
- **1,934 source transfer records become 1,933 after removing one exact duplicate.** The 1,882 potential movement groups are not uniquely dated verified transfers. There are 1,239 unknown fees and 351 numeric zeros whose free-transfer semantics are unverified.
- The saved **25-row Segunda 2024/25 goalscorer sample** is parsed offline and retained separately. It has no complete player universe, verified stint scope or historical age. The 50 current market records and two current profiles remain separate from history.
- **2,371 cross-source identity candidates**, including three birth-year conflicts and 67 ambiguous pairs, are queued for review. No name-only links are approved or merged.
- Five low-exposure player-season outliers are flagged; none enters the historical baseline candidate dataset. Three source ages remain missing. No values are winsorized, globally imputed, scaled or learned in this phase.

## Cleaning decisions

1. Normalize empty source strings, units and numeric types. Negative/nonfinite measurements become unknown and are counted. No synthetic/unknown-source observations enter FBref preprocessing.
2. Remove only exact duplicates. Conflicting FBref ID/club/league/season keys fail explicitly. Preserve multiple source transfer records and conflicting contextual observations for review.
3. Keep club stints and sum compatible totals before the minutes floor. A missing statistic in any stint makes that season total missing. Rates use total recorded minutes/90, not the average of stint rates. Multi-club observations list all clubs without inferring the current club.
4. Preserve the archive's exposure audit: 1,329 auxiliary category joins had inconsistent periods and were nulled upstream. Do not backfill defensive totals from other seasons or divide partial-period counts by full-season exposure.
5. Reconcile Understat's `h_a` and `home_away` schema variants before identifying the shooting club. Own goals do not count as attacking shots/goals/xG. Provider timestamps retain unspecified timezone.
6. Preserve source estimates separately. FBref and Understat goals/xG are not summed together. Upstream mapping IDs and exact names are candidate evidence, not automatic identity approval.
7. Keep source-use flags on Transfermarkt context and mappings. This offline audit performs no collection or model fitting. Unknown historical dates, profile timing and transfer fee semantics remain explicit.

## Future experiment cohorts

The offensive baseline has train 2020/21–2022/23, validation 2023/24 and holdout 2024/25. The full-core proxy has train 2020/21–2021/22, validation 2022/23 and holdout 2023/24, because 2024/25 defensive coverage cannot support representative full-core testing. The latter labels 2024/25 as sparse monitoring. Both exclude partial 2025/26 from historical experiments. These flags prepare future experiments; none was fitted here. Unknown archive publication times still prevent strict historical as-of claims.

Fit imputation, scaling, PCA and K-means only within the chosen training cohort later. Do not tune using holdout outcomes. Exclude redundant G+A from the feature vector. Keep goalkeeper rows for inventory, but use goalkeeper-specific features before building goalkeeper recommendations. No complete real La Liga–Segunda comparison or dated historical budget/transfer-success validation is supported yet.

## Reproduce

```bash
cd /workspace/tfm_futbol
.venv/bin/python -m src.preprocessing.collected
MPLCONFIGDIR=/tmp/tfm-matplotlib .venv/bin/python -m scripts.collected_eda
.venv/bin/python -m pytest -q
```

Execute `notebooks/05_collected_data_preprocessing.ipynb` with the existing `tfm-python` kernel. It contains data description, missingness, distributions, outliers, correlations, position/season comparisons, source audits and written interpretation. Its figure files and tabular evidence are in `reports/`. The earlier notebooks retain their original legacy-model scope.

`reports/collected_preprocessing.json` pins input/output SHA-256 values, transformation code hashes, original archive provenance, dataset version, Git commit, source-dirty status and split parameters. `reports/collected_data_dictionary.csv` enumerates every exported field and dtype. `reports/collected_eda.json` records executed descriptive findings; these are not model evaluation metrics.

For reviewed identities, provide `data/processed/real/identity_matches_reviewed.csv` with columns `left_source,left_id,right_source,right_id,reviewer,evidence,reviewed_at`. An absent ledger means no approvals. The validator rejects missing evidence, conflicting birth years and non-bijective mappings; it never overwrites an existing ledger. Review candidates are readable in `reports/collected_identity_candidates.csv`.

## Name plus supporting features: identity trial

Run `.venv/bin/python -m scripts.identity_resolution` to reproduce the offline trial. It reads checksum-verified collected tables and the pinned upstream mapping; no raw inputs or original source-separated outputs are overwritten. New outputs stay in the existing directories:

- `data/processed/real/identity_match_trials.parquet`: candidate evidence for each source pair and season cutoff.
- `data/processed/real/identity_crosswalk_proposed.parquet`: reciprocal, unambiguous proposals with stable `canonical_player_id` values.
- `data/processed/real/collected_identity_join_preview.parquet`: FBref club-season rows with separately prefixed Understat and Transfermarkt context.
- `reports/identity_resolution.json`, `identity_join_coverage.csv`, `identity_match_trials.csv` and `identity_resolution_dictionary.csv`: provenance, coverage, review evidence and field dictionary.

Player names are normalized for accents, case, punctuation and whitespace. All observed name variants at/before a season cutoff remain candidate aliases. Candidate pairs are blocked using exact names, shared league/club/season history, or the existing FBref–Transfermarkt mapping. Explicit club spelling aliases are listed in `src/data/identity.py`; unknown club names are not guessed.

The supporting features available on both sides determine the decision. Our Understat shooter extract has no DOB or birth year, so exact name plus shared league/club/season supports a proposal. Transfermarkt DOB can be compared with FBref birth year; a year mismatch or inconsistent source profile prevents a proposal. Names with minor spelling differences need similarity of at least 0.92, multiple name tokens with a shared exact token, birth-year agreement and club-season overlap. Current age, changing club membership and approximate birth year derived from age are never immutable player keys. Position/height/nationality are not fabricated where the other source lacks comparable fields.

The evidence score assigns 50 points for an exact normalized name (35 for a supported near name), 20 for club-season overlap plus five for at least two overlaps, 20 for birth-year agreement and five for an upstream ID mapping. These are transparent rules, not calibrated probabilities or measured matching accuracy. A proposal must have the required supporting features, be the reciprocal best match and exceed each competing candidate by at least ten points. Ties and weak evidence stay in the review queue. Profile conflicts remain visible. A changing mapping is flagged from the season when the change becomes visible; it never changes earlier snapshots using future evidence.

The person key is `canonical_player_id = fbref:<FBref ID>`. Name and supporting features resolve identity; they do not form a fragile permanent concatenated key. The crosswalk maps Understat/Transfermarkt IDs to this person ID. Names, clubs and seasons can change without changing the key. Performance joins use the mapped player plus normalized league, season and club, with explicit cardinality validation. Duplicate/conflicting context rows are excluded from the preview instead of arbitrarily taking the first row. Birth year is not a full DOB match.

All proposed links remain `provisional_not_reviewed`. The preview disables model/scouting eligibility and budget eligibility, and model fitting/transformation rejects unreviewed identity links. It does not update the existing reviewed identity ledger or retrain the model. Each source retains its own goals/xG columns; values are never summed or used to fill another source without a separate justified decision. Transfermarkt dates and source-use flags remain explicit. Historical publication/profile dates are unknown, so season-bounded matching is not proof of strict historical as-of availability. Review a representative sample, collisions and unmatched players before accepting the crosswalk; no accuracy figure is claimed without reference labels.

### Executed trial results

At the latest 2025/26 evidence cutoff, the rules produce **977 FBref–Understat** and **803 FBref–Transfermarkt** supported identity proposals. All 977 Understat proposals use exact normalized names plus context; the extract supplies no birth-year evidence. Of the 803 Transfermarkt proposals, 790 have exact normalized names, 13 use supported spelling variants, 802 have birth-year agreement and 795 also occur in the upstream mapping. These are evidence counts, not verified precision or recall.

The preview preserves all **3,443 FBref club-season rows**: **2,317** have joined Understat context, **1,420** have joined Transfermarkt context, and **1,099** have both. Transfermarkt context joins are limited to the retained 2020/21–2022/23 profile seasons; later performance rows do not receive old/current market values. There are zero approved links. Review queues contain 90 unresolved Understat and 122 unresolved Transfermarkt candidate pairs at the latest cutoff, plus two Understat and 38 Transfermarkt conflict pairs. Conflict counts include same-name different people and inconsistent source profile histories; they are not necessarily erroneous source observations. No observed supported mapping switches across cutoffs were found.
