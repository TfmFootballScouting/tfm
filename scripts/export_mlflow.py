"""Portable export of genuine logged runs and their artifacts, excluding demos."""
import json
import shutil
from pathlib import Path
import mlflow
from mlflow.tracking import MlflowClient
from src.config import ROOT, MODELS_DIR


def run():
    mlflow.set_tracking_uri('sqlite:///mlflow.db')
    client=MlflowClient()
    meta=json.loads((MODELS_DIR/'metrics.json').read_text())
    record=client.get_run(meta['run_id'])
    export=ROOT/'reports/mlflow_export'
    export.mkdir(parents=True,exist_ok=True)
    payload=dict(run_id=record.info.run_id,experiment_id=record.info.experiment_id,status=record.info.status,
        start_time=record.info.start_time,end_time=record.info.end_time,
        artifact_root='.', runtime_artifact_uri_scope='machine-local URI omitted from portable export',
        params=record.data.params,metrics=record.data.metrics,tags=dict(record.data.tags))
    source_name=payload['tags'].get('mlflow.source.name')
    if source_name and Path(source_name).is_absolute():
        payload['tags']['mlflow.source.name']=Path(source_name).relative_to(ROOT).as_posix()
        payload['export_normalization']='Artifact root and local source-name tag made relative; metrics and other tags unchanged'
    (export/'run.json').write_text(json.dumps(payload,indent=2))
    for folder in ['evaluation','lineage','models']:
        items=client.list_artifacts(record.info.run_id,folder)
        if not items:
            raise ValueError(f'Missing logged {folder} artifacts')
        # Download through MLflow, rather than manufacture an export from unlogged files.
        source=client.download_artifacts(record.info.run_id,folder)
        shutil.copytree(source,export/folder,dirs_exist_ok=True)
    assert record.info.status=='FINISHED'
    assert payload['tags']['dataset_kind']=='real_legacy_unverified'
    print('Exported verified logged run:',record.info.run_id, 'metrics:',len(record.data.metrics))


if __name__=='__main__':
    run()
