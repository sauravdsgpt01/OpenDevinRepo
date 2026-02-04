"""Unit tests for the repository agent_finish.sh hook."""

from unittest.mock import MagicMock, patch

from openhands.controller.agent_controller import AgentController
from openhands.events.action import CmdRunAction
from openhands.events.event import EventSource


def test_enqueue_agent_finish_hook_adds_cmd_run_action():
    controller = MagicMock(spec=AgentController)
    controller.is_delegate = False
    controller.event_stream = MagicMock()

    with patch.object(
        AgentController,
        '_enqueue_agent_finish_hook',
        AgentController._enqueue_agent_finish_hook,
    ):
        AgentController._enqueue_agent_finish_hook(controller)

    controller.event_stream.add_event.assert_called_once()
    action, source = controller.event_stream.add_event.call_args.args

    assert isinstance(action, CmdRunAction)
    assert source == EventSource.ENVIRONMENT
    assert '.openhands/agent_finish.sh' in action.command
    assert action.hidden is True
    assert action.blocking is True
    assert action.timeout == 600


def test_enqueue_agent_finish_hook_skips_for_delegate_controller():
    controller = MagicMock(spec=AgentController)
    controller.is_delegate = True
    controller.event_stream = MagicMock()

    with patch.object(
        AgentController,
        '_enqueue_agent_finish_hook',
        AgentController._enqueue_agent_finish_hook,
    ):
        AgentController._enqueue_agent_finish_hook(controller)

    controller.event_stream.add_event.assert_not_called()
