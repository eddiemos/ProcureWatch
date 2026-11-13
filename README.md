# ProcureWatch

ProcureWatch is an explainable risk-screening application for Kenyan public procurement records published in the Open Contracting Data Standard (OCDS) format. It highlights unusual patterns for further review; a risk indicator is not evidence of wrongdoing and does not accuse any person or organisation.

## Features

- Reads OCDS JSONL records, including records with missing awards, suppliers, or values.
- Normalises buyer, supplier, tender, award, contract, date, and value fields while retaining the source record and source-file path for traceability.
- Validates the normalised dataset with Pandera and reports missing values and invalid records.
- Calculates award, buyer, supplier, and buyer-supplier relationship features.
- Combines an Isolation Forest anomaly signal with supplier concentration, relative award value, and repeated-relationship signals into a transparent 0-100 screening score.
- Provides a Streamlit dashboard for an overview, risk monitoring, procurement exploration, and data quality.
- Provides a FastAPI service with searchable records, buyer and supplier profiles, high-risk records, quality information, and interactive API documentation.
- Includes a NetworkX buyer-supplier graph module and a PostgreSQL schema for future extensions.

The score is a prioritisation aid, not a probability of fraud. The current model is unsupervised and has no labelled outcome data, so it does not report predictive accuracy, precision, or recall. Scores and thresholds are exploratory and should be reviewed before operational use.

## Data source

The intended source is the [Kenya PPRA dataset on the Open Contracting Data Registry](https://data.open-contracting.org/en/publication/147).

Download the JSONL export and place it at:

```text
data/2024.jsonl
```

The dashboard and API prefer `data/2024.jsonl`, then `data/procurements.jsonl`. If neither file is present, they show a small built-in demonstration dataset. The real dataset is deliberately excluded from Git: it is large, may have redistribution conditions, and should be downloaded separately.

Each non-empty line should contain one OCDS JSON object. The loader processes the file line by line and logs malformed or non-object lines rather than silently accepting them.

## Run locally (Windows PowerShell)

Use Python 3.10 or later. From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

If PowerShell says the virtual-environment Python cannot be found, confirm that the commands are being run from the `ProcureWatch` project root.

### Start the dashboard

```powershell
.\.venv\Scripts\python.exe -m streamlit run procurewatch\dashboard\app.py
```

Open the local address printed by Streamlit, usually [http://localhost:8501](http://localhost:8501).

### Start the API

Open a second PowerShell terminal in the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn procurewatch.api.app:app --reload
```

- Interactive API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Stop either process with **Ctrl+C**. Restart the processes after replacing the dataset so the API reloads it.

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health check |
| `GET /stats` | Record count, risk distribution, and data-quality summary |
| `GET /procurements` | Paginated records; supports `page`, `per_page`, `supplier`, and `buyer` filters |
| `GET /procurements/{ocid}` | Procurement record details |
| `GET /suppliers/{supplier_id}` | Supplier profile and award records |
| `GET /buyers/{buyer_id}` | Buyer profile and procurement records |
| `GET /high-risk` | Records with a score of 55 or higher |
| `GET /quality` | Data-quality summary |

## Risk score

The current score combines four components:

- 45%: normalised Isolation Forest anomaly score
- 30%: supplier share of procurement value
- 15%: award value relative to the supplier's average
- 10%: percentile rank of buyer-supplier relationship frequency

The score is capped at 100. Categories are Low (<25), Medium (25-<55), High (55-<80), and Critical (80 or higher). These are configurable prototype thresholds, not statistically calibrated enforcement thresholds. Comparisons may be misleading across different currencies or incomparable procurement categories; review the data and context before investigating a flagged record.

## Tests

Run the focused test suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Project layout

```text
procurewatch/
  agent/       Evidence-oriented investigation helpers
  analysis/    Feature engineering, risk scoring, and network analysis
  api/         FastAPI application
  dashboard/   Streamlit application
  data/        JSONL loading and validation
database/
  schema.sql   PostgreSQL schema draft
data/          Place the downloaded JSONL dataset here
tests/         Pipeline tests
```

## Current scope and limitations

- The dashboard currently has Overview, Risk monitoring, Procurement explorer, and Data quality views.
- The API and dashboard analyse the dataset in memory; the PostgreSQL schema is not yet connected to the application.
- The NetworkX graph module and investigation helper are library components, not dashboard features or a deployed conversational assistant.
- MLflow experiment tracking is not currently integrated.
- This is a decision-support prototype. Flags require human review and additional evidence; they must not be presented as findings of corruption or misconduct.

## Contributing

Contributions should include focused tests for changed behaviour. Keep risk indicators explainable, preserve source traceability, and avoid treating missing data as evidence of wrongdoing.
