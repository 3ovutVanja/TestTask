from tortoise import fields, models
from enum import Enum
from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


class EventStatus(Enum):
    unfinished = "незавершённое"
    win_team_one = "завершено выигрышем первой команды"
    win_team_two = "завершено выигрышем второй команды"


class Event(models.Model):

    id = fields.IntField(pk=True)
    coefficient = fields.DecimalField(max_digits=5, decimal_places=2)
    deadline = fields.DatetimeField()
    status = fields.CharEnumField(EventStatus, max_length=50)

    class Meta:
        table = "event"

