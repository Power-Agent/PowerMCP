"""The shared tool result shape.

Every bundled server reports through :mod:`powermcp.errors`, so a caller reads
``status`` once and gets the same answer from all of them.
"""

from __future__ import annotations

import logging

import pytest

from powermcp.errors import run_tool, tool_error, tool_success
from powermcp.sandbox import PathNotAllowed


@pytest.fixture()
def logger() -> logging.Logger:
    return logging.getLogger("powermcp.tests.errors")


def test_tool_success_names_the_status():
    assert tool_success() == {"status": "success"}


def test_tool_success_carries_result_keys():
    result = tool_success(file_path="/tmp/out.png", rows=3)
    assert result == {"status": "success", "file_path": "/tmp/out.png", "rows": 3}


def test_tool_error_names_the_status_and_the_message():
    assert tool_error("no such case") == {"status": "error", "message": "no such case"}


def test_tool_error_carries_the_keys_a_caller_reads_on_both_branches():
    result = tool_error("unknown plot_type", file_path=None)
    assert result == {"status": "error", "message": "unknown plot_type", "file_path": None}


def test_run_tool_passes_a_successful_body_through(logger):
    assert run_tool(lambda: tool_success(value=7), logger=logger) == {
        "status": "success",
        "value": 7,
    }


@pytest.mark.parametrize("exception", [ValueError, PathNotAllowed])
def test_an_argument_failure_keeps_its_own_message(logger, exception):
    """The text of these two is written for the caller, so it passes through."""

    def body() -> dict:
        raise exception("`csv_path` is outside the allowed roots")

    assert run_tool(body, logger=logger) == {
        "status": "error",
        "message": "`csv_path` is outside the allowed roots",
    }


def test_any_other_failure_is_named_by_type(logger):
    def body() -> dict:
        raise KeyError("Resource")

    result = run_tool(body, logger=logger)
    assert result["status"] == "error"
    assert result["message"] == "KeyError: 'Resource'"


def test_an_unexpected_failure_is_logged_with_its_traceback(logger, caplog):
    def body() -> dict:
        raise RuntimeError("sbatch is gone")

    with caplog.at_level(logging.ERROR, logger=logger.name):
        run_tool(body, logger=logger)

    record = caplog.records[-1]
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError


def test_an_argument_failure_is_not_logged_as_an_incident(logger, caplog):
    """A rejected argument is an answer to the caller, not a server fault."""

    def body() -> dict:
        raise ValueError("period must be positive")

    with caplog.at_level(logging.ERROR, logger=logger.name):
        run_tool(body, logger=logger)

    assert caplog.records == []


def test_a_keyboard_interrupt_is_not_turned_into_a_result(logger):
    """Only failures of the tool become results; a shutdown signal propagates."""

    def body() -> dict:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_tool(body, logger=logger)
