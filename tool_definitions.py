"""LLM tool descriptions in OpenAI Responses API format.

Parameter types, descriptions, and required fields come from schemas.py.
These definitions describe tools; execution still belongs to tools.py and
must go through the permission harness when LLM calling is added.
"""

from typing import Any

from pydantic import BaseModel

from schemas import CheckScheduleInput, RegisterCourseInput, SearchCourseInput


def _parameters(model: type[BaseModel]) -> dict[str, Any]:
    """Generate parameters for our flat models, whose fields are all required."""
    parameters = model.model_json_schema()
    # Strict function calling rejects arguments outside the declared fields.
    parameters["additionalProperties"] = False
    return parameters


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_course",
        "description": (
            "Find courses by a course ID or a keyword in the course name, "
            "ignoring letter case. Returns matching course details, including "
            "schedules and available seats."
        ),
        "parameters": _parameters(SearchCourseInput),
        "strict": True,
    },
    {
        "type": "function",
        "name": "check_schedule",
        "description": (
            "Look up a student's registered courses and their schedules using "
            "the student ID. Use this to view the student's current timetable."
        ),
        "parameters": _parameters(CheckScheduleInput),
        "strict": True,
    },
    {
        "type": "function",
        "name": "register_course",
        "description": (
            "Register a student in a course using the student ID and course ID. "
            "Requires admin permission. Checks that both records exist, rejects "
            "duplicate registration and courses with no available seats, then "
            "updates the student's registrations and reduces available seats."
        ),
        "parameters": _parameters(RegisterCourseInput),
        "strict": True,
    },
]
