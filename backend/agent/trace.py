from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from backend.agent.errors import AgentError


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class TraceStep:
    stepId: str
    stepName: str
    toolName: str | None
    input: dict[str, Any]
    output: dict[str, Any] | None
    status: str
    error: dict[str, Any] | None
    startedAt: str
    durationMs: int


@dataclass
class ExecutionTrace:
    traceId: str
    userInput: str
    goal: str
    steps: list[TraceStep] = field(default_factory=list)
    error: dict[str, Any] | None = None
    finalAnswer: str | None = None
    startedAt: str = field(default_factory=utc_now_iso)
    completedAt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "traceId": self.traceId,
            "userInput": self.userInput,
            "goal": self.goal,
            "steps": [asdict(step) for step in self.steps],
            "error": self.error,
            "finalAnswer": self.finalAnswer,
            "startedAt": self.startedAt,
            "completedAt": self.completedAt,
        }


class TraceRecorder:
    def __init__(self, user_input: str, goal: str):
        self.trace = ExecutionTrace(
            traceId=f"trace-{uuid4().hex[:12]}",
            userInput=user_input,
            goal=goal,
        )

    def record_tool_call(self, tool_name: str, tool_input: dict[str, Any], call):
        step_number = len(self.trace.steps) + 1
        started_at = utc_now_iso()
        start = perf_counter()
        try:
            output = call()
            error = output.get("error") if isinstance(output, dict) else None
            status = "failed" if error else "success"
            return output
        except Exception as exc:  # pragma: no cover - defensive wrapper
            output = None
            error = {
                "errorCode": "TOOL_EXECUTION_FAILURE",
                "message": str(exc),
                "recoverable": False,
            }
            status = "failed"
            return {"error": error}
        finally:
            duration_ms = int((perf_counter() - start) * 1000)
            # Store structured evidence for trace retrieval and engineering review.
            self.trace.steps.append(
                TraceStep(
                    stepId=f"step-{step_number:03d}",
                    stepName=tool_name,
                    toolName=tool_name,
                    input=tool_input,
                    output=output,
                    status=status,
                    error=error,
                    startedAt=started_at,
                    durationMs=duration_ms,
                )
            )

    def finish(self, final_answer: str, error: AgentError | None = None):
        self.trace.finalAnswer = final_answer
        self.trace.error = error.to_dict() if error else None
        self.trace.completedAt = utc_now_iso()
        return self.trace
