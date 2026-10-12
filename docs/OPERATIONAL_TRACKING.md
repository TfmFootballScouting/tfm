# Operational scouting tracking

`src/process/store.py` implements a separate SQLite database with `requests`, `events` and `feedback`. Default: `data/operational/scouting.sqlite`. `TFM_OPERATIONAL_DB` overrides it. `TFM_EVENT_LOG` isolates JSONL and derives an adjacent SQLite file when set; explicit test log paths isolate their database too. MLflow's `mlflow.db` is never used for operational decisions.

A request UUID is `scouting_request_id` in SQLite and `case_id` in exported events. Explicit searches reuse the request; **Nueva solicitud de scouting** starts a new request at the next search. Filter previews remain unlogged. Search events contain filters and a declared participant alias; ranking/review events contain FBref entity IDs. These IDs are source identifiers, not cross-source identity proof. Feedback stores player, shortlist/reject/needs-review decision, 1–5 usefulness, reason and UTC timestamp. A feedback entry is a scouting judgment, not an observed transfer outcome.

SQLite transactions enforce request references and valid decisions. The DB event record is written before the backward-compatible JSONL append. A filesystem failure may leave the JSONL mirror incomplete; SQLite is the authoritative operational record. Export it with:

```python
from src.process.store import export_events
export_events('data/events/operational_export.jsonl')
from src.process.events import discover
edges, cases = discover('data/events/operational_export.jsonl')
```

Current discovery uses directly-follows transitions, waiting times and durations. Its `complete` flag means the last event is `decision_recorded`, not that an authenticated business approval or a signing occurred. Iterative searches and multiple player decisions can continue within a request. There are no genuine organizational sessions supplied yet, so no findings about real scouts' delays or process efficiency are claimed. Automated checks use separate local paths; do not use them as organizational evidence.

Aliases are self-declared; authentication, authorization, consent/retention administration, concurrent multi-instance deployment and managed database backups are future production work. Participant records are ignored by Git and remain local. Back up the database consistently before upgrades; this prototype does not deploy automatic backups. Share anonymized aggregates only with participant consent.
