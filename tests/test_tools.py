"""Starter tests for Student Assistant tools."""

import json
from pathlib import Path
import shutil

import pytest
import tools

from schemas import CheckScheduleInput, RegisterCourseInput, SearchCourseInput
from tools import check_schedule, register_course, search_course


@pytest.fixture(autouse=True)
def isolated_tool_data(tmp_path, monkeypatch):
    """Use fresh registrations for every test without changing live records."""
    data_path = tmp_path / "data"
    data_path.mkdir()
    source_data = Path(tools.__file__).resolve().parent / "data"
    shutil.copyfile(source_data / "courses.json", data_path / "courses.json")
    students = [
        {"student_id": "S1001", "name": "Test Student One", "registered_courses": ["CS101", "AI201"]},
        {"student_id": "S1002", "name": "Test Student Two", "registered_courses": ["DB210"]},
    ]
    (data_path / "students.json").write_text(json.dumps(students), encoding="utf-8")
    monkeypatch.setattr(tools, "__file__", str(tmp_path / "tools.py"))


@pytest.mark.parametrize(
    "query, expected_ids",
    [
        ("Introduction to Programming", ["CS101"]),
        ("pRoGrAmMiNg", ["CS101"]),
        ("  artificial  ", ["AI201"]),
        ("ai", ["AI201"]),
        ("Development", ["WEB220"]),
        ("Learn", ["ML301"]),
        ("Systems", ["DB210"]),
        ("tion", ["CS101", "AI201"]),
    ],
)
def test_search_course_matches(query, expected_ids) -> None:
    result = search_course(SearchCourseInput(query=query))
    assert result["status"] == "success"
    assert [course["course_id"] for course in result["courses"]] == expected_ids
    assert all("available_seats" in course for course in result["courses"])


@pytest.mark.parametrize("query", ["nonexistent course", "   "])
def test_search_course_no_matches(query) -> None:
    assert search_course(SearchCourseInput(query=query)) == {
        "status": "not_found", "courses": []
    }


def test_search_course_from_another_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = search_course(SearchCourseInput(query="Database"))
    assert result["status"] == "success"
    assert result["courses"][0]["course_id"] == "DB210"


@pytest.mark.parametrize(
    "student_id, expected_schedule",
    [
        ("S1001", [("CS101", "Monday", "09:00", "10:30"),
                   ("AI201", "Tuesday", "11:00", "12:30")]),
        ("S1002", [("DB210", "Wednesday", "13:00", "14:30")]),
    ],
)
def test_check_schedule_registered_courses(student_id, expected_schedule) -> None:
    result = check_schedule(CheckScheduleInput(student_id=student_id))
    assert result["status"] == "success"
    assert result["student_id"] == student_id
    assert [
        (course["course_id"], course["day"], course["start_time"], course["end_time"])
        for course in result["schedule"]
    ] == expected_schedule


def test_check_schedule_unknown_student() -> None:
    assert check_schedule(CheckScheduleInput(student_id="UNKNOWN")) == {
        "status": "not_found", "student_id": "UNKNOWN", "schedule": []
    }


def test_check_schedule_from_another_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = check_schedule(CheckScheduleInput(student_id="S1001"))
    assert result["status"] == "success"
    assert [course["course_id"] for course in result["schedule"]] == ["CS101", "AI201"]

def test_register_course_already_registered() -> None:
    """Reject duplicate registration."""
    result = register_course(
        RegisterCourseInput(student_id="S1001", course_id="CS101")
    )
    assert result["status"] == "already_registered"
