from typing import Any


class DraftEmailTool:
    name = "draft_email"
    description = "Create a draft email to the PO owner without sending it."
    input_schema = {"invoice": "object", "purchaseOrder": "object", "policy": "object"}

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        invoice = tool_input["invoice"]
        purchase_order = tool_input["purchaseOrder"]
        policy = tool_input["policy"]
        owner = purchase_order["owner"]
        invoice_id = invoice["invoiceId"]
        subject_reason = invoice.get("blockReason", "invoice follow-up").replace("_", " ").lower()

        return {
            "to": owner,
            "subject": f"Action needed: {subject_reason} for {invoice_id}",
            "body": (
                f"Hi, invoice {invoice_id} for {invoice['vendor']} is currently "
                f"{invoice['status'].replace('_', ' ')}. {policy['policy']} "
                f"Recommended action: {policy['recommendedAction']}"
            ),
        }
