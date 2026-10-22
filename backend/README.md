# Backend

This directory contains the FastAPI application, tests, migrations, and deployment
files. Run backend commands from this directory.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check app tests migrations
uvicorn app.main:app --reload

cold start command:-

 Set-Location D:\salon\salon-backend\backend\.artifacts\cloud-run-staging
>> 
>> 1..10 | ForEach-Object {
>>     Write-Host "Starting cold-start trial $_ of 10"
>>     python .\measure_20261020.py --trial $_
>> 
>>     if ($_ -lt 10) {
>>         Start-Sleep -Seconds 5
>>     }
>> }
>> python .\audit_20261020.py

```


Copy `.env.example` to `.env` for local development. Use `.env.gcp.example` only as a
template for a GCP VM. Real credentials must remain outside Git.

See [the repository README](../README.md) for setup and [the runbook](docs/RUNBOOK.md)
for operations.
