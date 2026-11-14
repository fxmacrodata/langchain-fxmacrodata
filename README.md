# FXMacroData tools for LangChain

`langchain-fxmacrodata` is a standalone package that gives a LangChain agent the public FXMacroData API.

USD catalogue, USD macro history and the USD release calendar work with no API key and no account. For other data, set `FXMACRODATA_API_KEY` in the environment. The package sends that value as the `X-API-Key` header. A key is not a tool argument and is not written into the URL.

## Install and make a first call

Requires Python 3.10 or newer. Install the package into your Python environment:

```shell
python -m pip install langchain-fxmacrodata
```

No LangSmith account or model subscription is required to call a tool directly. Run this keyless USD example:

```python
from langchain_fxmacrodata import fxmacrodata_tools

tools = fxmacrodata_tools()
catalogue = next(tool for tool in tools if tool.name == "fxmacrodata_data_catalogue_currency")
print(catalogue.invoke({"currency": "USD"}))
```

## Use your own API key

For protected routes, set `FXMACRODATA_API_KEY` in your shell or secret manager before starting Python. Use your own FXMacroData key. Do not put it in a prompt, tool arguments, source code or a URL.

```python
from langchain_fxmacrodata import fxmacrodata_tools

tools = {tool.name: tool for tool in fxmacrodata_tools()}
print(tools["fxmacrodata_forex_base_quote"].invoke({"base": "EUR", "quote": "USD"}))
```

Access depends on your FXMacroData entitlement. A non-200 response contains `status` and `body`; check those before using the result as data.

## Macro date conventions

Use the indicator catalogue to check `supported_options.date_basis`. Where supported, pass `date_basis="meeting_date"` or `date_basis="effective_date"` to `fxmacrodata_announcements_currency_indicator`. Omit the selector for the API default. The conventions refer to separate stored series.

## Point-in-time research panels

`fxmacrodata_research_panel` submits a JSON body to `POST /v1/research/panel`. It validates the public request structure before sending it and returns the response unchanged:

```python
from langchain_fxmacrodata import fxmacrodata_tools

tools = {tool.name: tool for tool in fxmacrodata_tools()}
panel = tools["fxmacrodata_research_panel"].invoke({
    "series": [{"currency": "USD", "indicator": "inflation"}],
    "decision_times": ["2026-11-10T12:00:00Z"],
    "start_date": "2026-10-01",
    "end_date": "2026-11-10",
    "availability": "public",
})
print(panel)
```

Use the catalogue's indicator identifiers. Select one to six series and one to 10,000 decision times. Optional series settings are `max_age_days` and `period_aggregation`; optional panel settings are `availability` (`public` or `captured`) and `dataset_version` (a SHA-256 identifier). Panel access depends on your entitlement, and empty or unavailable results must be handled as returned.

## LangGraph

The same tools work in a LangGraph agent. Install the extra with `python -m pip install "langchain-fxmacrodata[langgraph]"`, then pass the tools to a `ToolNode` and bind them to any chat model that supports tool calling:

```python
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_fxmacrodata import fxmacrodata_tools

tools = fxmacrodata_tools()
model = chat_model.bind_tools(tools)  # your LangChain chat model


def agent(state: MessagesState):
    return {"messages": [model.invoke(state["messages"])]}


graph = StateGraph(MessagesState)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")
app = graph.compile()

app.invoke({"messages": [("user", "What USD indicators does FXMacroData cover?")]})
```

To keep a model's tool list short, pass only the tools you need, for example `[tool for tool in tools if tool.name.startswith("fxmacrodata_calendar")]`.

## Behaviour

The package exposes 42 GET tools and one research-panel POST tool. Each returns the response body unchanged. A non-200 response comes back as JSON with `status` and `body`. Requests have a 30-second timeout and a 2 MB response limit. The event tool can send `Last-Event-ID` and reads one response; it is not an incremental event iterator and an open stream can reach the timeout. Tools use synchronous HTTP; select a smaller tool subset when binding an agent. A model-backed agent uses your chosen model provider and may incur that provider's charges.

Requests go only to `https://api.fxmacrodata.com`.

Documentation: https://fxmacrodata.com/docs?utm_source=langchain&utm_medium=integration&utm_campaign=langchain-fxmacrodata&utm_content=readme-docs
