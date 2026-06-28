import { FormEvent, useState } from "react";

import EmailDraft, { DraftEmail } from "./EmailDraft";

type AgentAction = {
  type: string;
  status: string;
  traceId?: string;
  stepId?: string;
};

type AgentError = {
  errorCode: string;
  message: string;
  recoverable: boolean;
};

type AgentRunResponse = {
  status: "completed" | "partial" | "needs_input" | "failed";
  finalAnswer: string;
  actions: AgentAction[];
  traceId: string;
  error?: AgentError;
  draftEmail?: DraftEmail;
};

type TraceStep = {
  stepId: string;
  stepName: string;
  toolName: string | null;
  input: unknown;
  output: unknown;
  status: string;
  error: AgentError | null;
  startedAt: string;
  durationMs: number;
};

type AgentTrace = {
  traceId: string;
  userInput: string;
  goal: string;
  finalAnswer: string;
  error: AgentError | null;
  steps: TraceStep[];
};

const exampleRequest =
  "Please check invoice INV-1001. Why is it not paid yet, and what should I do next?";

export default function App() {
  const [userRequest, setUserRequest] = useState("");
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const [trace, setTrace] = useState<AgentTrace | null>(null);
  const [selectedAction, setSelectedAction] = useState<AgentAction | null>(null);
  const [uiError, setUiError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isTraceLoading, setIsTraceLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedRequest = userRequest.trim();

    if (!trimmedRequest) {
      setUiError("Enter a request that includes an invoice ID, such as INV-1001.");
      setResult(null);
      setTrace(null);
      setSelectedAction(null);
      return;
    }

    setIsLoading(true);
    setUiError(null);
    setResult(null);
    setTrace(null);
    setSelectedAction(null);

    try {
      const runResponse = await fetch("/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userRequest: trimmedRequest })
      });
      const runData = (await runResponse.json()) as AgentRunResponse;
      setResult(runData);
    } catch {
      setUiError("The finance agent API is unavailable. Check that the backend is running.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleTraceQuery() {
    if (!result?.traceId) {
      return;
    }

    setIsTraceLoading(true);
    setUiError(null);

    try {
      const traceResponse = await fetch(`/agent/traces/${result.traceId}`);
      if (!traceResponse.ok) {
        setUiError("The execution trace could not be loaded.");
        return;
      }
      setTrace((await traceResponse.json()) as AgentTrace);
    } catch {
      setUiError("The execution trace could not be loaded.");
    } finally {
      setIsTraceLoading(false);
    }
  }

  const displayedError = result?.error
    ? `${result.error.errorCode}: ${result.error.message}`
    : uiError;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wide text-cyan-700">
            Finance Operations
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
            Invoice payment investigator
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-slate-600">
            Ask why an invoice has not been paid yet. The agent will call the backend tools and show
            both the business answer and the structured execution trace.
          </p>
        </header>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <label htmlFor="finance-request" className="block text-sm font-medium text-slate-800">
              Finance request
            </label>
            <textarea
              id="finance-request"
              className="min-h-32 w-full resize-y rounded-md border border-slate-300 bg-white p-3 text-sm leading-6 text-slate-950 outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
              placeholder={exampleRequest}
              value={userRequest}
              onChange={(event) => setUserRequest(event.target.value)}
            />
            <button
              className="inline-flex min-h-10 items-center justify-center rounded-md bg-cyan-700 px-4 text-sm font-semibold text-white transition hover:bg-cyan-800 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400"
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? "Running..." : "Run agent"}
            </button>
          </form>
        </section>

        {displayedError ? (
          <section
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900"
          >
            <h2 className="font-semibold">Error</h2>
            <p className="mt-1">{displayedError}</p>
            {result?.error ? (
              <p className="mt-2 text-red-800">
                Recoverable: {result.error.recoverable ? "Yes" : "No"}
              </p>
            ) : null}
          </section>
        ) : null}

        {result ? (
          <section className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
            <article
              aria-label="Final answer"
              className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold">Final answer</h2>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                  {result.status}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">{result.finalAnswer}</p>
              <p className="mt-4 text-xs text-slate-500">Trace ID: {result.traceId}</p>
            </article>

            <article
              aria-label="Actions"
              className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
            >
              <h2 className="text-lg font-semibold">Actions</h2>
              <ul className="mt-3 space-y-2">
                {result.actions.map((action) => (
                  <li
                    className="rounded-md bg-slate-50 text-sm"
                    key={`${action.type}-${action.status}-${action.stepId ?? action.type}`}
                  >
                    <button
                      className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left"
                      type="button"
                      onClick={() => setSelectedAction(action)}
                    >
                      <span className="font-medium text-slate-800">{action.type}</span>
                      <span
                        className={
                          action.status === "success" ? "text-emerald-700" : "text-red-700"
                        }
                      >
                        {action.status}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {selectedAction ? (
                <div className="mt-4 rounded-md border border-cyan-200 bg-cyan-50 p-3 text-xs leading-5 text-cyan-950">
                  <p className="font-semibold">Selected action</p>
                  <p>Trace ID: {selectedAction.traceId ?? result.traceId}</p>
                  <p>Step ID: {selectedAction.stepId ?? "Not provided"}</p>
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-500">
                  Select an action to view its trace and step identifiers.
                </p>
              )}
            </article>
          </section>
        ) : null}

        {result?.draftEmail ? <EmailDraft email={result.draftEmail} /> : null}

        <section
          aria-label="Execution trace"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Execution trace</h2>
            <span className="text-xs text-slate-500">
              {trace ? `${trace.steps.length} steps` : "Query the trace to load details"}
            </span>
          </div>

          {result?.traceId ? (
            <button
              className="mt-4 inline-flex min-h-9 items-center justify-center rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:text-slate-400"
              type="button"
              onClick={handleTraceQuery}
              disabled={isTraceLoading}
            >
              {isTraceLoading ? "Querying..." : "Query execution trace"}
            </button>
          ) : null}

          {trace ? (
            <ol className="mt-4 space-y-3">
              {trace.steps.map((step) => (
                <TraceStepItem key={step.stepId} step={step} />
              ))}
            </ol>
          ) : (
            <p className="mt-3 text-sm text-slate-600">
              Tool inputs and outputs stay hidden until you query this trace.
            </p>
          )}
        </section>
      </div>
    </main>
  );
}

function TraceStepItem({ step }: { step: TraceStep }) {
  return (
    <li className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">{step.toolName ?? step.stepName}</p>
          <p className="text-xs text-slate-500">
            {step.stepId} - {step.durationMs} ms - {step.status}
          </p>
        </div>
        {step.error ? (
          <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
            {step.error.errorCode}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <JsonBlock label="Input" value={step.input} />
        <JsonBlock label="Output" value={step.output} />
      </div>
    </li>
  );
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</h3>
      <pre className="mt-1 max-h-44 overflow-auto rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-100">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
