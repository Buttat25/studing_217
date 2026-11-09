# Вспомогательный модуль открытых тестов. Сгенерировано — не редактируйте.
# Ожидаемые ответы записаны в golden.json.gz.
"""Независимая модель отчёта задачи 5 для тестов (не тест, вспомогательный модуль).

Строит ожидаемый отчёт по байтам файла журнала по правилам из README задачи.
"""
import io
import re
from datetime import datetime, timedelta

from course_program import golden_lookup


report = golden_lookup(__file__, "eventlog_model.report")
