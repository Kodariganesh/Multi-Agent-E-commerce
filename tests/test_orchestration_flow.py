"""Unit tests for deterministic Orchestrator routing and final handoff."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import agent_orchestrator


class RecordingTool:
    """Record calls to a tool and return a stable result."""

    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def __call__(self, **arguments):
        self.calls.append((self.name, arguments))
        if self.name == 'route_to_communication_agent':
            return 'Final response from CommunicationAgent'
        return f'{self.name} completed'


class FakeOrchestrator:
    """Expose the tool registry shape used by Strands Agent."""

    def __init__(self):
        self.calls = []
        names = (
            'initialize_session',
            'route_to_inventory_agent',
            'route_to_policy_agent',
            'route_to_refund_agent',
            'route_to_communication_agent',
        )
        self.tool_registry = type(
            'ToolRegistryStub',
            (),
            {
                'registry': {
                    name: RecordingTool(name, self.calls)
                    for name in names
                }
            },
        )()


class OrchestrationFlowTests(unittest.TestCase):
    def test_return_request_routes_inventory_refund_then_communication(self):
        self.assert_route(
            'I want to return order ORD-27176',
            [
                'initialize_session',
                'route_to_inventory_agent',
                'route_to_refund_agent',
                'route_to_communication_agent',
            ],
        )

    def test_policy_question_routes_policy_then_communication(self):
        self.assert_route(
            'What is the return policy for premium customers?',
            [
                'initialize_session',
                'route_to_policy_agent',
                'route_to_communication_agent',
            ],
        )

    def test_account_question_routes_inventory_then_communication(self):
        self.assert_route(
            'What is my customer tier?',
            [
                'initialize_session',
                'route_to_inventory_agent',
                'route_to_communication_agent',
            ],
        )

    def test_calculation_routes_directly_to_communication(self):
        self.assert_route(
            'How much are 5 items at $29.99 with 10% off?',
            [
                'initialize_session',
                'route_to_communication_agent',
            ],
        )

    def assert_route(self, request, expected_names):
        orchestrator = FakeOrchestrator()
        message = f'[Session ID: session-1] [Customer ID: CUST-001] {request}'

        result = agent_orchestrator.run_orchestrated_request(orchestrator, message)

        actual_names = [name for name, _ in orchestrator.calls]
        self.assertEqual(actual_names, expected_names)
        self.assertEqual(
            result,
            'Final response from CommunicationAgent',
        )
        self.assertEqual(actual_names[-1], 'route_to_communication_agent')
        self.assertEqual(actual_names.count('route_to_communication_agent'), 1)


if __name__ == '__main__':
    unittest.main()
