"""Audited prepared-field glossary; never infers unknown raw-provider semantics."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DEFINITIONS={
'player':'Provider display name; names are not unique cross-source keys',
'nation':'Provider nationality code/text; not independently verified citizenship',
'pos':'Provider position label; multiple positions may be listed',
'pos_main':'First normalized position token; not a inferred tactical role',
'age':'Source-reported age for the season; not current age',
'birth_year':'Source birth calendar year; does not establish exact birth date',
'minutes':'Observed season playing minutes; unavailable for shot-only Understat exports',
'mp':'Provider season match appearances',
'gls':'Goals scored, provider season total', 'ast':'Assists, provider season total',
'xg':'Expected goals: sum of provider shot probabilities; provider model is not reproduced',
'xa':'Expected assists: provider expected-assist total; not interchangeable with xAG',
'xag':'Expected assisted goals: provider sum of xG on assisted shots',
'sh':'Shots attempted, season count', 'sot':'Shots on target, season count',
'int':'Interceptions, season count', 'tklw':'Tackles won, season count',
'crs':'Crosses, season count', 'fls':'Fouls committed, season count', 'fld':'Fouls drawn, season count',
'passes_completed':'Completed passes, season count', 'passes_attempted':'Attempted passes, season count',
'key_passes':'Passes directly leading to a shot, season count',
'touches':'Ball touches recorded by provider, season count',
'successful_take_ons':'Successful attempts to beat a defender while dribbling, season count',
'source':'Named provider and secondary acquisition channel',
'provenance_status':'Secondary archive provenance status; does not imply direct provider acquisition',
'period_status':'Coverage/completeness annotation; 2025-2026 is a September 2025 partial snapshot',
'age_source_text':'Unmodified provider age text retained for audit',
'foot':'Source preferred-foot text; unknown preserved',
'currency':'Normalized EUR assumption for values; source currency not independently verified',
'valuation_known_at':'UTC upload receipt timestamp: first known acquisition time in this project; not proof of original publication date',
'valuation_source':'Named provenance of reported market amount; not a model estimate or transfer fee',
'age_reference':'Explanation of source season-age temporal scope',
'nineties':'Playing minutes / 90; exposure denominator for season rates',
'pass_completion_pct':'100 * passes_completed / passes_attempted; zero denominator gives missing',
'minutes_eligible':'Whether minutes meet the code-defined minimum exposure threshold',
'complete_core_features':'All nine core rate features are present',
'experiment_split':'Chronological experiment membership assigned from source season, not random rows',
'core_proxy_split':'Chronological membership for core next-season retrieval experiment',
'age_filter_supported':'Whether source age metadata can support the app age filter',
'quality_inconsistent_counts':'Shots on target exceed shots OR completed passes exceed attempts',
'club_count':'Number of distinct clubs in aggregated player-season observation',
'metadata_conflict':'Within player-season, differing nonmissing name/age/birth-year/nationality metadata',
'id':'Original provider shot identifier, retained alongside normalized shot_id',
'result':'Provider shot outcome, including Goal and OwnGoal',
'h_a':'Primary shot team side: h=home, a=away',
'situation':'Provider shot situation category, such as open play or penalty',
'shotType':'Provider body-part/shot type label',
'match_id':'Provider-specific match identifier',
'home_team':'Provider home team name', 'away_team':'Provider away team name',
'home_goals':'Final observed home-team match goals', 'away_goals':'Final observed away-team match goals',
'date':'Provider match timestamp as supplied; not acquisition or publication time',
'player_assisted':'Provider name of assisting player, if recorded',
'lastAction':'Provider action immediately preceding shot',
'home_away':'Alternate provider home/away side field; checked against h_a',
'source_season':'Original Understat season start year before YYYY-YYYY normalization',
'shot_date':'Parsed provider match timestamp; not an independently verified publication time',
 'team_side_resolved':'Home/away side can be resolved without a conflict',
'side_field_conflict':'Both side fields populated and disagree; team is not silently assigned',
'attempt':'Shot result is not OwnGoal; own goals excluded from attack denominators',
'goal':'Shot result equals Goal; own goals excluded',
'attempt_xg':'Shot xG when attempt=True; zero for own goals only, not missing-xG imputation',
'matches_with_shots':'Distinct match IDs with observed shots; not total player appearances',
'player_raw':'Unmodified provider profile name before normalization',
'height_raw_cm':'Original reported height retained for audit; parsed height_cm is normalized',
'position_source':'Unmodified profile position description',
'main_position':'Normalized primary profile position; current profile scope',
'current_club_id':'Provider club ID in current profile snapshot; not historical club membership',
'current_club_name':'Club name in current profile snapshot; not historical club membership',
'date_of_birth_raw':'Unmodified reported birth-date string before parsing',
'profile_temporal_scope':'Current snapshot annotation; cannot be assumed known in historical seasons',
'valuation_date_raw':'Unmodified value event date before parsing',
'reported_zero_value':'Reported amount equals zero; ambiguous zero is excluded by budget filter',
'source_publication_known_at':'Original publication time if evidenced; unknown retained otherwise',
'date_evidence_status':'Whether value-event date and publication knowledge have independent evidence',
'historical_budget_eligible':'False when source publication knowledge is unavailable; prevents historical affordability claims',
}

def main():
    path=ROOT/'docs/data_dictionary_review.csv'
    frame=pd.read_csv(path)
    for i,row in frame.iterrows():
        field=row.field
        if field.endswith('_p90'):
            base=field[:-4]
            definition=DEFINITIONS.get(base)
            if definition:
                frame.loc[i,['definition','definition_status','unit']]=[definition+'; rate = season total * 90 / minutes; zero/unknown minutes remain missing','documented','events per 90 minutes' if base not in {'xg','xag','xa'} else 'expected events per 90 minutes']
        elif field in DEFINITIONS:
            frame.loc[i,['definition','definition_status']]=[DEFINITIONS[field],'documented']
    frame.to_csv(path,index=False)
    print('Unresolved prepared fields:',frame.loc[frame.definition_status.eq('pending_provider_glossary'),'field'].unique().tolist())
if __name__=='__main__':main()
