import json
import pandas as pd
import pytest
from src.config import ROOT
from src.data.provenance import sha256
from src.data.source_rights import require_model_data_use


def test_actual_value_audit_preserves_inputs_and_never_infers_currency_or_known_at():
    report=json.loads((ROOT/'reports/valuation_verification/verification.json').read_text())
    for path,digest in report['input_sha256'].items():assert sha256(ROOT/path)==digest,path
    assert sha256(ROOT/'scripts/verify_reported_valuations.py')==report['audit_source_sha256']
    values=pd.read_parquet(ROOT/'data/processed/real/valuation_verification_records.parquet')
    assert len(values)==report['valuation_records']==901429
    assert values.amount_raw_roundtrip_verified.all() and values.effective_date_raw_roundtrip_verified.all()
    assert not values.primary_amount_verified.any() and not values.primary_effective_date_verified.any()
    assert values.currency_verification_status.str.contains('not_explicit').all()
    assert values.source_publication_known_at.isna().all()
    assert not values.historical_budget_eligible.any() and not values.model_use_eligible.any()
    with pytest.raises(ValueError):require_model_data_use(values)


def test_actual_identity_corroboration_stays_provisional():
    report=json.loads((ROOT/'reports/valuation_verification/verification.json').read_text())
    identities=pd.read_parquet(ROOT/'data/processed/real/valuation_verification_identities.parquet')
    assert len(identities)==5405 and identities.supported_review_candidate.sum()==4869
    assert identities.club_season_overlap_count.gt(0).sum()>=1650
    corroborated=identities[identities.verification_status.eq('corroborated_name_birth_year_and_club_season')]
    assert len(corroborated)==1650
    assert corroborated.supported_review_candidate.all() and corroborated.club_season_overlap_count.gt(0).all()
    primary=identities[identities.primary_profile_verified]
    assert set(primary.source_player_id.astype(str))=={'937958','527966'}
    assert primary.uploaded_dob_matches_retained_primary_profile.all()
    assert report['approved_identities']==0 and not identities.approved_identity.any()
    assert identities.identity_match_status.eq('provisional_not_reviewed').all()
    with pytest.raises(ValueError):require_model_data_use(identities)
