import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

import App from "./App";

const successResponse = {
  status: "completed",
  finalAnswer:
    "Invoice INV-1001 for ABC Logistics is not paid yet because it is blocked because the invoice amount is higher than the PO amount. Suggested next step: Contact PO owner.",
  actions: [
    { type: "invoice_lookup", status: "success", traceId: "trace-123", stepId: "step-001" },
    { type: "po_lookup", status: "success", traceId: "trace-123", stepId: "step-002" },
    { type: "policy_lookup", status: "success", traceId: "trace-123", stepId: "step-003" },
    { type: "draft_email", status: "success", traceId: "trace-123", stepId: "step-004" }
  ],
  traceId: "trace-123",
  draftEmail: {
    to: "john.smith@example.com",
    subject: "Action needed: PO amount mismatch for INV-1001",
    body: "Hi John, invoice INV-1001 from ABC Logistics is blocked because the invoice amount is 12000 EUR while PO PO-9001 is 10000 EUR. Please confirm whether the PO should be amended before payment proceeds."
  }
};

const traceResponse = {
  traceId: "trace-123",
  userInput: "Please check invoice INV-1001",
  goal: "Investigate invoice payment status",
  finalAnswer: successResponse.finalAnswer,
  error: null,
  steps: [
    {
      stepId: "step-001",
      stepName: "invoice_lookup",
      toolName: "invoice_lookup",
      input: { invoiceId: "INV-1001" },
      output: { invoiceId: "INV-1001", status: "blocked" },
      status: "success",
      error: null,
      startedAt: "2026-06-28T10:00:00Z",
      durationMs: 8
    },
    {
      stepId: "step-002",
      stepName: "policy_lookup",
      toolName: "policy_lookup",
      input: { blockReason: "PO_AMOUNT_MISMATCH" },
      output: { recommendedAction: "Contact PO owner." },
      status: "success",
      error: null,
      startedAt: "2026-06-28T10:00:01Z",
      durationMs: 5
    }
  ]
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Finance agent frontend", () => {
  test("shows action statuses immediately and loads trace details only when requested", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(successResponse))
      .mockResolvedValueOnce(jsonResponse(traceResponse));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    await userEvent.type(
      screen.getByLabelText(/finance request/i),
      "Please check invoice INV-1001"
    );
    await userEvent.click(screen.getByRole("button", { name: /run agent/i }));

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/agent/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ userRequest: "Please check invoice INV-1001" })
      })
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const finalAnswer = await screen.findByRole("article", { name: /final answer/i });
    expect(within(finalAnswer).getByText(/ABC Logistics/)).toBeInTheDocument();
    const emailDraft = screen.getByRole("region", { name: /email draft/i });
    expect(emailDraft).toBeInTheDocument();
    expect(within(emailDraft).getByLabelText(/^to$/i)).toHaveValue("john.smith@example.com");
    expect(within(emailDraft).getByLabelText(/^subject$/i)).toHaveValue(
      "Action needed: PO amount mismatch for INV-1001"
    );
    expect(within(emailDraft).getByLabelText(/^body$/i)).toHaveValue(
      successResponse.draftEmail.body
    );

    await userEvent.clear(within(emailDraft).getByLabelText(/^to$/i));
    await userEvent.type(within(emailDraft).getByLabelText(/^to$/i), "owner@example.com");
    await userEvent.clear(within(emailDraft).getByLabelText(/^subject$/i));
    await userEvent.type(within(emailDraft).getByLabelText(/^subject$/i), "Please review INV-1001");
    await userEvent.clear(within(emailDraft).getByLabelText(/^body$/i));
    await userEvent.type(within(emailDraft).getByLabelText(/^body$/i), "Can you amend the PO?");

    expect(within(emailDraft).getByLabelText(/^to$/i)).toHaveValue("owner@example.com");
    expect(within(emailDraft).getByLabelText(/^subject$/i)).toHaveValue("Please review INV-1001");
    expect(within(emailDraft).getByLabelText(/^body$/i)).toHaveValue("Can you amend the PO?");

    const actions = screen.getByRole("article", { name: /actions/i });
    expect(
      within(actions).getByRole("button", { name: /invoice_lookup success/i })
    ).toBeInTheDocument();
    expect(
      within(actions).getByRole("button", { name: /policy_lookup success/i })
    ).toBeInTheDocument();

    await userEvent.click(within(actions).getByRole("button", { name: /invoice_lookup success/i }));
    expect(screen.getByText(/Selected action/)).toBeInTheDocument();
    expect(within(actions).getByText(/trace-123/)).toBeInTheDocument();
    expect(within(actions).getByText(/step-001/)).toBeInTheDocument();
    expect(screen.queryByText(/PO_AMOUNT_MISMATCH/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /query execution trace/i }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/agent/traces/trace-123");

    const trace = screen.getByRole("region", { name: /execution trace/i });
    expect(await within(trace).findByText("invoice_lookup")).toBeInTheDocument();
    expect(within(trace).getByText("policy_lookup")).toBeInTheDocument();
    expect(within(trace).getByText(/8 ms/)).toBeInTheDocument();
    expect(within(trace).getByText(/PO_AMOUNT_MISMATCH/)).toBeInTheDocument();
  });

  test("shows structured API errors clearly and keeps actions visible", async () => {
    const notFoundResponse = {
      status: "failed",
      finalAnswer: "Invoice INV-9999 was not found.",
      actions: [
        { type: "invoice_lookup", status: "failed", traceId: "trace-404", stepId: "step-001" }
      ],
      traceId: "trace-404",
      error: {
        errorCode: "INVOICE_NOT_FOUND",
        message: "Invoice INV-9999 was not found.",
        recoverable: true
      }
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(jsonResponse(notFoundResponse, false, 404))
    );

    render(<App />);
    await userEvent.type(screen.getByLabelText(/finance request/i), "Check INV-9999");
    await userEvent.click(screen.getByRole("button", { name: /run agent/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("INVOICE_NOT_FOUND");
    expect(
      within(screen.getByRole("article", { name: /final answer/i })).getByText(
        /Invoice INV-9999 was not found/
      )
    ).toBeInTheDocument();
    expect(screen.getByText("invoice_lookup")).toBeInTheDocument();
  });

  test("does not show an email draft when the backend does not return one", async () => {
    const pendingApprovalResponse = {
      status: "completed",
      finalAnswer: "Invoice INV-1002 is pending approval.",
      actions: [
        { type: "invoice_lookup", status: "success", traceId: "trace-456", stepId: "step-001" },
        { type: "po_lookup", status: "success", traceId: "trace-456", stepId: "step-002" },
        { type: "policy_lookup", status: "success", traceId: "trace-456", stepId: "step-003" }
      ],
      traceId: "trace-456"
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse(pendingApprovalResponse)));

    render(<App />);
    await userEvent.type(screen.getByLabelText(/finance request/i), "Check INV-1002");
    await userEvent.click(screen.getByRole("button", { name: /run agent/i }));

    expect(await screen.findByText(/pending approval/i)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /email draft/i })).not.toBeInTheDocument();
  });

  test("prevents empty submissions before calling the backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /run agent/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/enter a request/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body
  } as Response;
}
