import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

import App from "./App";

const successResponse = {
  status: "completed",
  finalAnswer:
    "Invoice INV-1001 for ABC Logistics is not paid yet because it is blocked because the invoice amount is higher than the PO amount. Suggested next step: Contact PO owner.",
  actions: [
    { type: "invoice_lookup", status: "success" },
    { type: "po_lookup", status: "success" },
    { type: "policy_lookup", status: "success" },
    { type: "draft_email", status: "success" }
  ],
  traceId: "trace-123"
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
  test("submits a user request and displays the final answer with readable trace steps", async () => {
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
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/agent/traces/trace-123");
    expect(await screen.findByText(/ABC Logistics/)).toBeInTheDocument();

    const trace = screen.getByRole("region", { name: /execution trace/i });
    expect(within(trace).getByText("invoice_lookup")).toBeInTheDocument();
    expect(within(trace).getByText("policy_lookup")).toBeInTheDocument();
    expect(within(trace).getByText(/8 ms/)).toBeInTheDocument();
  });

  test("shows structured API errors clearly and keeps actions visible", async () => {
    const notFoundResponse = {
      status: "failed",
      finalAnswer: "Invoice INV-9999 was not found.",
      actions: [{ type: "invoice_lookup", status: "failed" }],
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
