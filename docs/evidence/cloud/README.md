# Cloud cost evidence and reproducible formulas

The dated original Module 9 estimate remains an historical assumption. `cost_inputs.csv` separates compute, primary storage, outbound transfer, retained backups, object storage, PUT/GET requests and monitoring. Its quantities are workload assumptions, not observed usage. Blank prices are deliberately pending, never zero/free. No complete total is calculated until every line has a rate, region, date and source URL.

Run from the project root:

```bash
python -m scripts.estimate_cloud_costs
python -m scripts.estimate_cloud_costs --usd-per-eur YOUR_VERIFIED_USD_PER_EUR
```

The rate is **USD for one EUR**: EUR total = USD total / rate. Preserve the ECB publication date and downloaded quote separately; this formula does not verify a user-entered quote. Tax, support plans, credits, burst CPU charges and allowances must be reconciled with the official selected configuration. No AWS resource is provisioned by this worksheet.

Manual evidence needed:

1. Open https://calculator.aws/, choose eu-west-1 and the documented prototype configuration. Compare continuous 730-hour use with the separate 40-hour teaching scenario; do not mix their quantities.
2. Include t3.medium, 50 GB gp3, relevant billable outbound GB after the applicable allowance, incremental retained snapshot GB and the actual chosen object-storage/request/monitoring services. Record redundancy and retention assumptions. If a component is not used, enter quantity zero with the documented architectural reason; verify its price rather than labelling it free.
3. Export the estimate, preserve the share link, capture a screenshot showing services/region/currency/total and record capture UTC date. Save under this folder; paste each line's verified rate and dated official URL into `cost_inputs.csv`.
4. Obtain the dated ECB quote at https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml; record publication date and USD per EUR. Recompute and retain output, identifying VAT/taxes separately.

Access attempts on 2026-10-12 UTC to AWS Calculator and ECB daily XML returned `CONNECT tunnel failed, response 403` through this environment's network gateway. No official estimate screenshot or exchange rate was acquired. See `access_attempts.json`. This is a network access blocker, not a pricing result.
