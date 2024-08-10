from tortoise import fields, models
from enum import Enum
from datetime import datetime, timedelta
import logging
from enum import Enum


logger = logging.getLogger(__name__)


class BetStatus(str, Enum):
    pending = "еще не сыграла"
    won = "выиграла"
    lost = "проиграла"


class ActualEvents(models.Model):
    id = fields.IntField(pk=True)
    lp_id = fields.IntField()
    coefficient = fields.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        table = "actual_events"


class Bet(models.Model):
    id = fields.IntField(pk=True)
    lp_id = fields.IntField()
    amount = fields.DecimalField(max_digits=10, decimal_places=2)
    status = fields.CharEnumField(BetStatus, max_length=20, default=BetStatus.pending)

    class Meta:
        table = "bets"
