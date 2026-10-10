#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -c 'import sys; assert sys.version_info[:2] == (3,12), "Use Python 3.12"'
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/tmp/tfm-pip-cache}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/tfm-matplotlib}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/tfm-cache}"
export IPYTHONDIR="${IPYTHONDIR:-/tmp/tfm-ipython}"
export JUPYTER_RUNTIME_DIR="${JUPYTER_RUNTIME_DIR:-/tmp/tfm-jupyter}"
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip check
.venv/bin/python -m ipykernel install --prefix .jupyter --name tfm-python --display-name 'TFM Python 3.12'
# Uses the committed, explicitly labelled exploratory model for the app test.
# No download, training, synthetic fallback or source-data overwrite is implicit.
.venv/bin/python -m pytest -q
