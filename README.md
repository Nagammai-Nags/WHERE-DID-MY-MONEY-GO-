# Where Did My Money Go?

A smart expense tracker with automatic transaction categorization. This privacy-first UPI spending prototype stores transactions locally in SQLite and reports deterministic INR analytics.

## Requirements and Setup

Use Python 3.10 or later.

In VS Code PowerShell, from this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```sh
./run.sh
```

Or run Uvicorn directly:

```sh
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The app is served at <http://127.0.0.1:8000>. The health endpoint is <http://127.0.0.1:8000/api/v1/healthz>.

The application database defaults to `data/wdmmg.db`; set `WDMMG_DB` to override it. `run.sh` honors `HOST` and `PORT`.

## Frontend

The vanilla JavaScript frontend includes Import, Review merchants, Dashboard, Transactions, Graph Analytics, Sankey, Budget, and Assistant screens.

Member 3 owns:

- `frontend/index.html`
- `frontend/style.css`
- `frontend/api.js`
- `frontend/app.js`
- `frontend/charts.js`

Member 4 owns:

- `frontend/budget.js`
- `frontend/assistant.js`
- `frontend/graph_analytics.js`

The frontend displays values supplied by the API and does not calculate financial totals.

## Tests

```sh
pytest -q
```

Tests use temporary SQLite databases.
