"""Tool functions for course search, schedules, and registration."""

import json
from pathlib import Path
from typing import Any

from schemas import CheckScheduleInput, RegisterCourseInput, SearchCourseInput


def search_course(request: SearchCourseInput) -> dict[str, Any]:
    """Find courses by a case-insensitive name keyword or course ID."""
    query = request.query.strip().lower()
    if not query:
        return {"status": "not_found", "courses": []}

    # Use this file's location so any terminal working directory works.
    courses_path = Path(__file__).resolve().parent / "data" / "courses.json"
    with courses_path.open(encoding="utf-8") as file:
        courses = json.load(file)

    matches = []
    for course in courses:
        if query in course["course_name"].lower() or query in course["course_id"].lower():
            matches.append(course)

    return {"status": "success" if matches else "not_found", "courses": matches}


def check_schedule(request: CheckScheduleInput) -> dict[str, Any]:
    """Check a student's registered-course schedule."""
    data_path = Path(__file__).resolve().parent / "data"
    with (data_path / "students.json").open(encoding="utf-8-sig") as file:
        students = json.load(file)

    student = next(
        (student for student in students if student["student_id"] == request.student_id),
        None,
    )
    if student is None:
        return {"status": "not_found", "student_id": request.student_id, "schedule": []}

    with (data_path / "courses.json").open(encoding="utf-8-sig") as file:
        courses_by_id = {course["course_id"]: course for course in json.load(file)}

    schedule = [
        courses_by_id[course_id]
        for course_id in student["registered_courses"]
        if course_id in courses_by_id
    ]
    return {"status": "success", "student_id": request.student_id, "schedule": schedule}


def register_course(request: RegisterCourseInput) -> dict[str, Any]:
    """Register a student for a course after harness checks."""
    data_path = Path(__file__).resolve().parent / "data"
    students_path = data_path / "students.json"
    courses_path = data_path / "courses.json"
    with students_path.open(encoding="utf-8-sig") as file:
        students = json.load(file)
    with courses_path.open(encoding="utf-8-sig") as file:
        courses = json.load(file)

    student = next(
        (item for item in students if item["student_id"] == request.student_id), None
    )
    course = next(
        (item for item in courses if item["course_id"] == request.course_id), None
    )
    result = {"student_id": request.student_id, "course_id": request.course_id}
    if student is None or course is None:
        return {"status": "not_found", **result}
    if request.course_id in student["registered_courses"]:
        return {"status": "already_registered", **result}
    if course["available_seats"] <= 0:
        return {"status": "no_seats", **result}

    student["registered_courses"].append(request.course_id)
    course["available_seats"] -= 1
    with students_path.open("w", encoding="utf-8") as file:
        json.dump(students, file, ensure_ascii=False, indent=2)
        file.write("\n")
    with courses_path.open("w", encoding="utf-8") as file:
        json.dump(courses, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return {"status": "success", **result}

