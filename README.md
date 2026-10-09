# Where Did My Money Go?

## Member 3 frontend — current branch: `member3`

This branch contains the responsive, vanilla JavaScript frontend for the prototype: Import, Review merchants, Dashboard, Transactions, and Assistant screens. The dashboard and Sankey views display values supplied by the API. They do not calculate financial totals.

### Files in this branch

- `frontend/index.html` and `frontend/style.css` — page shell, tabs, responsive styles, and panel mount points.
- `frontend/api.js` — `/api/v1` client, mock mode, error toast, and INR/date formatting helpers.
- `frontend/app.js` — import, merchant review, dashboard, and transaction interactions.
- `frontend/charts.js` — Sankey renderer, fallback flow view, and link table.
- `frontend/fixtures/` — documented mock responses for summary, Sankey, transactions, review queue, and import result.

`frontend/budget.js` and `frontend/assistant.js` belong to Member 4 and are included by the page, but are not present in this checkout. The backend is also not present here, so real API integration is pending.

### Preview the mock frontend

From the repository root, serve the files with a local static server, then open:

```text
http://localhost:8000/frontend/index.html?mock=1
```

For example, if Python is installed:

```bash
python -m http.server 8000
```

Mock GET requests load the JSON in `frontend/fixtures/`. Mock writes return documented fixture responses and do not persist changes. For the integrated app, serve the frontend through the FastAPI application and connect it to `/api/v1`.

### Contract and ownership

The frontend follows `PROTOTYPE_WORK_SPLIT.md` §5 and the Member 3 checklist in §9. The split names `m3-frontend` as the frontend branch; this workspace checkout is currently named `member3`.

### Current verification limits

JavaScript syntax, fixture JSON parsing, and static asset serving were checked in this workspace. A browser walkthrough could not be run because no browser was available. The mock UI can render the supplied fixtures, but the full mouse journey requires the backend and Member 4's budget and assistant panels.
