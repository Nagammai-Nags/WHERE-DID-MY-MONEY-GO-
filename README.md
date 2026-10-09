# Where Did My Money Go?

A smart expense tracker with automatic transaction categorization. This privacy-first UPI spending prototype stores transactions locally in SQLite and reports deterministic INR analytics. Member 1 owns the shared data model, database/repository, core analytics and API integration foundation.

## Requirements and setup

Use Python 3.10 or later. In VS Code PowerShell, from this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

On macOS/Linux, `./run.sh` starts the same server (honors `HOST` and `PORT`). The health endpoint is <http://127.0.0.1:8000/api/v1/healthz>.

## Tests

```powershell
pytest -q
```

Tests use temporary SQLite databases. The application database defaults to `data/wdmmg.db`; set `WDMMG_DB` to override it.
