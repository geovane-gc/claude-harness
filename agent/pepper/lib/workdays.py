from datetime import datetime, timedelta

from .settings import CONFIG


def is_workday(moment=None):
    moment = moment or datetime.now()
    return moment.weekday() in CONFIG.get("workdays", [0, 1, 2, 3, 4])


def previous_workday(day):
    day -= timedelta(days=1)
    while not is_workday(datetime.combine(day, datetime.min.time())):
        day -= timedelta(days=1)
    return day


def days_since_previous_workday(today=None):
    today = today or datetime.now().date()
    start = previous_workday(today)
    return [(start + timedelta(days=n)) for n in range((today - start).days)]
