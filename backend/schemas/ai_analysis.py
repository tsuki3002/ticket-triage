from pydantic import BaseModel, Field, field_validator
from enum import Enum


class Category(str, Enum):
    AUTHENTICATION = "Authentication"
    BILLING = "Billing"
    PERFORMANCE = "Performance"
    DATA_ISSUE = "Data Issue"
    INTEGRATION = "Integration"
    UI = "User Interface"
    ACCESS_REQUEST = "Access Request"
    FEATURE_REQUEST = "Feature Request"
    SECURITY = "Security"
    GENERAL_SUPPORT = "General Support"
    UNKNOWN = "Unknown"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketAnalysis(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    category: Category
    priority: Priority
    priority_reason: str = Field(min_length=1, max_length=300)
    recommended_team: str = Field(min_length=1, max_length=100)
    suggested_response: str = Field(min_length=1, max_length=1000)

    @field_validator("summary", "priority_reason", "suggested_response")
    @classmethod
    def not_just_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field cannot be empty/whitespace")
        return v.strip()