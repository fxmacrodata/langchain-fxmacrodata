"""LangChain tools for the public FXMacroData API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import ConfigDict, Field, create_model

from langchain_fxmacrodata.schemas import ResearchPanelRequest

from langchain_fxmacrodata.client import OPERATIONS, call_operation, path_fields

Transport = Callable[[str, str, str | None], tuple[int, str]]


def tool_name(template: str) -> str:
    parts = []
    for part in template.strip("/").split("/"):
        parts.append(part[1:-1] if part.startswith("{") and part.endswith("}") else part)
    return "fxmacrodata_" + "_".join(parts[1:])


JSONTransport = Callable[[str, str, str | None, dict], tuple[int, str]]


def fxmacrodata_tools(transport: Transport | None = None, *, json_transport: JSONTransport | None = None) -> list[StructuredTool]:
    """One LangChain tool for every public REST operation this client can send."""
    tools = []
    for method, template, query_names in OPERATIONS:
        if method == "POST":
            def research_panel(**kwargs) -> str:
                return call_operation("/v1/research/panel", "", kwargs, json_transport=json_transport)

            tools.append(StructuredTool.from_function(
                func=research_panel,
                name=tool_name(template),
                description=("Build a point-in-time macro research panel for up to six currency/indicator "
                             "series at supplied decision times and within a date window. "
                             "Choose public or captured availability and an optional dataset version. "
                             "Returns the API JSON body unchanged; access depends on your entitlement."),
                args_schema=ResearchPanelRequest,
                infer_schema=False,
            ))
            continue
        fields = {name: (str, ...) for name in path_fields(template)}
        for name in query_names.split():
            fields[name] = (str, "")
        if template == "/v1/stream/events":
            fields["last_event_id"] = (str, "")
        if "date_basis" in fields:
            fields["date_basis"] = (
                Literal["", "effective_date", "meeting_date"],
                Field(default="", description="Use only conventions declared by this indicator's catalogue; each reads its own stored series."),
            )
        schema = create_model(tool_name(template) + "_args", __config__=ConfigDict(extra="forbid"), **fields)
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
