from dataclasses import asdict, dataclass


@dataclass
class AgentError:
    errorCode: str
    message: str
    recoverable: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def missing_invoice_id() -> AgentError:
    return AgentError(
        "MISSING_INVOICE_ID",
        "Please provide an invoice ID such as INV-1001.",
        True,
    )


def invalid_invoice_id(invoice_id: str) -> AgentError:
    return AgentError(
        "INVALID_INVOICE_ID",
        f"Invoice ID {invoice_id} is not valid. Use the format INV-1234.",
        True,
    )


def invoice_not_found(invoice_id: str) -> AgentError:
    return AgentError(
        "INVOICE_NOT_FOUND",
        f"Invoice {invoice_id} was not found.",
        True,
    )


def policy_not_found(block_reason: str) -> AgentError:
    return AgentError(
        "POLICY_NOT_FOUND",
        f"No policy was found for block reason {block_reason}.",
        True,
    )


def tool_execution_failure(message: str) -> AgentError:
    return AgentError("TOOL_EXECUTION_FAILURE", message, False)
