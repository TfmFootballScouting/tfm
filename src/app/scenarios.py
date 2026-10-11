"""Explicit retrospective requirements; prices screen rankings, never train models."""
from dataclasses import dataclass, replace
import json
import numpy as np
import pandas as pd
from src.app.budget import attach_reported_values, screen_budget
from src.features.styles import measured_weight_fraction
from src.app.collected import ORIGINAL_STYLES

TEMPLATES = {
    'Desarrollo en posesión': dict(position='MF', style='posesion', max_age=23, min_minutes=900, budget_million=5.),
    'Equilibrio defensivo': dict(position='DF', style='solidez_defensiva', max_age=27, min_minutes=1800, budget_million=8.),
    'Ataque vertical': dict(position='FW', style='vertical', max_age=25, min_minutes=900, budget_million=10.),
    'Juego por banda (proxy)': dict(position='FW', style='desborde_banda', max_age=25, min_minutes=900, budget_million=10.),
}

@dataclass(frozen=True)
class Requirements:
    club: str
    season: str
    position: str
    style: str
    max_age: int
    min_minutes: int
    budget_million: float
    top_n: int = 5
    league: str | None = None

    def validate(self, rec):
        if self.position not in {'DF', 'MF', 'FW'}: raise ValueError('Use a broad outfield position')
        if self.style not in ORIGINAL_STYLES or measured_weight_fraction(self.style, rec.artifacts.feature_cols) < .6:
            raise ValueError('Style lacks measured feature coverage')
        for value, low, high in [(self.max_age, 18, 45), (self.min_minutes, 450, 10000), (self.top_n, 1, 50)]:
            if not isinstance(value, (int, np.integer)) or not low <= value <= high:
                raise ValueError('Invalid age, minutes or shortlist size')
        if not np.isfinite(self.budget_million) or self.budget_million <= 0: raise ValueError('Positive finite budget required')
        if set(rec.players.season) != {self.season}: raise ValueError('Use a single matching season gallery')
        if rec.players.partial_season.any(): raise ValueError('Partial seasons cannot support this scenario')
        clubs = {club for item in rec.players.clubs for club in json.loads(item)}
        if self.club not in clubs: raise ValueError('Select an observed club')
        if self.league is not None and (self.league not in set(rec.players.league) or rec.players.league.eq(self.league).sum() < 10):
            raise ValueError('Select a league with sufficient gallery coverage')

    @property
    def valuation_cutoff(self):
        return pd.Timestamp(f'{int(self.season.split("-")[1])}-06-30')


def run_scenario(rec, requirements, links, values):
    requirements.validate(rec)
    ranked = rec.recommend(style_key=requirements.style, top_n=len(rec.players), max_budget=None,
                           season=requirements.season)
    funnel = [{'stage': 'gallery', 'count': len(ranked)}]
    def keep(mask, stage):
        nonlocal ranked
        ranked = ranked.loc[mask].copy()
        funnel.append(dict(stage=stage, count=len(ranked)))
    if requirements.league is not None: keep(ranked.league.eq(requirements.league), 'target_league')
    keep(ranked.pos_main.eq(requirements.position), 'broad_position')
    keep(ranked.age.notna() & ranked.age.le(requirements.max_age), 'known_age_within_ceiling')
    keep(ranked.minutes.ge(requirements.min_minutes), 'minimum_minutes')
    keep(~ranked.clubs.map(lambda item: requirements.club in json.loads(item)), 'exclude_all_own_club_stints')
    ranked = attach_reported_values(ranked, links, values, requirements.valuation_cutoff)
    keep(ranked.reported_value_screenable, 'known_positive_reported_value')
    ranked = screen_budget(ranked, requirements.budget_million)
    funnel.append(dict(stage='reported_value_ceiling', count=len(ranked)))
    shortlist = ranked.head(requirements.top_n).copy()
    shortlist['scenario_club'] = requirements.club
    shortlist['scenario_style'] = requirements.style
    shortlist['scenario_kind'] = 'illustrative_retrospective_one_vacancy'
    return dict(shortlist=shortlist, eligible=ranked, funnel=pd.DataFrame(funnel))


def overlap(left, right):
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a | b else np.nan


def analyze_scenario(rec, requirements, links, values):
    result = run_scenario(rec, requirements, links, values)
    eligible = result['eligible']
    ids = result['shortlist'].entity_id
    baselines = []
    for name, rows in [('goals_assists_per90', eligible.sort_values(['ga_p90', 'player_id'], ascending=[False, True])),
                       ('goals_per90', eligible.sort_values(['gls_p90', 'player_id'], ascending=[False, True])),
                       ('seeded_random_42', eligible.sample(frac=1, random_state=42))]:
        baseline = rows.head(requirements.top_n)
        baselines.append(dict(baseline=name, eligible=len(eligible), returned=len(baseline),
                              shortlist_jaccard=overlap(ids, baseline.entity_id)))
    variations = [('budget_minus20pct', dict(budget_million=requirements.budget_million*.8)),
                  ('budget_plus20pct', dict(budget_million=requirements.budget_million*1.2)),
                  ('age_minus2', dict(max_age=max(18, requirements.max_age-2))),
                  ('age_plus2', dict(max_age=min(45, requirements.max_age+2))),
                  ('minutes_minus20pct', dict(min_minutes=max(450, int(requirements.min_minutes*.8)))),
                  ('minutes_plus20pct', dict(min_minutes=min(10000, int(requirements.min_minutes*1.2))))]
    sensitivity = []
    for name, changes in variations:
        other = run_scenario(rec, replace(requirements, **changes), links, values)
        sensitivity.append(dict(variation=name, eligible=len(other['eligible']), returned=len(other['shortlist']),
                                shortlist_jaccard=overlap(ids, other['shortlist'].entity_id)))
    result['baselines'] = pd.DataFrame(baselines)
    result['sensitivity'] = pd.DataFrame(sensitivity)
    return result
