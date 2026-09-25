"""Starter tests for application-level permission checking."""

import pytest

from harness import ADMIN_ROLE, STUDENT_ROLE, PermissionError, ToolHarness
from schemas import RegisterCourseInput
from tools import register_course


def test_student_can_check_read_only_tools() -> None:
    """Students may use non-mutating tools."""
    harness = ToolHarness(role=STUDENT_ROLE)
    assert harness.can_use_tool("search_course")
    assert harness.can_use_tool("check_schedule")


def test_student_cannot_register_course() -> None:
    """Registration is restricted in the starter permission model."""
    harness = ToolHarness(role=STUDENT_ROLE)
    request = RegisterCourseInput(student_id="S1001", course_id="CS101")

    with pytest.raises(PermissionError):
        harness.execute_tool("register_course", register_course, request)


def test_admin_can_register_course() -> None:
    """Admins are allowed to call the future registration tool."""
    harness = ToolHarness(role=ADMIN_ROLE)
    assert harness.can_use_tool("register_course")
