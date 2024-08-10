from pydantic import BaseModel, validator, condecimal
from models import EventStatus
from datetime import datetime
import re
from typing import Annotated


class EventIn(BaseModel):
    coefficient: condecimal(max_digits=5, decimal_places=2)
    deadline: datetime
    status: EventStatus

    @validator('coefficient')
    def check_amount(cls, value):
        if value <= 0:
            raise ValueError('Amount must be greater than 0')
        return value


class EventOut(BaseModel):
    id: int
    coefficient: float
    deadline: datetime
    status: EventStatus


class EventBasicOut(BaseModel):
    id: int
    coefficient: float


class StatusUpdate(BaseModel):
    status: EventStatus
