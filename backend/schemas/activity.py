from datetime import datetime

from pydantic import BaseModel


class ActivityOut(BaseModel):
    id: int
    ticket_id: int
    user_id: int | None
    activity_type: str
    description: str
    timestamp: datetime

    model_config = {"from_attributes": True}