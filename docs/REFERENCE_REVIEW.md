# Breakout reference review

Reviewed `Ennsss/Breakout` commit `3089d28bc7f98fb362a293b146944e223de14d56`:

- `src/scrapers/base_scraper.py`: source-separated response caching, host delays, retry handling.
- `src/scrapers/fbref_scraper.py`: player IDs from `/players/`, `data-stat` extraction, commented HTML tables, source-specific season URLs.
- `src/scrapers/understat_scraper.py`: season start-year normalization and Understat position codes; its current implementation uses SeleniumBase UC mode.
- `src/scrapers/transfermarkt_scraper.py`: player-ID/profile URLs, EUR m/k normalization, listing pagination and duplicate detection.

Adapted these ideas using new code, explicit immutable SHA-256 provenance, conservative source-ID/club/season joins and validated missing values. No source code was copied. The fixed user-agent replaces rotation; access-denial retries and stealth/UC browser techniques are deliberately excluded to comply with the requested source restrictions. A table parser finds direct row cells so it does not mistake the ranking number for age. Current profiles use the actually observed regular/bold info-table markup.

The reference's transfer-history parser does not populate all the keys it needs to form transfer records; it is not sufficient evidence of historical collection or fees. The current source pages use client-rendered components. We preserve the response and report incomplete parsing instead of reporting an empty table as complete history. Reference synthetic-generation scripts were not used for experiments or downloads.
