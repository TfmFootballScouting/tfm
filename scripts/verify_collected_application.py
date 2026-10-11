"""Verify collected-model serving, preserved experiments and actual app tests."""
from datetime import datetime, timezone
import json
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np

from src.config import ROOT
from src.app.collected import load_collected_service
from src.app.budget import load_budget_inputs, candidate_links, attach_reported_values
from scripts.salimt_history_audit import sha


def run():
    previous = json.loads((ROOT / 'reports/enrichment/pipeline.json').read_text())
    protected = {**previous['preserved_input_sha256'], **previous['outputs_sha256'], **previous['code_sha256']}
    for name, digest in protected.items():
        if sha(ROOT / name) != digest: raise ValueError(f'Existing data/model evidence changed: {name}')
    values, candidates, fbref = load_budget_inputs()
    modes = {}
    for name in ['core', 'offensive']:
        service = load_collected_service(name)
        mean = service.model.artifacts.scaler.mean_.copy()
        median = service.model.artifacts.imputer.statistics_.copy()
        coverage = []
        for season in service.available_seasons:
            model = service.for_season(season)
            links = candidate_links(model.players, candidates, fbref)
            prices = attach_reported_values(model.players, links, values, values.valuation_date.max())
            np.testing.assert_equal(model.artifacts.scaler.mean_, mean)
            np.testing.assert_equal(model.artifacts.imputer.statistics_, median)
            coverage.append({'season': season, 'candidate_people': len(model.players),
                'provisional_price_links': len(links), 'positive_reported_values': int(prices.reported_value_screenable.sum())})
        modes[name] = {'styles': service.supported_styles, 'season_coverage': coverage,
            'training_seasons': sorted(service.model.players.season.unique()),
            'distance_method': service.model.neighbor_method,
            'model_path': service.info['model_path'], 'model_sha256': service.info['model_sha256']}
    xml = ET.parse(ROOT / 'reports/collected_application_tests.xml').getroot()
    totals = {key: sum(int(suite.get(key, '0')) for suite in xml.findall('testsuite'))
              for key in ['tests', 'failures', 'errors', 'skipped']}
    assert totals['tests'] >= 98 and all(totals[key] == 0 for key in ['failures', 'errors', 'skipped'])
    with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=10) as response:
        assert response.status == 200 and response.read().decode().strip() == 'ok'
    paths = ['src/app/collected.py', 'src/app/streamlit_app.py', 'src/app/budget.py',
        'tests/test_collected_app.py', 'tests/test_app.py', 'scripts/verify_collected_application.py',
        'reports/collected_application_tests.xml']
    report = {'status': 'collected_models_served_application_verified',
        'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'default_mode': 'core',
        'source_git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'serving_modes': modes, 'legacy_mode_explicitly_available_and_tested': True,
        'training_transformations_frozen': True, 'neighbor_index_rebuilt_for_selected_gallery': True,
        'new_model_training_performed': False, 'preserved_evidence_files': len(protected),
        'provisional_reported_value_screening_preserved': True, 'price_fields_enter_model_transforms': False,
        'historical_budget_validation_performed': False, 'transfer_success_validation_performed': False,
        'app_workflows_executed': ['core_default_six_styles', 'season_gallery', 'position_minute_age_club_filters',
            'reported_value_budget', 'same_season_similarity', 'profiles_and_history',
            'identical_player_comparison_charts', 'offensive_mode_supported_styles', 'legacy_workflow'],
        'tests': totals, 'streamlit_health': '200 ok',
        'code_and_execution_sha256': {name: sha(ROOT / name) for name in paths},
        'limitations': ['Exploration uses observed full-season profiles, not historical decision simulation.',
            'Core/offensive evaluation folds differ; metrics cannot be directly interpreted as a controlled comparison.',
            'Styles and clusters are statistical proxies; tactic/transfer success is unvalidated.',
            'Complete advanced Segunda profiles and final 2025/26 galleries unavailable.',
            'Reported values retain provisional identities and unknown original publication dates.']}
    (ROOT / 'reports/collected_application_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'tests': totals, 'default': 'core', 'modes': modes}, indent=2))


if __name__ == '__main__':
    run()
