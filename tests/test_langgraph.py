import json
import unittest

try:
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langgraph.graph import START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode, tools_condition
except ImportError:  # the langgraph extra is optional
    StateGraph = None

from langchain_fxmacrodata import fxmacrodata_tools


@unittest.skipIf(StateGraph is None, "install the langgraph extra")
class LangGraphTests(unittest.TestCase):
    def test_tool_node_runs_a_tool_call_and_returns_the_body(self) -> None:
        body = '{"currency":"USD","indicators":[]}'
        seen = []

        def transport(method, url, key):
            seen.append((method, url, key))
            return 200, body

        tools = fxmacrodata_tools(transport=transport)

        def agent(state):
            # Stands in for a chat model bound with the tools: one tool call, then an answer.
            if not any(isinstance(message, ToolMessage) for message in state["messages"]):
                call = {
                    "name": "fxmacrodata_data_catalogue_currency",
                    "args": {"currency": "USD"},
                    "id": "call-1",
                    "type": "tool_call",
                }
                return {"messages": [AIMessage(content="", tool_calls=[call])]}
            return {"messages": [AIMessage(content="done")]}

        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent)
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
        result = graph.compile().invoke({"messages": [HumanMessage(content="What USD data is there?")]})

        tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0].content, body)
        self.assertEqual(json.loads(tool_messages[0].content)["currency"], "USD")
        self.assertEqual(result["messages"][-1].content, "done")
        self.assertEqual(seen, [("GET", "https://api.fxmacrodata.com/v1/data_catalogue/USD", None)])


if __name__ == "__main__":
    unittest.main()
