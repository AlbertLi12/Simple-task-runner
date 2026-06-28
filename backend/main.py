from fastapi import FastAPI

from backend.agent.runner import AgentRunner
from backend.api.routes import router
from backend.tools.registry import build_default_registry


app = FastAPI(title="Finance Operations Agent")
app.state.agent_runner = AgentRunner(registry=build_default_registry())
app.include_router(router)
