# Finance Operations Invoice Agent

This project is a prototype of AI Agent Task Runner for a finance operations scenario.

When a finance operations user wants to investigate invoice payment status:

> "Please check invoice INV-1001. Why is it not paid yet, and what should I do next?"

The application extracts the invoice ID, runs a agent plan, calls registered tools, records a structured execution trace, and returns a business-readable recommendation for the finance user.

This prototype covers that workflow with mock JSON data:

- `INV-1001`: blocked because the invoice amount is higher than the PO amount.
- `INV-1002`: pending approval.
- `INV-1003`: already paid.
- Missing, invalid, and unknown invoice IDs return structured errors.

## Overview

The backend exposes a REST API powered by FastAPI. The agent uses a rule-based planner instead of a real LLM API. Tool execution goes through a `ToolRegistry`, and every tool call is stored in a structured trace with inputs, outputs, timestamps, durations, statuses, and errors.

The frontend is a minimal React/Vite interface where a user can submit a finance request, read the final answer, inspect the executed actions, and review the full execution trace.

## Tech Stack

- Backend: Python, FastAPI, Pydantic
- Agent: rule-based planner, tool registry, structured trace recorder
- Data storage: mock JSON files
- Frontend: React, TypeScript, Vite, TailwindCSS
- API style: REST
- Backend tests: Pytest, FastAPI TestClient
- Frontend tests: Vitest, React Testing Library
- Code quality: ESLint, Prettier
- DevOps: Docker and Docker Compose

## Project Structure

```text
backend/
  Dockerfile
  api/routes.py
  agent/
    context.py
    errors.py
    planner.py
    runner.py
    trace.py
  data/
    invoices.json
    policies.json
    purchase_orders.json
  tests/test_agent_api.py
  tools/
    base.py
    data_loader.py
    draft_email.py
    invoice_lookup.py
    policy_lookup.py
    po_lookup.py
    registry.py
  main.py
frontend/
  Dockerfile
  nginx.conf
  src/
    App.test.tsx
    App.tsx
    main.tsx
    setupTests.ts
    styles.css
docs/
  screenshots/invoice-agent-main.png
docker-compose.yml
requirements.txt
```

## Backend API

### `POST /agent/run`

Runs the finance agent for a user request.

Request:

```json
{
  "userRequest": "Please check invoice INV-1001. Why is it not paid yet?"
}
```

Success response:

```json
{
  "status": "completed",
  "finalAnswer": "Invoice INV-1001 for ABC Logistics is not paid yet because it is blocked because the invoice amount is higher than the PO amount...",
  "actions": [
    { "type": "invoice_lookup", "status": "success" },
    { "type": "po_lookup", "status": "success" },
    { "type": "policy_lookup", "status": "success" },
    { "type": "draft_email", "status": "success" }
  ],
  "traceId": "trace-..."
}
```

Error response example:

```json
{
  "status": "failed",
  "finalAnswer": "Invoice INV-9999 was not found.",
  "actions": [{ "type": "invoice_lookup", "status": "failed" }],
  "traceId": "trace-...",
  "error": {
    "errorCode": "INVOICE_NOT_FOUND",
    "message": "Invoice INV-9999 was not found.",
    "recoverable": true
  }
}
```

Important status behavior:

- `completed`: full answer was generated.
- `partial`: policy lookup failed, but invoice and PO context were available.
- `needs_input`: request did not include an invoice ID.
- `failed`: invalid invoice format, invoice not found, or tool execution failure.

### `GET /agent/traces/{traceId}`

Returns the full structured trace for a previous run.

Trace response includes:

- `traceId`
- `userInput`
- `goal`
- `finalAnswer`
- `error`
- `steps`

Each trace step includes:

```json
{
  "stepId": "step-001",
  "stepName": "invoice_lookup",
  "toolName": "invoice_lookup",
  "input": { "invoiceId": "INV-1001" },
  "output": { "status": "blocked", "blockReason": "PO_AMOUNT_MISMATCH" },
  "status": "success",
  "error": null,
  "startedAt": "2026-06-28T10:00:00Z",
  "durationMs": 12
}
```

## Frontend Usage

Start the backend and frontend, then open:

```text
http://127.0.0.1:5173
```

Use the page as follows:

1. Enter a finance request in the text box, for example:

   ```text
   Please check invoice INV-1001. Why is it not paid yet, and what should I do next?
   ```

2. Click **Run agent**.
3. Read the final business answer.
4. Review the action list to see which tools were called.
5. Inspect the execution trace to see tool inputs, outputs, statuses, timing, and errors.

### Page Screenshot

![Invoice payment investigator screenshot](docs/screenshots/invoice-agent-main.png)

## Local Backend Debugging

Create or activate the conda environment:

```powershell
conda activate agentrunner
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the API:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Try the main endpoint:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/agent/run" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"userRequest":"Please check invoice INV-1001"}'
```

Run backend tests:

```powershell
python -m pytest backend\tests
```

## Local Frontend Debugging

Install dependencies:

```powershell
cd frontend
npm install
```

Run the Vite dev server:

```powershell
npm run dev
```

The Vite config proxies `/agent` API calls to:

```text
http://127.0.0.1:8000
```

Build the frontend:

```powershell
npm run build
```

Run frontend tests:

```powershell
npm test
```

Run lint and formatting checks:

```powershell
npm run lint
npm run format
```

## Docker and Docker Compose

The repository includes Docker files for both services:

- `backend/Dockerfile`: builds the FastAPI service with Python and runs Uvicorn on port `8000`.
- `frontend/Dockerfile`: builds the React app with Node, serves it with Nginx, and exposes port `80` inside the container.
- `frontend/nginx.conf`: serves the SPA and proxies `/agent/` requests to the backend service.
- `docker-compose.yml`: starts `backend` and `frontend` together.

From the repository root:

```powershell
docker compose up --build
```

Open the frontend:

```text
http://127.0.0.1:5173
```

The Compose file maps:

| Service | Container | Host URL |
| --- | --- | --- |
| Frontend | `finance-agent-frontend` | `http://127.0.0.1:5173` |
| Backend | `finance-agent-backend` | `http://127.0.0.1:8000` |

## Test Coverage

| Area | Command | Result |
| --- | --- | --- |
| Backend API tests | `python -m pytest backend\tests` | 12 passed |
| Frontend component tests | `npm test` | 3 passed |
| Frontend production build | `npm run build` | Passed |
| Browser smoke flow | Playwright against local backend and Vite frontend | Passed; screenshot captured |

Backend scenarios covered:

- `INV-1001` blocked by PO amount mismatch.
- `INV-1002` pending approval.
- `INV-1003` already paid, no policy lookup.
- `INV-9999` invoice not found.
- Missing invoice ID.
- Empty user request.
- Invalid invoice format.
- Lowercase invoice ID normalization.
- Extra spaces in the request.
- Simulated policy lookup failure.
- Unexpected tool result.
- Trace endpoint returns structured steps.

Frontend scenarios covered:

- Submitting a request displays the final answer and trace steps.
- Structured API errors are shown clearly.
- Empty submissions are blocked before calling the backend.

## Notes and Limitations

- The planner is intentionally deterministic and rule-based; it does not call a real LLM API.
- Data is stored in mock JSON files, not a database.
- The `draft_email` tool generates email content only; it does not send email.
