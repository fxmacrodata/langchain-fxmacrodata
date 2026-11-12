import os
import unittest
from unittest import mock

from langchain_fxmacrodata.client import OPERATIONS, build_url, call_operation
from langchain_fxmacrodata.tools import fxmacrodata_tools, tool_name


class ToolTests(unittest.TestCase):
    def test_every_get_operation_is_a_distinct_tool(self) -> None:
        tools = fxmacrodata_tools(transport=lambda method, url, key: (200, url))
        names = [tool.name for tool in tools]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(tools), sum(method == "GET" for method, _path, _query in OPERATIONS))
        self.assertGreater(len(tools), 40)
        self.assertIn("fxmacrodata_data_catalogue_currency", names)

    def test_public_catalogue_keeps_the_response_body(self) -> None:
        body = '{"indicator":"9007199254740993.0000"}'
        seen = {}

        def transport(method, url, key):
            seen["method"] = method
            seen["url"] = url
            seen["key"] = key
            return 200, body

        tool = next(item for item in fxmacrodata_tools(transport=transport) if item.name == "fxmacrodata_data_catalogue_currency")
        self.assertEqual(tool.invoke({"currency": "USD", "include_coverage": "true"}), body)
        self.assertEqual(seen["method"], "GET")
        self.assertEqual(seen["url"], "https://api.fxmacrodata.com/v1/data_catalogue/USD?include_coverage=true")
        self.assertIsNone(seen["key"])
        self.assertNotIn("api_key", seen["url"])

    def test_optional_key_is_a_header_value_not_a_url(self) -> None:
        def transport(method, url, key):
            return 200, key or ""

        with mock.patch.dict(os.environ, {"FXMACRODATA_API_KEY": "not-a-real-key"}):
            tool = next(item for item in fxmacrodata_tools(transport=transport) if item.name == tool_name("/v1/forex/{base}/{quote}"))
            self.assertEqual(tool.invoke({"base": "EUR", "quote": "USD"}), "not-a-real-key")

    def test_research_panel_is_refused(self) -> None:
        with self.assertRaises(Exception):
            call_operation("/v1/research/panel", "", {})

    def test_origin_cannot_be_replaced(self) -> None:
        with self.assertRaises(Exception):
            build_url("/v1/health", "", {}, origin="https://example.invalid")

    def test_stream_resume_id_is_a_header(self) -> None:
        captured = {}

        class _Body:
            status = 200

            def read(self, _limit):
                return b'{"events":[]}'

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        def _open(self, req, data=None, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = {key.lower(): value for key, value in req.header_items()}
            return _Body()

        tool = next(item for item in fxmacrodata_tools() if item.name == "fxmacrodata_stream_events")
        with mock.patch("urllib.request.OpenerDirector.open", _open):
            self.assertEqual(tool.invoke({"currencies": "USD", "last_event_id": "42"}), '{"events":[]}')
        self.assertEqual(captured["url"], "https://api.fxmacrodata.com/v1/stream/events?currencies=USD")
        self.assertEqual(captured["headers"].get("last-event-id"), "42")
        self.assertNotIn("last_event_id", captured["url"])


if __name__ == "__main__":
    unittest.main()
