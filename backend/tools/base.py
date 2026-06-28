from typing import Any, Protocol


class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, str]

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        ...
