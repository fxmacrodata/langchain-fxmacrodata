"""LangChain tools for the public FXMacroData API."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.tools import StructuredTool
from pydantic import create_model

from langchain_fxmacrodata.client import OPERATIONS, call_operation, path_fields

Transport = Callable[[str, str, str | None], tuple[int, str]]


def tool_name(template: str) -> str:
    parts = []
    for part in template.strip("/").split("/"):
        parts.append(part[1:-1] if part.startswith("{") and part.endswith("}") else part)
    return "fxmacrodata_" + "_".join(parts[1:])


def fxmacrodata_tools(transport: Transport | None = None) -> list[StructuredTool]:
    """One LangChain tool for every public REST operation this client can send."""
    tools = []
    for method, template, query_names in OPERATIONS:
        if method != "GET":
            continue
        fields = {name: (str, ...) for name in path_fields(template)}
        for name in query_names.split():
            fields[name] = (str, "")
        if template == "/v1/stream/events":
            fields["last_event_id"] = (str, "")
        schema = create_model(tool_name(template) + "_args", **fields)
        description = (
            f"Read FXMacroData {method} {template}. "
            "USD catalogue, USD macro history and the USD release calendar work with no API key. "
            "An optional FXMACRODATA_API_KEY is sent as a header for protected data. "
            "The response body is returned unchanged."
        )

        def run(_template=template, _query=query_names, **kwargs: str) -> str:
            return call_operation(_template, _query, kwargs, transport)

        tools.append(
            StructuredTool.from_function(
                func=run,
                name=tool_name(template),
                description=description,
                args_schema=schema,
                infer_schema=False,
            )
        )
    return tools
