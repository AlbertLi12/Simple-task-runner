from typing import Any

from backend.agent.errors import policy_not_found
from backend.tools.data_loader import load_json


class PolicyLookupTool:
    name = "policy_lookup"
    description = "Look up finance policy by invoice block reason."
    input_schema = {"blockReason": "string"}

    def __init__(self, policies: list[dict[str, Any]] | None = None):
        self.policies = policies if policies is not None else load_json("policies.json")

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        block_reason = str(tool_input.get("blockReason", "")).upper()
        for policy in self.policies:
            if policy["blockReason"] == block_reason:
                return dict(policy)
        return {"error": policy_not_found(block_reason).to_dict()}
