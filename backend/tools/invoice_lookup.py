from typing import Any

from backend.agent.errors import invoice_not_found
from backend.tools.data_loader import load_json


class InvoiceLookupTool:
    name = "invoice_lookup"
    description = "Look up invoice details by invoice ID."
    input_schema = {"invoiceId": "string"}

    def __init__(self, invoices: list[dict[str, Any]] | None = None):
        self.invoices = invoices if invoices is not None else load_json("invoices.json")

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        invoice_id = str(tool_input.get("invoiceId", "")).upper()
        for invoice in self.invoices:
            if invoice["invoiceId"] == invoice_id:
                return dict(invoice)
        return {"error": invoice_not_found(invoice_id).to_dict()}
