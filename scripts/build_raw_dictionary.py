"""Raw CSV glossary. Retained provider schema, not invented transformations."""
import json
import pandas as pd
from scripts.build_processed_dictionary import ROOT, DEFINITIONS

EXPLICIT={
'Season_End_Year':('Season end calendar year','year'), 'Squad':('Source club/squad name','text'),
'Comp':('Source competition name','text'), 'Born':('Reported birth year','year'),
'Url':('Source player profile URL, from which FBref ID is parsed','URL'),
'Mins_Per_90':('Playing minutes divided by 90','90-minute equivalents'),
'Mins_Per_90_Playing':('Playing minutes divided by 90','90-minute equivalents'),
'Min_Playing':('Playing minutes','minutes'), 'MP_Playing':('Match appearances','appearances'), 'Starts_Playing':('Starting appearances','appearances'),
'G+A':('Goals plus assists','count'), 'G_minus_PK':('Goals excluding penalties','count'), 'G+A_minus_PK':('Goals plus assists excluding penalty goals','count'),
'PK':('Penalty goals','count'), 'PKatt':('Penalty attempts','count'), 'CrdY':('Yellow cards','count'), 'CrdR':('Red cards','count'), '2CrdY':('Second-yellow dismissals','count'),
'PrgC':('Progressive carries by provider definition','count'), 'PrgP':('Progressive passes by provider definition','count'), 'PrgR':('Progressive passes received by provider definition','count'), 'Prog':('Legacy progressive passes field','count'),
'npxG':('Non-penalty expected goals','expected goals'), 'npxG+xAG':('Non-penalty xG plus expected assisted goals','expected events'), 'xG+xAG':('Expected goals plus expected assisted goals','expected events'),
'SoT_percent':('100 * shots on target / shots','percent'), 'Sh_per_90':('Shots * 90 / minutes','shots per 90 minutes'), 'SoT_per_90':('Shots on target * 90 / minutes','shots per 90 minutes'),
'G_per_Sh':('Non-penalty goals per non-penalty shot','ratio'), 'G_per_SoT':('Non-penalty goals per non-penalty shot on target','ratio'), 'Dist':('Average shot distance','yards'), 'FK':('Shots from free kicks','count'),
'npxG_per_Sh':('Non-penalty expected goals per shot','expected goals per shot'), 'G_minus_xG':('Goals minus expected goals','goals'), 'np:G_minus_xG':('Non-penalty goals minus non-penalty xG','goals'),
'Cmp':('Completed passes','count'), 'Att':('Attempted passes','count'), 'Cmp_percent':('100 * completed / attempted passes','percent'),
'TotDist':('Total pass/carry distance, according to table category','yards'), 'PrgDist':('Distance towards opposing goal by passes/carries, according to table category','yards'),
'A_minus_xA':('Assists minus expected assists','assists'), 'A_minus_xAG':('Assists minus expected assisted goals','assists'),
'KP':('Key passes directly leading to shots','count'), 'Final_Third':('Passes entering final third','count'), 'PPA':('Completed passes entering penalty area','count'), 'CrsPA':('Completed crosses entering penalty area','count'),
'Tkl':('Tackles; challenges table counts dribblers tackled','count'), 'TklW':('Tackles won','count'), 'Def 3rd':('Events in defensive third, as specified by table group','count'), 'Mid 3rd':('Events in middle third, as specified by table group','count'), 'Att 3rd':('Events in attacking third, as specified by table group','count'),
'Tkl_percent':('100 * dribblers tackled / dribbler challenges','percent'), 'Lost':('Unsuccessful dribbler challenges','count'), 'Blocks':('Blocked shots and passes','count'), 'Pass':('Blocked passes','count'), 'Tkl+Int':('Tackles plus interceptions','count'), 'Clr':('Clearances','count'), 'Err':('Errors leading to an opponent shot','count'),
'Def Pen':('Touches in own penalty area','count'), 'Att Pen':('Touches in opposing penalty area','count'), 'Live':('Live-ball touches','count'),
'Succ':('Successful take-ons','count'), 'Succ_percent':('100 * successful / attempted take-ons','percent'), 'Tkld':('Times tackled during a take-on','count'), 'Tkld_percent':('100 * tackled / attempted take-ons','percent'),
'Carries':('Ball carries','count'), 'CPA':('Carries into penalty area','count'), 'Mis':('Miscontrols','count'), 'Dis':('Times dispossessed','count'), 'Rec':('Passes received','count'),
'Off':('Offsides','count'), 'PKwon':('Penalties won','count'), 'PKcon':('Penalties conceded','count'), 'OG':('Own goals','count'), 'Recov':('Loose-ball recoveries','count'),
'Won':('Aerial duels won','count'), 'Won_percent':('100 * won / total aerial duels','percent'),
'X':('Normalized longitudinal shot coordinate','fraction 0–1'), 'Y':('Normalized lateral shot coordinate','fraction 0–1'), 'minute':('Recorded match minute','minutes'), 'xG':('Provider shot probability of scoring','probability 0–1'),
'season':('Original Understat season start year','year'), 'player_id':('Provider-specific player identifier','identifier'), 'league':('Competition label','category'),
'date_unix':('Despite its name, supplied CSV contains ISO calendar value dates, not Unix seconds','YYYY-MM-DD'),
'value':('Reported market assessment; EUR assumed by normalizer, currency unverified; not transfer fee','source amount'),
'height':('Provider-reported height; normalizer treats positive numeric values as centimetres','source height, assumed cm'),
'is_eu':('Source European Union membership flag; not independently verified eligibility','boolean'),
'_last_modified_at':('Secondary dataset modification timestamp; not proof of provider publication','timestamp'),
'season_points_against':('Source field points_against; interpretation unverified, not used in pipeline','provider-defined; unverified'),
'season_points_for':('Source field points_for; interpretation unverified, not used in pipeline','provider-defined; unverified'),
'season_manager':('Source manager metadata; may contain serialized structure','source text/object'),
}

def definition(field,provider):
    if field in EXPLICIT:return (*EXPLICIT[field],'documented' if 'unverified' not in EXPLICIT[field][1] else 'pending_provider_glossary')
    if field in DEFINITIONS:return (DEFINITIONS[field],'source text/category' if field not in {'home_goals','away_goals'} else 'goals','documented')
    if provider=='fbref':
        if field.endswith('_Per'):
            base=field[:-4]
            meaning,unit,status=definition(base,provider)
            return (meaning+'; provider rate per 90 minutes',unit+' per 90 minutes',status)
        groups=['_Playing','_Progression','_Standard','_Expected','_Total','_Short','_Medium','_Long','_Tackles','_Challenges','_Blocks','_Touches','_Take','_Carries','_Receiving','_Aerial']
        for suffix in groups:
            if field.endswith(suffix):
                base=field[:-len(suffix)]
                if field=='Att_Take':return ('Attempted take-ons','count','documented')
                if field=='Att_Challenges':return ('Challenges against dribbling opponents','count','documented')
                if field=='Sh_Blocks':return ('Shots blocked','count','documented')
                if field=='Lost_Aerial':return ('Aerial duels lost','count','documented')
                if field=='Final_Third_Carries':return ('Carries entering final third','count','documented')
                d,u,s=definition(base,provider)
                return (d+'; group '+suffix[1:],u,s)
        lower={'Player':'player','Nation':'nation','Pos':'pos','Age':'age','Gls':'gls','Ast':'ast','Sh':'sh','SoT':'sot','Int':'int','Crs':'crs','Fls':'fls','Fld':'fld','xA':'xa','xAG':'xag','xG':'xg','Touches':'touches'}
        if field in lower:return (DEFINITIONS[lower[field]],'years' if field=='Age' else ('source label' if field in ['Player','Nation','Pos'] else 'count or expected events'),'documented')
    if provider=='transfermarkt':
        dates={'date_of_birth','joined','contract_expires','date_of_last_contract_extension','contract_there_expires','date_of_death'}
        if field in dates:return ('Source '+field.replace('_',' ')+' date; current snapshot, not historical publication evidence','source date','documented')
        if field.endswith('_id'):return ('Provider-specific '+field[:-3].replace('_',' ')+' identifier; not universal','identifier','documented')
        if field.endswith('_url'):return ('Source '+field[:-4].replace('_',' ')+' URL','URL','documented')
        if field.endswith('_slug'):return ('Source URL slug for '+field[:-5].replace('_',' '),'text','documented')
        if field.endswith('_name') or field in {'player_name','name_in_home_country','citizenship','place_of_birth','country_of_birth','outfitter','contract_option','position','club_division','season_manager_manager_name','team_name'}:
            return ('Source '+field.replace('_',' ')+'; snapshot metadata, not independently verified','text/category','documented')
        counts={'season_wins':'wins','season_draws':'draws','season_losses':'losses','season_total_matches':'matches','season_goals_for':'goals scored','season_goals_against':'goals conceded','season_goal_difference':'goals scored minus conceded','season_points':'league points','season_rank':'league standing rank','season_league_level_level_number':'competition tier number'}
        if field in counts:return ('Reported team-season '+counts[field],'count/points/rank as named','documented')
        if field=='season_is_two_point_system':return ('Whether source competition uses two points for a win','boolean','documented')
        if field=='season_season':return ('Source season display label','season label','documented')
    return ('Unresolved provider field; retained verbatim and excluded from model features','unverified','pending_provider_glossary')


def main():
    manifest=json.loads((ROOT/'data/raw/source_manifest.json').read_text())
    rows=[]
    for record in manifest['raw_csvs']:
        for field in record['columns']:
            d,u,status=definition(field,record['provider'])
            rows.append(dict(table=record['path'],field=field,unit=u,definition=d,definition_status=status,provenance_manifest='data/raw/source_manifest.json'))
    frame=pd.DataFrame(rows);frame.to_csv(ROOT/'docs/data_dictionary_raw.csv',index=False)
    print(frame[frame.definition_status.ne('documented')][['table','field']].to_string(index=False))
if __name__=='__main__':main()
