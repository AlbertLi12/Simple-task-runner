from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    user_input: str
    invoice_id: str | None = None
    goal: str = "Investigate why the invoice is not paid and recommend next action."
    observations: dict[str, Any] = field(default_factory=dict)
