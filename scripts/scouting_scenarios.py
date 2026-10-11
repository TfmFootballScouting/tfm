"""Run observed-data retrospective scenarios; no human events or transfer accuracy."""
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
import pandas as pd
from src.config import ROOT
from src.data.provenance import sha256
from src.app.collected import load_collected_service
from src.app.budget import load_budget_inputs, candidate_links
from src.app.scenarios import Requirements, TEMPLATES, analyze_scenario


def main():
    destination = ROOT / 'reports/scouting_scenarios'
    destination.mkdir(exist_ok=True)
    values, candidates, canonical = load_budget_inputs()
    tables = {key: [] for key in ['funnel', 'baselines', 'sensitivity', 'shortlist']}
    cases = []
    protected = json.loads((ROOT / 'reports/enrichment/pipeline.json').read_text())
    hashes = {**protected['preserved_input_sha256'], **protected['outputs_sha256']}
    for path, digest in hashes.items():
        if sha256(ROOT / path) != digest: raise ValueError(f'Protected artifact changed: {path}')
    for model, seasons in [('core', ['2022-2023', '2023-2024']), ('offensive', ['2023-2024', '2024-2025'])]:
        service = load_collected_service(model)
        for season in seasons:
            rec = service.for_season(season)
            links = candidate_links(rec.players, candidates, canonical)
            for label, template in TEMPLATES.items():
                if template['style'] not in service.supported_styles: continue
                req = Requirements(club='Valencia', season=season, **template)
                result = analyze_scenario(rec, req, links, values)
                case_id = f'{model}:{season}:{req.style}'
                cases.append(dict(case_id=case_id, label=label, requirements=asdict(req),
                                  valuation_cutoff=str(req.valuation_cutoff.date()), eligible=len(result['eligible']),
                                  returned=len(result['shortlist'])))
                for key in tables:
                    tables[key].append(result[key].assign(case_id=case_id, model=model, observed_season=season))
    for key, frames in tables.items():
        pd.concat(frames, ignore_index=True).to_csv(destination / f'{key}.csv', index=False)
    report = dict(created_at=datetime.now(timezone.utc).isoformat(),
                  git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  kind='illustrative_retrospective_requirements_real_observations', cases=cases,
                  protected_artifacts_verified=len(hashes), dataset_version=protected['dataset_version'],
                  model_retrained=False, transfer_success_validated=False, identity_approval=False,
                  limitations=['Market assessment is not a transfer fee or total acquisition cost',
                               'Price identities provisional; original publication time unknown',
                               'No verified official club requirements or transfer outcome relevance labels',
                               'Broad FW is not a validated winger role; no advanced Segunda gallery'],
                  code_sha256={path: sha256(ROOT/path) for path in ['src/app/scenarios.py', 'scripts/scouting_scenarios.py']},
                  output_sha256={f'{key}.csv': sha256(destination/f'{key}.csv') for key in tables})
    (destination / 'results.json').write_text(json.dumps(report, indent=2))
    print(json.dumps([dict(case=case['case_id'], eligible=case['eligible'], returned=case['returned']) for case in cases], indent=2))

if __name__ == '__main__': main()
