from tools import search_course
from schemas import SearchCourseInput

result = search_course(SearchCourseInput(query="databse"))
print(result)