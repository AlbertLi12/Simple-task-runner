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
        po_id = purchase_order["poId"]
        po_amount = f"{purchase_order['amount']} {purchase_order['currency']}"
        invoice_amount = f"{invoice['amount']} {invoice['currency']}"
        first_name = owner.split("@", maxsplit=1)[0].split(".", maxsplit=1)[0].title()
        subject_reason = invoice.get("blockReason", "invoice follow-up").replace("_", " ").lower()
        if invoice.get("blockReason") == "PO_AMOUNT_MISMATCH":
            subject_reason = "PO amount mismatch"

        # The tool only drafts a message; sending remains a user decision.
        return {
            "to": owner,
            "subject": f"Action needed: {subject_reason} for {invoice_id}",
            "body": (
                f"Hi {first_name},\n\n"
                "I hope you are well.\n\n"
                f"I am following up on invoice {invoice_id} from {invoice['vendor']}. "
                f"The invoice is currently blocked because the invoice amount is "
                f"{invoice_amount}, while PO {po_id} is {po_amount}. "
                f"{policy['policy']}\n\n"
                f"Could you please confirm whether PO {po_id} should be amended, or let us "
                "know if there is another action finance should take before payment can "
                f"proceed? The current recommended action is: {policy['recommendedAction']}\n\n"
                "Thanks,\nFinance Operations\n\n"
                "This is only a draft and has not been sent."
            ),
        }
