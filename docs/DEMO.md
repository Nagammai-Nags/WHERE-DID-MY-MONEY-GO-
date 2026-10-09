# WDMMG Prototype Demo

This script is for the final 6-minute prototype walkthrough. It assumes the app is running from a clean local SQLite database and uses the shared October 2026 sample data.

## Setup

Before the audience arrives:

```sh
rm -f data/wdmmg.db
./run.sh
```

Open the browser at:

```text
http://127.0.0.1:8000
```

Keep a second terminal open with:

```sh
cat data/extra_message.txt
```

Driver: Member 3. Narration: Member 1 for setup/architecture, Member 2 for ingestion and merchant correction, Member 4 for Sankey, budget, and assistant.

## Walkthrough

| # | Action | Narration | Expected result |
|---|---|---|---|
| 1 | Open the app on Dashboard. | Empty state: no numbers are invented. Member 1 gives the one-process architecture summary. | Empty state with Load sample data. |
| 2 | Click Load sample data. | 14 bank-statement rows and 5 pasted SMS-style blocks go through the same pipeline. | 18 found, 17 imported, 1 duplicate skipped, 1 non-transaction ignored, 5 unknown merchants. |
| 3 | Open Transactions. | Swiggy and Uber are recognized, but original text is preserved. Income and self-transfer are visibly not spending. | Original counterparty text appears under merchant names; INCOME and TRANSFER_OUT rows are not counted as spend. |
| 4 | Open Dashboard. | Total spending is computed from transactions, not hardcoded. | Spending ₹5,918.00, income ₹8,250.00, Uncategorized ₹280.00, and a 5 unknown merchants review banner. |
| 5 | Open Review merchants. Rename `q8812@ybl` to `Tea stall`, category `Food`. | The user teaches the app once. | 4 transactions updated; queue now only has `rajesh77@oksbi`; Food ₹1,050.00; Uncategorized ₹150.00. |
| 6 | Return to Dashboard and show Sankey. Hover Small payments in Food. | Income flows to categories and merchants. Payments of ₹100.00 or less are grouped. | Root ₹8,250.00; Food ₹1,050.00 splits into Swiggy ₹450.00, Zomato ₹380.00, Small payments ₹220.00; Not spent ₹2,332.00. |
| 7 | In Budget, set ₹5,000, then ₹6,500. | Spending is ₹5,918.00; status changes are computed from the same net spend rule. | ₹5,000 shows Exceeded, ₹918.00 over, 118.4%. ₹6,500 shows Warning, ₹582.00 remaining, 91.0%. |
| 8 | Ask the assistant: `Where did most of my money go this month?` Then ask `How much did I spend on small transactions?` Then ask `Should I invest in mutual funds?` | Every amount comes from computed facts; unsupported questions are refused. Point at the facts table and `engine: rules`. | Transport ₹1,420.00, 24.0% of ₹5,918.00. Small payments: 5, ₹220.00. Unsupported investment question gets no rupee figures. |
| 9 | Paste `data/extra_message.txt` into Import and submit. | A new Q8812 payment arrives after the correction, with no repeat prompt. | 1 imported; review queue unchanged; Food ₹1,090.00; total spending ₹5,958.00; budget updates. |
| 10 | Stop and restart the server, then reload. | Aliases, budget, and transactions persist. | Same numbers remain; Tea stall is still applied. |

## Honest Framing

Say this clearly at the end:

- Single local demo user, no login.
- Rule-based assistant for the prototype; no LLM in the must-build path.
- SQLite is used instead of PostgreSQL.
- PDF/OCR, forecasts, push notifications, auth, and deployment are deferred.
- Auto-classified labels come from a small built-in dictionary.
- Confirmed merchant names are only the ones typed by the user.

## If Something Breaks

Keep the value story moving: import sample data, show dashboard totals, rename Tea stall, show budget exceeded/warning, ask the assistant top-category question, then show the Sankey table view if the visual renderer is unavailable.

Do not debug on stage. Use table views and the computed API payloads as the fallback.
