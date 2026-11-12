# FXMacroData tools for LangChain

`langchain-fxmacrodata` is a standalone package that gives a LangChain agent the public FXMacroData API.

USD catalogue, USD macro history and the USD release calendar work with no API key and no account. For other data, set `FXMACRODATA_API_KEY` in the environment. The package sends that value as the `X-API-Key` header. A key is not a tool argument and is not written into the URL.

```python
from langchain_fxmacrodata import fxmacrodata_tools

tools = fxmacrodata_tools()
catalogue = next(tool for tool in tools if tool.name == "fxmacrodata_data_catalogue_currency")
print(catalogue.invoke({"currency": "USD"}))
```

## LangGraph

The same tools work in a LangGraph agent. Install the extra with `pip install "langchain-fxmacrodata[langgraph]"`, then pass the tools to a `ToolNode` and bind them to any chat model that supports tool calling:

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

Each tool calls one public GET route and returns the response body. A non-200 response comes back as JSON with `status` and `body`. This package does not call `POST /v1/research/panel`. The event tool can send `Last-Event-ID` and returns one response.

Requests go only to `https://api.fxmacrodata.com`.

Documentation: https://fxmacrodata.com/docs?utm_source=langchain&utm_medium=integration&utm_campaign=langchain-fxmacrodata&utm_content=readme-docs
