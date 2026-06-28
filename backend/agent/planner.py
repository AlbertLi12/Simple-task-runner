import re

from backend.agent.context import AgentContext
from backend.agent.errors import invalid_invoice_id, missing_invoice_id


VALID_INVOICE_RE = re.compile(r"\bINV-\d{4}\b", re.IGNORECASE)
INVOICE_LIKE_RE = re.compile(r"\bINV-[A-Z0-9]+\b", re.IGNORECASE)


class RuleBasedPlanner:
    def parse_invoice_id(self, user_request: str):
        normalized = " ".join(user_request.strip().split())
        if not normalized:
            return None, missing_invoice_id()

        valid_match = VALID_INVOICE_RE.search(normalized)
        if valid_match:
            return valid_match.group(0).upper(), None

        invoice_like_match = INVOICE_LIKE_RE.search(normalized)
        if invoice_like_match:
            return None, invalid_invoice_id(invoice_like_match.group(0).upper())

        return None, missing_invoice_id()

    def next_tools(self, context: AgentContext) -> list[tuple[str, dict[str, object]]]:
        invoice = context.observations.get("invoice")
        po = context.observations.get("po")

        if invoice is None and context.invoice_id:
            return [("invoice_lookup", {"invoiceId": context.invoice_id})]

        if invoice.get("status") == "paid":
            return []

        if invoice.get("poId") and po is None:
            return [("po_lookup", {"poId": invoice["poId"]})]

        if invoice.get("blockReason") and "policy" not in context.observations:
            return [("policy_lookup", {"blockReason": invoice["blockReason"]})]

        if po and "policy" in context.observations and "draftEmail" not in context.observations:
            return [
                (
                    "draft_email",
                    {
                        "invoice": invoice,
                        "purchaseOrder": po,
                        "policy": context.observations["policy"],
                    },
                )
            ]

        return []
