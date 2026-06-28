from typing import Any

from backend.agent.errors import tool_execution_failure
from backend.tools.draft_email import DraftEmailTool
from backend.tools.invoice_lookup import InvoiceLookupTool
from backend.tools.po_lookup import POLookupTool
from backend.tools.policy_lookup import PolicyLookupTool


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        self.tools[tool.name] = tool

    def execute(self, name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            return {"error": tool_execution_failure(f"Tool {name} is not registered.").to_dict()}
        return tool.execute(tool_input)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(InvoiceLookupTool())
    registry.register(POLookupTool())
    registry.register(PolicyLookupTool())
    registry.register(DraftEmailTool())
    return registry
