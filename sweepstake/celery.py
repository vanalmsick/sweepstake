# -*- coding: utf-8 -*-

import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sweepstake.settings")

app = Celery("sweepstake")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "daily_matchday_email": {
        "task": "competition.tasks.daily_emails",
        "schedule": crontab(minute="45", hour="12", day_of_week="1-5"),
        "args": (),
    },
    "daily_matchday_api_scores": {
        "task": "competition.tasks.daily_api_scores",
        "schedule": crontab(minute="00", hour="14"),
        "args": (),
    },
}
app.conf.broker_transport_options = {
    "visibility_timeout": 60 * 60 * 24
}  # 24 hours to fix double execution of tasks with ETA


def is_task_already_executing(task_name: str) -> bool:
    """Returns whether the task with given task_name is already being executed.

    Args:
        task_name: Name of the task to check if it is running currently.
    Returns: A boolean indicating whether the task with the given task name is
        running currently.
    """
    active_tasks = app.control.inspect().active()
    task_count = 0
    for worker, running_tasks in active_tasks.items():
        for task in running_tasks:
            if task["name"] == task_name:
                task_count += 1

    return task_count > 1
