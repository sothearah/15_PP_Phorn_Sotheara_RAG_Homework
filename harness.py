"""Safety harness for permissions, validation, and tool execution."""

from typing import Any, Callable

from pydantic import BaseModel

# These role names define the first application-level permission boundary.
STUDENT_ROLE = "student"
ADMIN_ROLE = "admin"
MAX_ITERATIONS = 3
MAX_TOOL_CALLS = 5


class PermissionError(Exception):
    """Raised when a role cannot use a requested tool."""


class ToolHarness:
    """Control future tool calls with permissions and execution limits."""

    def __init__(
        self,
        role: str = STUDENT_ROLE,
        max_iterations: int = MAX_ITERATIONS,
        max_tool_calls: int = MAX_TOOL_CALLS,
    ) -> None:
        """Configure the role and limits used by the harness."""
        self.role = role
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
        self.tool_calls = 0

    def can_use_tool(self, tool_name: str) -> bool:
        """Return whether the configured role may use a tool."""
        allowed_tools = {
            STUDENT_ROLE: {"search_course", "check_schedule"},
            ADMIN_ROLE: {"search_course", "check_schedule", "register_course"},
        }
        return tool_name in allowed_tools.get(self.role, set())

    def execute_tool(
        self,
        tool_name: str,
        tool: Callable[[BaseModel], dict[str, Any]],
        request: BaseModel,
    ) -> dict[str, Any]:
        """Validate permission and execute one controlled tool call."""
        if not self.can_use_tool(tool_name):
            raise PermissionError(f"Role '{self.role}' cannot use '{tool_name}'.")
        if self.tool_calls >= self.max_tool_calls:
            raise RuntimeError("Maximum tool-call limit reached.")
        self.tool_calls += 1
        return tool(request)
