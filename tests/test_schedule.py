from tools import check_schedule
from schemas import CheckScheduleInput

result = check_schedule(CheckScheduleInput(student_id="S1001"))
print(result)