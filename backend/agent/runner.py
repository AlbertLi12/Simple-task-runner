from dataclasses import dataclass
from typing import Any

from backend.agent.context import AgentContext
from backend.agent.errors import (
    AgentError,
    invoice_not_found,
    policy_not_found,
    tool_execution_failure,
)
from backend.agent.planner import RuleBasedPlanner
from backend.agent.trace import ExecutionTrace, TraceRecorder
from backend.tools.registry import ToolRegistry


@dataclass
class AgentRunResult:
    status: str
    final_answer: str
    actions: list[dict[str, str]]
    trace_id: str
    error: AgentError | None = None
    http_status: int = 200
    draft_email: dict[str, Any] | None = None

    def to_response(self) -> dict[str, Any]:
        response = {
            "status": self.status,
            "finalAnswer": self.final_answer,
            "actions": self.actions,
            "traceId": self.trace_id,
        }
        if self.draft_email:
            response["draftEmail"] = self.draft_email
        if self.error:
            response["error"] = self.error.to_dict()
        return response


class AgentRunner:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.planner = RuleBasedPlanner()
        self.traces: dict[str, ExecutionTrace] = {}

    def run(self, user_request: str) -> AgentRunResult:
        context = AgentContext(user_input=user_request)
        recorder = TraceRecorder(user_request, context.goal)
        actions: list[dict[str, str]] = []

        # Validate the request before any tool is called.
        invoice_id, parse_error = self.planner.parse_invoice_id(user_request)
        if parse_error:
            answer = parse_error.message
            trace = recorder.finish(answer, parse_error)
            self.traces[trace.traceId] = trace
            status = "needs_input" if parse_error.errorCode == "MISSING_INVOICE_ID" else "failed"
            http_status = 400 if status == "needs_input" else 422
            return AgentRunResult(status, answer, actions, trace.traceId, parse_error, http_status)

        context.invoice_id = invoice_id

        # Execute one planned tool at a time so each observation can change the next step.
        while True:
            next_steps = self.planner.next_tools(context)
            if not next_steps:
                break

            tool_name, tool_input = next_steps[0]
            output = recorder.record_tool_call(
                tool_name,
                tool_input,
                lambda name=tool_name, data=tool_input: self.registry.execute(name, data),
            )
            status = "failed" if isinstance(output, dict) and output.get("error") else "success"
            recorded_step = recorder.trace.steps[-1]
            # Expose lightweight action metadata without leaking tool inputs or outputs.
            actions.append(
                {
                    "type": tool_name,
                    "status": status,
                    "traceId": recorder.trace.traceId,
                    "stepId": recorded_step.stepId,
                }
            )

            stop_result = self._observe_tool_result(tool_name, output, context, recorder, actions)
            if stop_result:
                self.traces[stop_result.trace_id] = recorder.trace
                return stop_result

        # Build the business-readable recommendation after the context has all observations.
        final_answer = self._build_final_answer(context)
        trace = recorder.finish(final_answer)
        self.traces[trace.traceId] = trace
        return AgentRunResult(
            "completed",
            final_answer,
            actions,
            trace.traceId,
            draft_email=context.observations.get("draftEmail"),
        )

    def get_trace(self, trace_id: str) -> ExecutionTrace | None:
        return self.traces.get(trace_id)

    def _observe_tool_result(
        self,
        tool_name: str,
        output: dict[str, Any],
        context: AgentContext,
        recorder: TraceRecorder,
        actions: list[dict[str, str]],
    ) -> AgentRunResult | None:
        if not isinstance(output, dict):
            return self._fail_with_tool_error("Tool returned a non-object result.", recorder, actions)

        error_data = output.get("error")
        if error_data:
            return self._handle_tool_error(tool_name, error_data, context, recorder, actions)

        if tool_name == "invoice_lookup":
            required = {"invoiceId", "vendor", "amount", "currency", "status"}
            if not required.issubset(output):
                return self._fail_with_tool_error("Invoice lookup returned an unexpected result.", recorder, actions)
            context.observations["invoice"] = output
        elif tool_name == "po_lookup":
            if "poId" not in output or "owner" not in output:
                return self._fail_with_tool_error("PO lookup returned an unexpected result.", recorder, actions)
            context.observations["po"] = output
        elif tool_name == "policy_lookup":
            if "policy" not in output or "recommendedAction" not in output:
                return self._fail_with_tool_error("Policy lookup returned an unexpected result.", recorder, actions)
            context.observations["policy"] = output
        elif tool_name == "draft_email":
            if "to" not in output or "subject" not in output or "body" not in output:
                return self._fail_with_tool_error("Draft email returned an unexpected result.", recorder, actions)
            context.observations["draftEmail"] = output

        return None

    def _handle_tool_error(
        self,
        tool_name: str,
        error_data: dict[str, Any],
        context: AgentContext,
        recorder: TraceRecorder,
        actions: list[dict[str, str]],
    ) -> AgentRunResult:
        error = AgentError(**error_data)
        if tool_name == "invoice_lookup" and error.errorCode == "INVOICE_NOT_FOUND":
            answer = error.message
            trace = recorder.finish(answer, error)
            return AgentRunResult("failed", answer, actions, trace.traceId, error, 404)

        if tool_name == "policy_lookup" and error.errorCode == "POLICY_NOT_FOUND":
            invoice = context.observations.get("invoice", {})
            po = context.observations.get("po", {})
            # Finance can still act on invoice and PO facts when policy lookup is unavailable.
            answer = (
                f"Invoice {invoice.get('invoiceId')} for {invoice.get('vendor')} is not paid yet "
                f"because it is {self._human_status(invoice)}. PO owner: {po.get('owner', 'unknown')}. "
                "Policy information is unavailable, so confirm the correct finance policy before proceeding."
            )
            trace = recorder.finish(answer, error)
            return AgentRunResult("partial", answer, actions, trace.traceId, error, 200)

        trace = recorder.finish(error.message, error)
        return AgentRunResult("failed", error.message, actions, trace.traceId, error, 500)

    def _fail_with_tool_error(
        self, message: str, recorder: TraceRecorder, actions: list[dict[str, str]]
    ) -> AgentRunResult:
        error = tool_execution_failure(message)
        trace = recorder.finish(message, error)
        return AgentRunResult("failed", message, actions, trace.traceId, error, 500)

    def _build_final_answer(self, context: AgentContext) -> str:
        invoice = context.observations["invoice"]
        if invoice["status"] == "paid":
            return (
                f"Invoice {invoice['invoiceId']} for {invoice['vendor']} is already paid. "
                "No further action is required."
            )

        po = context.observations.get("po", {})
        policy = context.observations.get("policy", {})
        draft = context.observations.get("draftEmail")
        email_note = f" A draft email is ready for {draft['to']}." if draft else ""
        return (
            f"Invoice {invoice['invoiceId']} for {invoice['vendor']} is not paid yet because it is "
            f"{self._human_status(invoice)}. The invoice amount is {invoice['amount']} {invoice['currency']}; "
            f"PO {po.get('poId')} is {po.get('amount')} {po.get('currency')} and owned by {po.get('owner')}. "
            f"Policy: {policy.get('policy')} Suggested next step: {policy.get('recommendedAction')}"
            f"{email_note}"
        )

    def _human_status(self, invoice: dict[str, Any]) -> str:
        reason = invoice.get("blockReason")
        if reason == "PO_AMOUNT_MISMATCH":
            return "blocked because the invoice amount is higher than the PO amount"
        if reason == "APPROVAL_PENDING":
            return "pending approval"
        return str(invoice.get("status", "unknown")).replace("_", " ")
