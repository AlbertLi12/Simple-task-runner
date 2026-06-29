# Test Instruction

This document describes how to test the Finance Operations Invoice Agent Runner. It covers backend API tests, frontend component tests, manual end-to-end checks, Docker Compose checks, and the expected results for the main business scenarios.

## 1. Scope

The test scope includes:

- Agent request parsing and invoice ID validation.
- Dynamic tool planning through `invoice_lookup`, `po_lookup`, `policy_lookup`, and `draft_email`.
- Structured error handling.
- Structured trace creation and trace retrieval by `traceId`.
- Frontend display of final answer, action statuses, trace IDs, step IDs, editable email draft, and explicit trace detail loading.
- Docker-based backend and frontend startup.

The implementation uses a deterministic rule-based planner. No real LLM API or real email service should be called during testing.

## 2. Prerequisites

From the repository root:

```powershell
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Recommended versions:

- Python 3.11 or newer.
- Node.js compatible with the installed frontend dependencies.
- Docker Desktop if Docker Compose testing is required.

## 3. Backend Automated Tests

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path
pytest
```

Expected result:

```text
14 passed
```

Backend automated tests are in:

```text
backend/tests/test_agent_api.py
```

Covered backend scenarios:

| Scenario | Expected Result |
| --- | --- |
| `INV-1001` PO amount mismatch | Completed response; calls `invoice_lookup`, `po_lookup`, `policy_lookup`, and `draft_email`; returns editable draft email data. |
| `INV-1002` approval pending | Completed response; calls invoice, PO, and policy tools; no draft email. |
| `INV-1003` paid invoice | Completed response; stops after invoice lookup; no policy lookup. |
| `INV-9999` invoice not found | `404`; `INVOICE_NOT_FOUND`; stops after invoice lookup. |
| Missing invoice ID | `400`; `MISSING_INVOICE_ID`; no tool calls. |
| Empty user request | `400`; `MISSING_INVOICE_ID`; no tool calls. |
| Invalid invoice format | `422`; `INVALID_INVOICE_ID`; no tool calls. |
| Lowercase invoice ID | Normalizes to uppercase and succeeds. |
| Extra spaces | Extracts invoice ID and succeeds. |
| Simulated policy lookup failure | Partial response with `POLICY_NOT_FOUND`. |
| Unknown policy data path | `INV-1004` returns partial response with `POLICY_NOT_FOUND`. |
| Unexpected tool result | `500`; `TOOL_EXECUTION_FAILURE`. |
| Trace endpoint | Returns structured steps with timestamps and durations. |
| Action metadata | Run response actions include `traceId` and `stepId`. |

## 4. Frontend Automated Tests

Run:

```powershell
cd frontend
npm test
```

Expected result:

```text
4 passed
```

Frontend automated tests are in:

```text
frontend/src/App.test.tsx
```

Covered frontend scenarios:

| Scenario | Expected Result |
| --- | --- |
| Successful `INV-1001` flow | Shows final answer, action statuses, editable email draft, and trace details only after explicit trace query. |
| Structured API error | Shows backend error and keeps failed action metadata visible. |
| No email draft case | Approval-pending response does not render the email draft block. |
| Empty submission | Frontend blocks the request before calling the backend. |

## 5. Frontend Build, Lint, and Format Checks

Run from `frontend/`:

```powershell
npm run build
npm run lint
npm run format
```

Expected result:

- `npm run build` completes without TypeScript or Vite errors.
- `npm run lint` completes without ESLint errors.
- `npm run format` reports that all matched files use Prettier code style.

## 6. Manual Backend API Tests

Start the backend:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6.1 PO Amount Mismatch

Request:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/agent/run" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"userRequest":"Please check invoice INV-1001. Why is it not paid yet, and what should I do next?"}'
```

Expected:

- HTTP `200`.
- `status` is `completed`.
- `actions` contains `invoice_lookup`, `po_lookup`, `policy_lookup`, and `draft_email`.
- `draftEmail.to` is `john.smith@example.com`.
- `draftEmail.subject` references `INV-1001`.
- `draftEmail.body` is polite, includes invoice and PO context, and states that it has not been sent.

### 6.2 Pending Approval

Request body:

```json
{
  "userRequest": "Why is INV-1002 not paid?"
}
```

Expected:

- HTTP `200`.
- `status` is `completed`.
- Final answer mentions pending approval.
- No `draftEmail` field.
- Actions are `invoice_lookup`, `po_lookup`, and `policy_lookup`.

### 6.3 Paid Invoice

Request body:

```json
{
  "userRequest": "Please check invoice INV-1003"
}
```

Expected:

- HTTP `200`.
- Final answer says the invoice is already paid and no further action is required.
- Only `invoice_lookup` is called.

### 6.4 Missing or Invalid Invoice ID

Use these request bodies:

```json
{ "userRequest": "Please check why this invoice is not paid" }
```

```json
{ "userRequest": "Please check invoice INV-ABC" }
```

Expected:

- Missing invoice ID returns `400`, `needs_input`, `MISSING_INVOICE_ID`, and no actions.
- Invalid invoice format returns `422`, `failed`, `INVALID_INVOICE_ID`, and no actions.

### 6.5 Trace Retrieval

After any successful or failed run, copy the returned `traceId` and call:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/agent/traces/<traceId>" `
  -Method Get
```

Expected:

- HTTP `200`.
- Response includes `traceId`, `userInput`, `goal`, `steps`, `finalAnswer`, and timestamps.
- Each step includes `stepId`, `stepName`, `toolName`, `input`, `output`, `status`, `error`, `startedAt`, and `durationMs`.

Note: traces are stored in backend memory. Restarting the backend clears previously generated trace IDs.

## 7. Manual Frontend End-to-End Test

Start backend:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Start frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Manual test flow:

1. Enter:

   ```text
   Please check invoice INV-1001. Why is it not paid yet, and what should I do next?
   ```

2. Click `Ask agent` or `Run agent`, depending on the current UI text.
3. Verify that the final answer mentions `ABC Logistics`, the PO amount mismatch, `PO-9001`, and `john.smith@example.com`.
4. Verify that the Actions panel shows each tool call and whether it succeeded.
5. Click one action and verify that only `Trace ID` and `Step ID` are shown, not full tool input or output.
6. Verify that the Email draft panel appears.
7. Edit `to`, `subject`, and `body`; the fields should remain editable.
8. Before clicking the trace details button, verify that full input/output JSON is hidden.
9. Click `Show trace details` or `Query execution trace`.
10. Verify that the Execution trace block shows each step's input and output JSON.

Repeat with `INV-1002`:

- Final answer should mention pending approval.
- Actions should not include `draft_email`.
- Email draft block should not appear.

Repeat with an empty request:

- Frontend should show a validation error.
- No API call should be made.

## 8. Docker Compose Test

Run from the repository root:

```powershell
docker compose up --build
```

Expected:

- Backend container starts as `finance-agent-backend`.
- Frontend container starts as `finance-agent-frontend`.
- Backend is reachable at `http://127.0.0.1:8000`.
- Frontend is reachable at `http://127.0.0.1:5173`.
- Frontend can call `/agent/run` through the Nginx proxy.

Stop containers:

```powershell
docker compose down
```

## 10. Notes

- The backend trace store is in memory, so trace IDs are not valid after backend restart.
- The `draft_email` tool never sends email; tests should only verify generated draft content.
- The frontend intentionally hides trace input and output until the user explicitly requests trace details.
