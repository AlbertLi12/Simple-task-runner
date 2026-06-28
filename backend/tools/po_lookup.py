from typing import Any

from backend.agent.errors import tool_execution_failure
from backend.tools.data_loader import load_json


class POLookupTool:
    name = "po_lookup"
    description = "Look up purchase order details by PO ID."
    input_schema = {"poId": "string"}

    def __init__(self, purchase_orders: list[dict[str, Any]] | None = None):
        self.purchase_orders = (
            purchase_orders if purchase_orders is not None else load_json("purchase_orders.json")
        )

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        po_id = str(tool_input.get("poId", "")).upper()
        for purchase_order in self.purchase_orders:
            if purchase_order["poId"] == po_id:
                return dict(purchase_order)
        return {
            "error": tool_execution_failure(f"Purchase order {po_id} was not found.").to_dict()
        }
