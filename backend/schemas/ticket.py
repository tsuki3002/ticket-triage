from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator

from schemas.ai_analysis import Category, Priority


class TicketStatus(str, Enum):
    OPEN = "Open"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    WAITING_FOR_CUSTOMER = "Waiting for Customer"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


# ---------- Create ----------
# Matches section 5.3 field-by-field:
# - customer_name: mandatory, max 100
# - customer_email: mandatory, valid email, max 150
# - subject: mandatory, min 10, max 200
# - description: mandatory, min 30, no stated max, stored unmodified by AI
# - product_module: optional free text / dropdown value
# - attachment_link: optional

class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    customer_email: EmailStr = Field(max_length=150)
    subject: str = Field(min_length=10, max_length=200)
    description: str = Field(min_length=30)
    product_module: str | None = Field(default=None, max_length=100)
    attachment_link: str | None = Field(default=None, max_length=500)

    @field_validator("customer_name", "subject", "description")
    @classmethod
    def not_just_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field cannot be empty/whitespace")
        return v.strip()


# ---------- Update (human review of AI suggestions / manual edits) ----------
# Per section 10: user can edit summary, category, priority, recommended_team,
# suggested_response. If the user changes a suggestion, the edited value becomes
# the active ticket value. All fields optional since this is a partial update.

class TicketUpdate(BaseModel):
    summary: str | None = Field(default=None, max_length=500)
    category: Category | None = None
    priority: Priority | None = None
    recommended_team: str | None = Field(default=None, max_length=100)
    suggested_response: str | None = Field(default=None, max_length=1000)
    product_module: str | None = Field(default=None, max_length=100)
    attachment_link: str | None = Field(default=None, max_length=500)


# ---------- Assignment ----------
# Section 11: assign to a team, a user, or both. IDs must reference existing,
# active records — enforced in the service layer, not here.

class AssignmentUpdate(BaseModel):
    team_id: int | None = None
    user_id: int | None = None


# ---------- Status ----------
# Section 12: one of the six defined statuses.

class StatusUpdate(BaseModel):
    status: TicketStatus


# ---------- Analyze response ----------
# Wraps the result of POST /tickets/{id}/analyze -- ticket is always present
# (it was saved before the AI call), error is only set on failure.

class AnalyzeResponse(BaseModel):
    status: str
    ticket: "TicketOut"
    error: str | None = None


# ---------- Output ----------
# Section 9: everything the ticket-details page needs to display.

class TicketOut(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    subject: str
    description: str
    product_module: str | None
    attachment_link: str | None

    # AI-derived / human-confirmed current values
    summary: str | None
    category: Category | None
    priority: Priority | None
    priority_reason: str | None
    recommended_team: str | None
    suggested_response: str | None

    # assignment + lifecycle
    assigned_team_id: int | None
    assigned_user_id: int | None
    status: TicketStatus

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Resolves the forward-referenced "TicketOut" used in AnalyzeResponse above,
# now that TicketOut is fully defined.
AnalyzeResponse.model_rebuild()