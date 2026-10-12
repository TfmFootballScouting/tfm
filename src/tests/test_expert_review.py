import pandas as pd
import pytest
from src.process.expert_review import analyze


def test_blank_real_review_template_is_pending():
    ratings=pd.read_csv('docs/expert_review/rating_template.csv')
    report,summary=analyze(ratings,pd.DataFrame())
    assert report['status']=='pending_human_ratings' and summary.empty


def test_duplicate_human_rating_rejected():
    row=dict(expert_alias='unit-test',brief_id='b',packet='A',player_id='p',tactical_fit_1_to_5=4,shortlist_yes_no='yes',confidence_1_to_5=3,rationale='Unit fixture')
    with pytest.raises(ValueError,match='Duplicate'):
        analyze(pd.DataFrame([row,row]),pd.DataFrame([dict(brief_id='b',packet='A',method='style_affinity')]))
