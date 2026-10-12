import argparse
import json
from pathlib import Path
import pandas as pd
from src.process.cloud_costs import estimate

parser=argparse.ArgumentParser()
parser.add_argument('--inputs',default='docs/evidence/cloud/cost_inputs.csv')
parser.add_argument('--usd-per-eur',type=float)
args=parser.parse_args()
rows=pd.read_csv(args.inputs,keep_default_na=False).to_dict('records')
print(json.dumps(estimate(rows,args.usd_per_eur),indent=2))
