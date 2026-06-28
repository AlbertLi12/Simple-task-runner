# Agent Implementation Guide

This repository should implement a finance operations prototype where a user can ask why an invoice has not been paid yet. The agent must investigate the invoice, call registered tools, keep a structured execution trace, and return a business-readable recommendation.

Use `codexdoc/Goal.md` as the source requirement.

## Product Goal

Support requests such as:

```text
Please check invoice INV-1001. Why is it not paid yet, and what should I do next?
```

The agent should extract the invoice ID, understand the user's goal, decide which tools to call, use tool results as observations, save a structured trace, and return a clear final answer for a finance operations user.

## Required Stack

- Backend: Python, FastAPI, Pydantic
- Frontend: React, TypeScript, Vite, TailwindCSS
- API style: REST
- Storage: mock JSON files
- Backend tests: Pytest and FastAPI TestClient
- Frontend tests: React Testing Library
- DevOps: Docker and Docker Compose
- Code quality: ESLint and Prettier

Do not call a real LLM API. Implement a mock planner or rule-based planner.

## Expected Structure

Implement the project in a modular, reviewable structure similar to:

```text
backend/
  api/
    routes.py
  agent/
    runner.py
    planner.py
    context.py
    trace.py
    errors.py
  tools/
    base.py
    registry.py
    invoice_lookup.py
    po_lookup.py
    policy_lookup.py
    draft_email.py
  data/
    invoices.json
    purchase_orders.json
    policies.json
  tests/
frontend/
README.md
```

Small deviations are acceptable when they keep the implementation simpler and equally clear.

## Backend API

Expose these endpoints:

- `POST /agent/run`
  - Request body includes `userRequest`.
  - Response includes `status`, `finalAnswer`, `actions`, and `traceId` on success.
  - Return structured errors where appropriate.
- `GET /agent/traces/{traceId}`
  - Return the full execution trace.
  - Include user input, selected tools, tool inputs, tool outputs, errors, timestamps, durations, and final answer.

## Mock Data

Include JSON mock data for invoices, purchase orders, and policies.

Required invoices:

- `INV-1001`: blocked, vendor `ABC Logistics`, amount `12000 EUR`, PO `PO-9001`, block reason `PO_AMOUNT_MISMATCH`
- `INV-1002`: pending approval, vendor `Global Parts Ltd.`, amount `5000 USD`, PO `PO-9002`, block reason `APPROVAL_PENDING`
- `INV-1003`: paid, vendor `Fast Office Supplies`, amount `800 EUR`, PO `PO-9003`, no block reason

Required purchase orders:

- `PO-9001`: amount `10000 EUR`, owner `john.smith@example.com`, active
- `PO-9002`: amount `5000 USD`, owner `mary.chen@example.com`, active
- `PO-9003`: amount `800 EUR`, owner `peter.mueller@example.com`, closed

Required policies:

- `PO_AMOUNT_MISMATCH`: requester must confirm whether the PO should be amended before payment proceeds; recommend contacting the PO owner.
- `APPROVAL_PENDING`: payment cannot proceed until the responsible approver completes approval; recommend reminding the approver.

## Tools

Implement a simple `ToolRegistry`. The agent must call tools through the registry rather than importing and invoking tool implementations directly from planner logic.

Each tool should expose at least:

- `name`
- `description`
- input schema or input type
- `execute(input)`

Required tools:

- `invoice_lookup`: accepts `invoiceId`, returns invoice details or a structured not-found error.
- `po_lookup`: accepts `poId`, returns purchase order details or a structured error.
- `policy_lookup`: accepts `blockReason`, returns policy details or a structured policy-not-found error.
- `draft_email`: generates a draft email to the PO owner. It must not send email.

## Agent Behavior

The planner can be rule-based. It should not always call every tool.

Expected flow:

```text
User request
-> Extract invoice ID
-> Create task goal
-> Plan next step
-> Call tool
-> Observe result
-> Update context
-> Decide next step
-> Generate final answer
-> Save trace
```

Required dynamic behavior:

- Missing invoice ID: ask the user to provide an invoice ID; do not call tools.
- Invalid invoice ID format: return a clear validation error.
- Invoice not found: stop after invoice lookup failure.
- Paid invoice: do not call policy lookup; say no further action is required.
- Blocked invoice with PO: call invoice lookup, PO lookup, and policy lookup.
- Policy lookup failure: return a partial answer and clearly state that policy information is unavailable.

Lowercase invoice IDs and extra spaces should be handled gracefully.

## Errors

Return structured errors where appropriate. At minimum, support:

- `MISSING_INVOICE_ID`
- `INVALID_INVOICE_ID`
- `INVOICE_NOT_FOUND`
- `TOOL_EXECUTION_FAILURE`
- `POLICY_NOT_FOUND`

Error objects should include an error code, a human-readable message, and whether the issue is recoverable.

## Trace Requirements

The trace must be structured data, not a plain text log.

Each trace step should include:

- `stepId`
- `stepName`
- `toolName`
- `input`
- `output`
- `status`
- `error`
- `startedAt`
- `durationMs`

The trace should make it clear to another engineer how the agent reached its answer.

## Frontend

Build a minimal, clean, usable frontend with:

- Text box for the user request
- Submit button
- Final answer display
- Execution trace display in a readable format
- Clear error display

Avoid complex styling. Prioritize clarity and usability.

## Tests

Include at least six meaningful tests. Cover all required backend behavior and add frontend tests for the core request flow if the frontend is implemented.

Required scenarios:

- `INV-1001`: blocked because of PO amount mismatch.
- `INV-1002`: pending approval.
- `INV-1003`: paid, no further action required.
- `INV-9999`: invoice not found.
- Missing invoice ID.
- Simulated policy lookup failure.
- Invalid invoice format.
- Lowercase invoice ID.
- Extra spaces in the request.
- Unexpected tool result.
- Empty user request.

## Repository Hygiene

Keep generated and environment-specific files out of version control, including dependency directories, virtual environments, caches, logs, and agent planning artifacts. Respect the existing `.gitignore` rules.

## Code Comments

- Add comments for important agent workflow steps
- Keep comments short and focused on business logic

- Do not leave temporary debugging comments or commented-out code
