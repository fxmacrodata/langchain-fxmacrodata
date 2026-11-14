import json
import os
import unittest
import urllib.parse
import urllib.error
from unittest import mock

from pydantic import ValidationError
from langchain_fxmacrodata import fxmacrodata_tools
from langchain_fxmacrodata.client import API_ORIGIN, FXMacroDataError, request


def panel_args():
    return {
        'series': [{'currency': 'USD', 'indicator': 'inflation'}],
        'decision_times': ['2026-11-10T12:00:00Z'],
        'start_date': '2026-10-01', 'end_date': '2026-11-10',
    }


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'FXMACRODATA_API_KEY': ''})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_research_tool_preserves_json_body_and_response(self):
        seen = []
        def send(*args):
            seen.append(args)
            return 200, '{"panel":[],"available":false}'
        tool = next(t for t in fxmacrodata_tools(json_transport=send) if t.name == 'fxmacrodata_research_panel')
        args = panel_args()
        args['series'][0].update(max_age_days=0, period_aggregation='monthly')
        args.update(availability='captured', dataset_version='a' * 64)
        with mock.patch.dict(os.environ, {'FXMACRODATA_API_KEY': 'fixture-key'}):
            result = tool.invoke(args)
        self.assertEqual(result, '{"panel":[],"available":false}')
        self.assertEqual(seen, [('POST', API_ORIGIN + '/v1/research/panel', 'fixture-key', args)])
        self.assertNotIn('fixture-key', json.dumps(seen[0][3]))

    def test_research_invalid_input_never_reaches_transport(self):
        send = mock.Mock(return_value=(200, '{}'))
        tool = next(t for t in fxmacrodata_tools(json_transport=send) if t.name == 'fxmacrodata_research_panel')
        bad = [
            {'series': []}, {'series': panel_args()['series'] * 7},
            {'decision_times': []}, {'decision_times': ['x'] * 10001},
            {'start_date': 'not-a-date'}, {'availability': 'guessed'},
            {'dataset_version': 'invalid'}, {'api_key': 'not-allowed'},
            {'series': [{'currency': 'USD', 'indicator': 'inflation', 'api_key': 'no'}]},
            {'series': [{'currency': 'USD', 'indicator': 'inflation', 'max_age_days': -1}]},
        ]
        for patch in bad:
            with self.subTest(patch=list(patch)):
                with self.assertRaises(ValidationError):
                    tool.invoke({**panel_args(), **patch})
        send.assert_not_called()

    def test_date_basis_is_sent_and_omission_preserves_default(self):
        send = mock.Mock(return_value=(200, '{}'))
        tool = next(t for t in fxmacrodata_tools(transport=send) if t.name == 'fxmacrodata_announcements_currency_indicator')
        args = {'currency': 'USD', 'indicator': 'policy_rate'}
        for basis in ('meeting_date', 'effective_date'):
            tool.invoke({**args, 'date_basis': basis})
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(send.call_args.args[1]).query)
            self.assertEqual(query['date_basis'], [basis])
        tool.invoke(args)
        self.assertNotIn('date_basis', send.call_args.args[1])
        send.reset_mock()
        with self.assertRaises(ValidationError):
            tool.invoke({**args, 'date_basis': 'guessed_date'})
        with self.assertRaises(ValidationError):
            tool.invoke({**args, '_template': '/v1/ping'})
        send.assert_not_called()

    def test_post_is_json_and_key_is_only_a_header(self):
        seen = []
        class Response:
            status = 200
            def read(self, limit): return b'{"panel":[]}'
            def __enter__(self): return self
            def __exit__(self, *args): pass
        def open_request(_self, req, **kwargs):
            seen.append(req)
            return Response()
        tool = next(t for t in fxmacrodata_tools() if t.name == 'fxmacrodata_research_panel')
        with mock.patch('urllib.request.OpenerDirector.open', open_request), mock.patch.dict(os.environ, {'FXMACRODATA_API_KEY': 'fixture-key'}):
            self.assertEqual(tool.invoke(panel_args()), '{"panel":[]}')
        req, = seen
        self.assertEqual(req.get_method(), 'POST')
        self.assertEqual(req.full_url, API_ORIGIN + '/v1/research/panel')
        self.assertEqual(req.get_header('X-api-key'), 'fixture-key')
        self.assertEqual(req.get_header('Content-type'), 'application/json')
        self.assertEqual(json.loads(req.data), {**panel_args(), 'availability': 'public', 'dataset_version': None})

    def test_post_cannot_target_another_route_or_origin(self):
        with mock.patch('urllib.request.OpenerDirector.open') as send:
            for method, url, body in [
                ('POST', API_ORIGIN + '/v1/ping', {}),
                ('POST', 'https://example.invalid/v1/research/panel', {}),
                ('POST', API_ORIGIN + '/v1/research/panel?api_key=fixture', {}),
                ('POST', API_ORIGIN + '/v1/research/panel', None),
                ('DELETE', API_ORIGIN + '/v1/research/panel', {}),
                ('GET', API_ORIGIN + '/v1/ping', {}),
            ]:
                with self.subTest(method=method, url=url), self.assertRaises(FXMacroDataError):
                    request(method, url, json_body=body)
            send.assert_not_called()

    def test_research_non_200_preserves_error_contract(self):
        tool = next(t for t in fxmacrodata_tools(json_transport=lambda *a: (403, '{"detail":"forbidden"}')) if t.name == 'fxmacrodata_research_panel')
        self.assertEqual(json.loads(tool.invoke(panel_args())), {'status': 403, 'body': '{"detail":"forbidden"}'})

    def test_langgraph_toolnode_runs_research_tool(self):
        from langchain_core.messages import AIMessage
        from langgraph.graph import START, END, MessagesState, StateGraph
        from langgraph.prebuilt import ToolNode
        tools = fxmacrodata_tools(json_transport=lambda *a: (200, '{"panel":[]}'))
        graph = StateGraph(MessagesState)
        graph.add_node('tools', ToolNode(tools))
        graph.add_edge(START, 'tools')
        graph.add_edge('tools', END)
        result = graph.compile().invoke({'messages': [AIMessage(content='', tool_calls=[{
            'name': 'fxmacrodata_research_panel', 'args': panel_args(),
            'id': 'research-1', 'type': 'tool_call',
        }])]})
        self.assertEqual(result['messages'][-1].content, '{"panel":[]}')


if __name__ == '__main__':
    unittest.main()
