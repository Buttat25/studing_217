import io
import re
from datetime import datetime, timedelta

from course_program import golden_lookup


report = golden_lookup(__file__, "eventlog_model.report")
