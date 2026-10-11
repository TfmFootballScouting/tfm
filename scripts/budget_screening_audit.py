"""Record real coverage and executed application tests for reported-value screening."""
from datetime import datetime, timezone
import json
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

from src.config import ROOT, MODELS_DIR
from src.app.budget import load_budget_inputs, candidate_links, attach_reported_values, screen_budget
from src.models.recommend import PlayerRecommender
from scripts.salimt_history_audit import sha


def run():
    preserved = json.loads((ROOT / 'reports/enrichment/pipeline.json').read_text())
    for name, digest in {**preserved['preserved_input_sha256'], **preserved['outputs_sha256'], **preserved['code_sha256']}.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Prior data/model evidence changed: {name}')
    values, candidates, fbref = load_budget_inputs()
    rec = PlayerRecommender.load(MODELS_DIR / 'recommender.joblib')
    links = candidate_links(rec.players, candidates, fbref)
    cutoff = values.valuation_date.max()
    attached = attach_reported_values(rec.players, links, values, cutoff)
    xml = ET.parse(ROOT / 'reports/budget_screening_tests.xml').getroot()
    suites = xml.findall('testsuite')
    tests = {key: sum(int(suite.get(key, '0')) for suite in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    assert tests['tests'] >= 94 and all(tests[key] == 0 for key in ['failures', 'errors', 'skipped'])
    with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=10) as response:
        assert response.status == 200 and response.read().decode().strip() == 'ok'
    paths = ['src/app/budget.py', 'src/app/streamlit_app.py', 'tests/test_budget_screening.py',
        'scripts/budget_screening_audit.py', 'reports/budget_screening_tests.xml',
        'data/processed/real/collected_salimt_values.parquet',
        'data/processed/real/collected_salimt_identity_candidates.parquet',
        'data/processed/real/collected_player_seasons.parquet', 'models/real/recommender.joblib']
    report = {'status': 'reported_market_value_screening_enabled_verified',
        'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_use_scope': 'local_user_requested_reported_value_display_and_post_ranking_screening_no_model_fit_or_transform',
        'latest_reported_date': cutoff.date().isoformat(), 'valuation_records': len(values),
        'application_observations': len(rec.players), 'application_people': int(rec.players.entity_id.nunique()),
        'provisionally_linked_observations': len(links),
        'positive_value_observations': int(attached.reported_value_screenable.sum()),
        'positive_value_people': int(attached[attached.reported_value_screenable].entity_id.nunique()),
        'status_counts': {key: int(value) for key, value in attached.reported_value_status.value_counts().items()},
        'observations_under_1M': len(screen_budget(attached, 1)),
        'observations_under_10M': len(screen_budget(attached, 10)),
        'identity_match_approval': False, 'source_use_authorization_for_model_fit': False,
        'historical_budget_validation_performed': False, 'original_publication_dates_known': False,
        'estimated_missing_prices_generated': False, 'transfer_fee_predictions_generated': False,
        'model_retraining_performed': False, 'zero_values_screened_as_free': False,
        'prior_evidence_unchanged': True, 'tests': tests, 'streamlit_health': '200 ok',
        'input_and_code_sha256': {name: sha(ROOT / name) for name in paths},
        'limitations': ['Market values are reported assessments, not agreed fees.',
            'Source dates support backward-only association, not publication-time availability.',
            'Player identity links remain provisional and are labelled in the UI/export.',
            'Latest zero/invalid values are unknown; no fallback to older positive values.',
            'The currently served model uses legacy 2023/24 profiles; valuation cutoff is independent and displayed.']}
    (ROOT / 'reports/budget_screening.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['status', 'positive_value_people', 'tests', 'streamlit_health']}, indent=2))


if __name__ == '__main__':
    run()
