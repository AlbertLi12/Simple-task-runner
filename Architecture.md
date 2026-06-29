# Architecture Note

## Overall Architecture

This project is a prototype of an AI Agent Task Runner for finance operations invoice investigation. 

The prototype follows a simple full-stack architecture with a React-based frontend, a FastAPI-based backend, JSON-based mock storage and in-memory storage.

The frontend provides the user simple web page for submitting invoice investigation requests and reviewing the agent answer. The backend owns the agent workflow, including request validation, invoice ID extraction, planning, tool execution, trace persistence, and final answer generation.

Agent capabilities are implemented as registered tools, such as invoice lookup, purchase order lookup, policy lookup, and draft email generation. The planner does not call tool implementations directly; instead, it uses the tool registry so the workflow remains modular and easier to extend.

No real LLM, payment system, ERP integration, or email service is used. The current demo implementation is deterministic by design, making it suitable for testing, review, and showing the expected agent behavior.

Architecture overview:

```text
[Web / React + Vite + TailwindCSS + TypeScript]
      |
      | HTTP / RESTful API
      v
[Python Backend API - FastAPI]
      |
      +--> [AgentRunner]
      |        |
      |        +--> [RuleBasedPlanner]
      |        +--> [AgentContext / Observations]
      |        +--> [TraceRecorder]
      |
      +--> [ToolRegistry]
      |        |
      |        +--> [invoice_lookup]
      |        +--> [po_lookup]
      |        +--> [policy_lookup]
      |        +--> [draft_email]
      |
      +--> [Mock JSON Data]
      |        |
      |        +--> [invoices.json]
      |        +--> [purchase_orders.json]
      |        +--> [policies.json]
      |
      +--> [In-memory Trace Store]
      |
[Docker / Nginx for composed deployment]
```



## Main Components

The backend part:

- `backend/api/routes.py` exposes `POST /agent/run` and `GET /agent/traces/{traceId}`.
- `backend/agent/runner.py` coordinates request validation, planning, tool execution, observation handling, final answer generation, and trace storage.
- `backend/agent/planner.py` contains the deterministic rule-based planner.
- `backend/agent/context.py` holds the current invoice ID, goal, and accumulated observations.
- `backend/agent/trace.py` records structured trace steps and final trace data.
- `backend/tools/registry.py` registers and invokes tools by name.
- `backend/tools/*` implement the individual tools.

The frontend part:

- `frontend/src/App.tsx` submits requests, displays final answers, shows action status, and shows trace details.
- `frontend/src/EmailDraft.tsx` renders editable `to`, `subject`, and `body` fields for email drafts.



## Agent Workflow

The agent starts by normalizing the request and extracting an invoice ID. Valid invoice IDs match `INV-####` (where `#` is number), with lowercase IDs accepted and normalized to uppercase. If no invoice ID is present, the agent returns a `needs_input` response and does not call any tools. If the request contains an invoice-like but invalid ID, it returns `INVALID_INVOICE_ID`.

For valid requests, the planner chooses one tool at a time based on the current context:

```text
[User Request]
      |
      v
[Normalize text and extract invoice ID]
      |
      +--> [Missing invoice ID]
      |        |
      |        v
      |   [Return needs_input, no tool calls]
      |
      +--> [Invalid invoice ID]
      |        |
      |        v
      |   [Return INVALID_INVOICE_ID, no tool calls]
      |
      v
[Create AgentContext + TraceRecorder]
      |
      v
[Plan next tool from current observations]
      |
      +--> [invoice_lookup]
      |        |
      |        +--> [Invoice not found -> stop with INVOICE_NOT_FOUND]
      |        +--> [Paid invoice -> final answer, no policy lookup]
      |
      +--> [po_lookup]
      |        |
      |        v
      |   [Store PO observation]
      |
      +--> [policy_lookup]
      |        |
      |        +--> [Policy not found -> partial answer]
      |        +--> [Store policy observation]
      |
      +--> [draft_email]
      |        |
      |        v
      |   [Store draftEmail observation]
      |
      v
[Record each tool call as a trace step]
      |
      v
[Build final business answer]
      |
      +--> [Return finalAnswer + actions results + traceId]
      |
      +--> [GET /agent/traces/{traceId} returns full input/output trace]
```

1. Always call `invoice_lookup` first.
2. If the invoice is paid, stop and return a no-further-action answer.
3. If the invoice has a PO, call `po_lookup`.
4. If the invoice has a block reason, call `policy_lookup`.
5. If the block reason is `PO_AMOUNT_MISMATCH` and policy plus PO data are available, call `draft_email`.
6. Build the final business answer from the accumulated observations.



## Tool Registration and Invocation

Tools are not imported and called directly from planner. The default registry is built in `build_default_registry()`, which registers:

- `InvoiceLookupTool`
- `POLookupTool`
- `PolicyLookupTool`
- `DraftEmailTool`

The runner calls tools through `ToolRegistry.execute(name, input)`. If a tool name is not registered, the registry returns a structured `TOOL_EXECUTION_FAILURE`. Each tool exposes a `name`, `description`, `input_schema`, and `execute(input)` method. This makes the tool implementation replaceable and extensible.



## Observations and Agent State

The agent state is stored in `AgentContext`. After each successful tool call, `AgentRunner._observe_tool_result()` validates the returned object shape and stores it in `context.observations`:

- `invoice_lookup` output becomes `observations["invoice"]`.
- `po_lookup` output becomes `observations["po"]`.
- `policy_lookup` output becomes `observations["policy"]`.
- `draft_email` output becomes `observations["draftEmail"]`.

If a tool returns an unexpected data, the runner converts it into `TOOL_EXECUTION_FAILURE`. This protects downstream answer generation from using wrong data.



## Execution Trace Storage

Every run creates a `TraceRecorder` with a generated `trace-...` ID. Each tool call is recorded as a structured `TraceStep` containing:

- step ID and tool name
- input and output
- status and error
- start timestamp
- duration in milliseconds

When the run finishes, the trace stores the final answer, optional error, and completion timestamp. Traces are currently stored in memory inside `AgentRunner.traces`, keyed by `traceId`. 

The frontend separates action summaries from full trace details. `POST /agent/run` returns actions results with `type`, `status`, `traceId`, and `stepId`. Full tool trace details are shown only after the user clicks the trace details button and the frontend calls `GET /agent/traces/{traceId}`.



## Error Handling Strategy

Errors are represented as structured objects with `errorCode`, `message`, and `recoverable`. The main supported error codes are:

- `MISSING_INVOICE_ID`
- `INVALID_INVOICE_ID`
- `INVOICE_NOT_FOUND`
- `POLICY_NOT_FOUND`
- `TOOL_EXECUTION_FAILURE`

The API maps these to appropriate status codes. Missing invoice ID returns `400` with `needs_input`. Invalid invoice format returns `422`. Invoice not found returns `404`. Policy lookup failure returns a `partial` response with HTTP `200`, because the invoice and PO facts are still useful to the finance user. Unexpected tool failures return `500`.



## Guardrails and Limitations

The main guardrail is a fixed, deterministic workflow. The agent cannot freely decide to call unregistered tools or generate fake intermediate results. It follows a predefined invoice-investigation flow: extract the invoice ID, validate the request, call only the required registered tools, observe the results, update context, and generate the final answer from those observations.

All tool access is routed through a fixed tool registry, similar to an MCP-style capability boundary.

**Current limitations:**

- No real LLM planner. It does not support complex and ambiguous user requests, exception handling beyond the configured cases.
- No real ERP, payment, approval, vendor management, and email systems.
- Mock JSON storage and In-memory storage only, instead of a database such as MySQL, MongoDB.
- No authentication, authorization, role-based access control, data masking, and persistent logs.
- No production monitoring, rate limiting, or secrets management.
- The frontend is intentionally simple and does not include production-grade UX.



## Production Extension

### Real LLMs

To support real LLMs, I would not replace the whole agent with a free-form chatbot. I would keep the current deterministic agent workflow and use the LLM only inside controlled boundaries. The LLM should never directly access databases or ERP APIs. It should produce structured outputs.

The production architecture should separate:

- **Intent extraction**: understand the user request and extract entities such as invoice ID, vendor, PO number, date range, or requested action.
- **Planning**: decide which registered tools are allowed and needed.
- **Tool execution**: execute allowed tools only through the registry.
- **Answer generation**: summarize verified observations into a business-readable response.

### Real ERP/SAP APIs

To support real ERP/SAP APIs, the mock lookup tools should be replaced by adapter tools that call approved ERP endpoints. Those adapters should handle authentication, retries, timeouts, pagination, and ERP-specific error mapping. Tool outputs should be normalized into stable internal schemas so the agent workflow does not depend on vendor-specific response shapes.

### Authentication and authorization

Authentication and authorization should be added at the API layer. Users should authenticate through an enterprise identity provider, and every request should be checked. The frontend would obtain an access token after login and contain it when send a request. Authorization should be business-aware. It is not enough to know that a user is logged in. The backend must decide whether the user can access the requested invoice.

### Audit log

Audit logs in production environments must be persistent, append-only, and tamper-proof. Each agent run should record request metadata, authenticated user identity, extracted intent, selected workflow steps, tool inputs and outputs, errors, timestamps, execution duration, and the final answer.

Logs should be stored in a database or logging platform. Sensitive finance, vendor, employee, or payment data should be de-identified, or encrypted according to security policies and privacy requirements.

Audit logs should not expose unnecessary personal or confidential information to users who do not need it.

### Production deployment

For production deployment, the frontend and backend should run as separate services behind a reverse proxy such as Nginx. The reverse proxy should handle TLS termination, routing, compression, request size limits, and standard security headers. 

Runtime configuration should come from environment variables or a secrets manager rather than hardcoded values. The backend should deploy multiple worker processes and configure health check endpoints to run behind a load balancer or container manage platform such as Kubernetes.

Production environment deployment should include structured logging, metrics monitoring, alerting mechanisms, error tracking, and rollback procedures.

### Monitoring and observability

The monitoring and observability framework should include structured logs, metrics, and distributed traces. Key metrics include request count, request latency, error rates, tool latency, policy-not-found rates, trace query rates, ERP timeout rate, policy-not-found rate, LLM validation failure rate and authorization denied count. Alerts should cover increased failure rates, slow ERP calls, missing policy coverage, and unavailable dependencies. Business-facing management dashboard could show top blocked invoice reasons, average investigation latency, number of drafts generated, policy gaps, such as unknown block reasons.

