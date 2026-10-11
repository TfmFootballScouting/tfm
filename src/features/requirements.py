"""Project feature contract; required schema does not mean invented observations."""
from src.config import FEATURE_COLS, PLAY_STYLES

IDENTITY_COLUMNS = ['source_player_id', 'entity_id', 'observation_id', 'player_id', 'player',
                    'team', 'league', 'season', 'source', 'provenance_status',
                    'source_snapshot', 'input_snapshot_sha256']
CONTEXT_COLUMNS = ['pos', 'pos_main', 'age', 'nation', 'minutes', 'mp', 'birth_year',
                   'date_of_birth', 'height_cm', 'foot']
BUDGET_COLUMNS = ['market_value_eur', 'currency', 'valuation_date', 'valuation_known_at',
                  'valuation_source']
BASE_COUNTS = ['gls', 'ast', 'ga', 'sh', 'sot', 'crs', 'int', 'tklw', 'fls', 'fld']
EXTRA_COUNTS = ['xg', 'xag', 'xa', 'passes_completed', 'passes_attempted', 'key_passes',
                'touches', 'successful_take_ons']
ALL_COUNTS = BASE_COUNTS + EXTRA_COUNTS
EXTENDED_FEATURES = [f'{c}_p90' for c in EXTRA_COUNTS] + ['pass_completion_pct']
MODEL_CANDIDATE_FEATURES = [c for c in FEATURE_COLS if c != 'ga_p90'] + EXTENDED_FEATURES
STYLE_MIN_MEASURED_WEIGHT = 0.60


def feature_contract():
    rows = []
    for columns, role, unit in [(IDENTITY_COLUMNS, 'required_identity', 'identifier/text'),
                                (CONTEXT_COLUMNS, 'required_scouting_context', 'field-specific'),
                                (FEATURE_COLS, 'required_core_performance', 'events per 90 minutes'),
                                (BUDGET_COLUMNS, 'required_for_budget_scenarios', 'EUR / ISO date / source'),
                                (EXTENDED_FEATURES, 'additional_performance', 'per 90 / percentage')]:
        for column in columns:
            rows.append(dict(feature=column, role=role, unit=unit,
                             model_candidate=column in MODEL_CANDIDATE_FEATURES,
                             missing_policy='retain unknown; never fabricate or fill with zero',
                             note='Derived G+A retained for reporting; excluded from fitting' if column == 'ga_p90'
                             else 'xAG and xA are different provider quantities' if column in ('xag_p90', 'xa_p90')
                             else 'Both effective date and known-at date required' if column in BUDGET_COLUMNS else ''))
    return rows


def style_coverage(players):
    """Measured proxy coverage per row; this does not validate real tactical fit."""
    rows = []
    for (season, position), group in players.groupby(['season', 'pos_main'], dropna=False):
        for style, definition in PLAY_STYLES.items():
            weights = definition['weights']
            fraction = sum(group[c].notna().astype(float) * abs(w) if c in group else 0
                           for c, w in weights.items()) / sum(abs(w) for w in weights.values())
            rows.append(dict(season=season, position=position, style=style, rows=len(group),
                             measured_weight_mean=float(fraction.mean()),
                             rows_above_60pct=int((fraction >= STYLE_MIN_MEASURED_WEIGHT).sum()),
                             interpretation='statistical proxy only; tactical effectiveness unvalidated',
                             goalkeeper_scouting_supported=False if position == 'GK' else None))
    return rows
