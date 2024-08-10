from pydantic import BaseModel, condecimal, validator
from models import BetStatus


class EventOut(BaseModel):
    lp_id: int
    coefficient: float


class BetCreate(BaseModel):
    lp_id: int
    amount: condecimal(max_digits=10, decimal_places=2)

    @validator('amount')
    def check_amount(cls, value):
        if value <= 0:
            raise ValueError('Amount must be greater than 0')
        return value


class BetOut(BaseModel):
    id: int
    lp_id: int
    amount: float
    status: BetStatus
