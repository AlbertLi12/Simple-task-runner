from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    user_request: str = Field(default="", alias="userRequest")


router = APIRouter()


@router.post("/agent/run")
def run_agent(payload: AgentRunRequest, request: Request):
    result = request.app.state.agent_runner.run(payload.user_request)
    status_code = {
        "completed": 200,
        "partial": 200,
        "needs_input": 400,
        "failed": result.http_status,
    }.get(result.status, 500)
    return JSONResponse(status_code=status_code, content=result.to_response())


@router.get("/agent/traces/{trace_id}")
def get_trace(trace_id: str, request: Request):
    trace = request.app.state.agent_runner.get_trace(trace_id)
    if trace is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "failed",
                "error": {
                    "errorCode": "TRACE_NOT_FOUND",
                    "message": f"Trace {trace_id} was not found.",
                    "recoverable": True,
                },
            },
        )
    return trace.to_dict()
