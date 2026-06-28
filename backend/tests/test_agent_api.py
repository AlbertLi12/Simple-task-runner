from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def run_agent(user_request: str):
    return client.post("/agent/run", json={"userRequest": user_request})


def action_types(response_json):
    return [action["type"] for action in response_json["actions"]]


# Tests the full PO amount mismatch path, including PO owner draft email generation.
def test_inv_1001_is_blocked_by_po_amount_mismatch():
    response = run_agent(
        "Please check invoice INV-1001. Why is it not paid yet, and what should I do next?"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "ABC Logistics" in body["finalAnswer"]
    assert "higher than the PO amount" in body["finalAnswer"]
    assert "john.smith@example.com" in body["finalAnswer"]
    assert action_types(body) == [
        "invoice_lookup",
        "po_lookup",
        "policy_lookup",
        "draft_email",
    ]
    assert body["draftEmail"]["to"] == "john.smith@example.com"
    assert "INV-1001" in body["draftEmail"]["subject"]
    assert "Hi John," in body["draftEmail"]["body"]
    assert "I hope you are well." in body["draftEmail"]["body"]
    assert "ABC Logistics" in body["draftEmail"]["body"]
    assert "PO-9001" in body["draftEmail"]["body"]
    assert "10000 EUR" in body["draftEmail"]["body"]
    assert "12000 EUR" in body["draftEmail"]["body"]
    assert "Could you please confirm whether PO PO-9001 should be amended" in body["draftEmail"]["body"]
    assert "This is only a draft and has not been sent." in body["draftEmail"]["body"]


# Tests the approval-pending path where policy guidance is needed but no email draft is created.
def test_inv_1002_is_pending_approval():
    response = run_agent("Why is INV-1002 not paid?")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "pending approval" in body["finalAnswer"].lower()
    assert "mary.chen@example.com" in body["finalAnswer"]
    assert action_types(body) == ["invoice_lookup", "po_lookup", "policy_lookup"]
    assert "draftEmail" not in body


# Tests that paid invoices stop after invoice lookup and require no further action.
def test_inv_1003_is_paid_without_policy_lookup():
    response = run_agent("Please check invoice INV-1003")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "already paid" in body["finalAnswer"].lower()
    assert "no further action" in body["finalAnswer"].lower()
    assert action_types(body) == ["invoice_lookup"]


# Tests that an unknown invoice stops the workflow after the failed invoice lookup.
def test_invoice_not_found_stops_after_invoice_lookup():
    response = run_agent("Please check invoice INV-9999")

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["errorCode"] == "INVOICE_NOT_FOUND"
    assert body["error"]["recoverable"] is True
    assert action_types(body) == ["invoice_lookup"]


# Tests that requests without an invoice ID ask for more input and call no tools.
def test_missing_invoice_id_does_not_call_tools():
    response = run_agent("Please check why this invoice is not paid")

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["error"]["errorCode"] == "MISSING_INVOICE_ID"
    assert body["actions"] == []


# Tests that an empty request is handled as a missing invoice ID.
def test_empty_user_request_is_missing_invoice_id():
    response = run_agent("")

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["error"]["errorCode"] == "MISSING_INVOICE_ID"
    assert body["actions"] == []


# Tests that malformed invoice IDs return a validation error before tools run.
def test_invalid_invoice_format_returns_validation_error():
    response = run_agent("Please check invoice INV-ABC")

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["errorCode"] == "INVALID_INVOICE_ID"
    assert body["actions"] == []


# Tests that lowercase invoice IDs are normalized before tool execution.
def test_lowercase_invoice_id_is_normalized():
    response = run_agent("please check invoice inv-1001")

    assert response.status_code == 200
    body = response.json()
    assert "INV-1001" in body["finalAnswer"]
    assert body["traceId"]


# Tests that extra whitespace does not prevent invoice ID extraction.
def test_extra_spaces_in_request_are_handled():
    response = run_agent("   Please   check   invoice    INV-1002    ")

    assert response.status_code == 200
    body = response.json()
    assert "INV-1002" in body["finalAnswer"]
    assert "Global Parts Ltd." in body["finalAnswer"]


# Tests that policy lookup failures return a partial answer using available invoice and PO facts.
def test_policy_lookup_failure_returns_partial_answer(monkeypatch):
    from backend.tools.registry import build_default_registry

    registry = build_default_registry()
    registry.tools["policy_lookup"].policies = []
    app.state.agent_runner.registry = registry

    response = run_agent("Please check invoice INV-1001")

    app.state.agent_runner.registry = build_default_registry()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["error"]["errorCode"] == "POLICY_NOT_FOUND"
    assert "policy information is unavailable" in body["finalAnswer"].lower()
    assert action_types(body) == ["invoice_lookup", "po_lookup", "policy_lookup"]


# Tests the data-driven policy-not-found path for an invoice with an unknown block reason.
def test_blocked_invoice_with_unknown_policy_returns_partial_answer():
    response = run_agent("Please check invoice INV-1004")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert body["error"]["errorCode"] == "POLICY_NOT_FOUND"
    assert "INV-1004" in body["finalAnswer"]
    assert "policy information is unavailable" in body["finalAnswer"].lower()
    assert "lisa.wong@example.com" in body["finalAnswer"]
    assert action_types(body) == ["invoice_lookup", "po_lookup", "policy_lookup"]


# Tests that unexpected tool output shapes become structured tool execution failures.
def test_unexpected_tool_result_is_tool_execution_failure(monkeypatch):
    from backend.tools.registry import build_default_registry

    registry = build_default_registry()

    def bad_execute(_input):
        return {"unexpected": "shape"}

    registry.tools["invoice_lookup"].execute = bad_execute
    app.state.agent_runner.registry = registry

    response = run_agent("Please check invoice INV-1001")

    app.state.agent_runner.registry = build_default_registry()
    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["errorCode"] == "TOOL_EXECUTION_FAILURE"


# Tests that saved traces expose the structured step-by-step tool execution history.
def test_trace_endpoint_returns_structured_steps():
    run_response = run_agent("Please check invoice INV-1001")
    trace_id = run_response.json()["traceId"]

    trace_response = client.get(f"/agent/traces/{trace_id}")

    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["traceId"] == trace_id
    assert trace["userInput"]
    assert trace["finalAnswer"]
    assert [step["toolName"] for step in trace["steps"]] == [
        "invoice_lookup",
        "po_lookup",
        "policy_lookup",
        "draft_email",
    ]
    assert all("startedAt" in step for step in trace["steps"])
    assert all("durationMs" in step for step in trace["steps"])


# Tests that run responses include trace and step identifiers for frontend action drill-down.
def test_run_response_actions_include_trace_and_step_ids():
    response = run_agent("Please check invoice INV-1001")

    assert response.status_code == 200
    body = response.json()
    assert body["traceId"]
    assert [action["stepId"] for action in body["actions"]] == [
        "step-001",
        "step-002",
        "step-003",
        "step-004",
    ]
    assert all(action["traceId"] == body["traceId"] for action in body["actions"])
