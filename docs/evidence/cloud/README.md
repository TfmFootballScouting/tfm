# Cloud costs — beginner guide for the TFM

## What you need to do first

Your professor asked for **evidence of an infrastructure cost estimate**: AWS Calculator screenshot/export, date, exchange rate, and separate computing/storage/transfer/backup costs. This does not by itself require deploying the project or paying for a server. Prepare the estimate first. Only launch resources if an actual cloud demonstration is required.

The current app works locally. A cloud version would run the same Python app on a rented computer instead of your PC. The repository already contains the model and prepared datasets; you do not need to scrape providers or train again merely to start the app.

## The proposed simple architecture

| Term | Plain meaning | Proposed use |
|---|---|---|
| EC2 | A rented virtual computer | Run Streamlit; optionally a private MLflow UI |
| t3.medium | One possible computer size: 2 virtual CPU cores, 4 GB RAM | Starting estimate for a small demo, not a capacity-tested guarantee |
| EBS gp3 | The computer's disk | 50 GB assumed for Linux, Python, project and local records |
| EBS snapshots | Saved backup copies of disk blocks | Proposed weekly backups, 30-day retention; not configured by this project |
| Outbound transfer | Data sent from AWS to visitors | Estimated billable traffic after documented allowances |
| Public IPv4 | An internet address for reaching the computer | Include address charges when the chosen setup uses one |
| S3 | Optional separate file storage | Not necessary for the initial one-computer prototype |
| Monitoring | Service health/usage measurements | Optional paid extras; do not assume every monitoring feature is free |

Region: **Europe (Ireland), eu-west-1**. No GPU, Kubernetes or managed database is required by the current prototype. Train on your PC for the first deployment and upload/use the existing model; cloud training is a different workload that needs its own resource estimate. Memory/concurrency suitability must be measured if you actually deploy.

## Step 1 — Make the AWS Calculator estimate

1. Open https://calculator.aws/ in your browser. Create an estimate and add **Amazon EC2**. You are estimating services, not launching them.
2. Select **Europe (Ireland)**, **Linux**, one instance, **t3.medium**, **On-Demand** pricing. Avoid adding Windows licensing or a paid software AMI when estimating the Ubuntu/Linux prototype.
3. Make a **continuous-use estimate: 730 instance-hours/month**. If the form asks for utilization instead of hours, select the setting that corresponds to continuous use and check the summary.
4. Include **50 GB EBS gp3** disk storage. Check whether EC2's estimate already includes it. Do not add the same disk again as a separate charge. Leave extra IOPS/throughput at the chosen standard configuration unless your design needs more; record the configuration.
5. Add the planned **snapshot storage** and **outbound transfer**. Our worksheet uses 50 GB-month of retained snapshots and 10 billable GB/month of transfer as assumptions. Snapshot billing is based on retained incremental data, not simply number of backups multiplied by disk size. Write down your actual assumption; it is not measured usage.
6. Include **public IPv4 address hours** if your proposed server has an address, and check whether that charge is already in the estimate. A retained/static address may continue to cost money even when the server is stopped.
7. For the initial prototype, you can omit S3, PUT/GET requests and paid custom monitoring if you will not use them. Explain these exclusions. If you do use them, add their actual configurations to the calculator.
8. Check the complete summary: services, region, quantity/usage assumptions and currency. Do not claim free tier or account credits unless the estimate documents exactly what applies. Record whether tax/support/additional burst CPU charges are included or excluded.

Create a **second, separate demo estimate with 40 instance-hours/month** if you want to show occasional classroom use. Keep disk and retained backups priced for the whole month when they remain provisioned. Do not multiply the entire continuous-use total by 40/730: storage and other retained resources do not stop costing money just because the instance stops.

## Step 2 — Save the teacher's evidence

Save these under this folder with the actual capture date in the filenames:

- `aws_estimate_YYYY-MM-DD.pdf` or the calculator's supported export.
- `aws_summary_YYYY-MM-DD.png`: screenshot showing region, services, currency and total.
- Additional service-detail screenshots if the summary does not show compute, disk, transfer, backups and address charges separately.
- `pricing_notes.md`: calculator share link, capture date, architecture, usage assumptions, excluded services and tax/credit assumptions. If you compare two scenarios, label them clearly.

Use actual screenshots and numbers from your estimate. The calculator is a proposal, not an invoice or proof that the project was deployed.

## Step 3 — Fill cost_inputs.csv

Open the CSV in an editor or spreadsheet, preserving comma-separated columns and decimal points.

| Column | What to enter |
|---|---|
| component | The charge being estimated, such as compute or backup |
| unit | Billing unit: instance-hour, GB-month, billable GB, etc. |
| quantity | Number of those units in one month |
| usd_per_unit | Verified USD price for exactly that unit/configuration/region |
| source_url | Official calculator share/service-pricing evidence URL |
| price_date | Date the price was captured, as YYYY-MM-DD |
| region | eu-west-1 for this proposed estimate |
| assumption | Explain what the quantity/configuration represents |

Do not enter a whole monthly total in `usd_per_unit`: the program multiplies quantity by unit price. If the calculator gives only a combined monthly subtotal, use the corresponding official AWS pricing breakdown to separate charges. Divide a component subtotal by quantity only when it really represents a single linear charge; tiered transfer, included allowances and bundled extras need their own breakdown.

Unused services: remove their rows from the worksheet and explain the exclusion in `pricing_notes.md`. A zero quantity with a blank/unverified price still leaves the current report pending. A real free allowance must be documented, not assumed. AWS official pricing pages: https://aws.amazon.com/ec2/pricing/ and https://aws.amazon.com/ebs/pricing/ ; use the region/configuration selected in your estimate.

The existing quantities are editable assumptions. Prices are deliberately blank because no official current estimate has been acquired. The program checks completeness and arithmetic; it cannot verify the truth of a manually entered price.

## Step 4 — Convert USD into EUR correctly

1. Get a dated ECB euro reference quote: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html .
2. Find the USD quote, expressed as **1 EUR = X USD**.
3. Save a screenshot/download with the rate's publication date. Record the publication date separately from when you downloaded it.
4. **EUR total = USD total / X**. Do not multiply by X.

## Step 5 — Generate the project report

From the project root, with the research environment installed:

```bash
python -m scripts.estimate_cloud_costs
```

If prices or source evidence are missing, `pending_price_evidence` and `null` are expected. `null` means unknown, not free.

For a verified conversion, replace `VERIFIED_USD_PER_EUR` below with your numeric ECB quote, without a currency symbol:

```bash
python -m scripts.estimate_cloud_costs --usd-per-eur VERIFIED_USD_PER_EUR > docs/evidence/cloud/cost_report.json
```

For a separate scenario, copy/edit the input CSV and pass it with `--inputs`; save each result under a different filename. Reconcile every line and the final total with the calculator. Keep unmatched fees, taxes or allowances explicit; do not hide a discrepancy.

## Step 6 — Update the TFM document

Update `docs/modulo9_cloud_estimacion.md` with:

- Proposed architecture and why one small CPU server is being estimated.
- Actual calculator date, region, configuration and share link.
- Monthly compute, disk, transfer, retained backup and address costs; optional services if used.
- Separate continuous-use and occasional-demo assumptions/results.
- Dated exchange rate and conversion direction, taxes/credits and exclusions.
- Your actual screenshots/exports and the honest statement that this is an estimate unless deployment was performed.

The old amounts in that document are historical assumptions. Replace the final quoted amounts with your verified estimate rather than presenting the historical numbers as today's prices.

## If your teacher also requires a real cloud demonstration

This is a later step that can incur charges. The calculator does not deploy anything.

1. Create/configure an AWS account, enable account protection and set billing alerts based on your estimate. Alerts are not an automatic spending cap.
2. Launch the selected Ubuntu EC2 instance in Ireland with the chosen disk. For a private academic demonstration, allow SSH from your own IP; do not open Streamlit or MLflow to everyone.
3. Connect with SSH using your private key. Install Git, Python 3.12 and its venv support. Clone `review/teacher-submission`, create a venv and install `requirements.lock.txt`.
4. Start the app on the server with `python -m streamlit run src/app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501`.
5. On your PC, open an SSH tunnel: `ssh -i YOUR_KEY.pem -L 8501:127.0.0.1:8501 ubuntu@YOUR_SERVER_ADDRESS`. Open the forwarded port 8501 in your local browser. Your key remains on your PC; never put it in Git or share its contents.
6. Check recommendations, league filters, values, comparisons, groups and shot views. Record observed memory/CPU and any errors before claiming the proposed instance is sufficient. MLflow can remain local for the first demo; never expose an unauthenticated tracking UI publicly.
7. After the demo, stop the instance to stop its running-compute charges, and check the retained disks, snapshots, static addresses and other resources that may still be billed. Delete only resources/data you intentionally no longer need, after preserving required evidence/backups.

No AWS resources are created, backups scheduled, HTTPS configured or deployment validated by the files in this folder. If the assignment only asks for cost evidence, complete Steps 1–6 and keep running the project locally.

## Calculator screenshots now received

The user supplied eight screenshots on 2026-10-13 showing the Linux t3.medium On-Demand configuration and a calculator summary of **41.17 USD/month**, **494.04 USD for 12 months**, and **0 USD upfront**. `calculator_observation.json` faithfully transcribes the visible settings, unit prices, calculations and limitations. The images have not been saved as original repository files; a calculator export/share link and capture-date confirmation are still needed.

Visible breakdown: compute 33.29 USD/month; gp3 disk 4.40; snapshots 2.58; Internet transfer 0.90. These displayed rounded lines sum to 41.17. Unrounded component arithmetic is 41.163; the calculator's rounded display is retained rather than silently replacing it with a different rounding rule.

`cost_inputs.csv` now contains the observed rates. Its price dates remain blank because the screenshots' reception date is not proof of the capture date. Optional S3/request/paid monitoring rows have been omitted because those services are not part of the shown estimate. Public IPv4 remains a pending row. Consequently the automated complete-cost report still reports pending, correctly distinguishing the observed calculator subtotal from a complete verified architecture budget.

The snapshot row's 51.5 GB-month is a **derived billing equivalent**, not a changed disk size: the calculator uses 50 GB initial snapshot plus three 1 GB increments with a 50% partial-month factor. Keep 50 GB disk and 1 GB changed per weekly snapshot in the calculator. No 30-day retention setting is evidenced. Verify free allowances, tax/extra credit charges, IP costs and FX before finalizing the TFM quote.
