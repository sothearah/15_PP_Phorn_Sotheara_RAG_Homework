"""Pydantic input schemas for Student Assistant tools."""

from pydantic import BaseModel, Field


class SearchCourseInput(BaseModel):
    """Validated input for searching courses."""

    query: str = Field(..., min_length=1, description="Course ID or course name search text")


class CheckScheduleInput(BaseModel):
    """Validated input for checking a student's schedule."""

    student_id: str = Field(..., min_length=1, description="Student identifier")


class RegisterCourseInput(BaseModel):
    """Validated input for registering a student in a course."""

    student_id: str = Field(..., min_length=1, description="Student identifier")
    course_id: str = Field(..., min_length=1, description="Course identifier")
