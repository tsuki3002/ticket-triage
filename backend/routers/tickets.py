from fastapi import APIRouter, Depends, HTTPException

import models
from schemas.ticket import (
    TicketCreate,
    TicketOut,
    TicketUpdate,
    AssignmentUpdate,
    StatusUpdate,
    AnalyzeResponse,
)
from services.ticket_service import TicketService
from auth.dependencies import get_current_user, get_ticket_service

router = APIRouter()


@router.post("", response_model=TicketOut)
def create_ticket(
    payload: TicketCreate,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    """
    Corresponds to the 'Save Ticket' action -- validates and saves the
    ticket without calling the AI. Status is always Open on creation.
    """
    return svc.create_ticket(payload, created_by=user)


@router.post("/{ticket_id}/analyze", response_model=AnalyzeResponse)
async def analyze_ticket(
    ticket_id: int,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    """
    Corresponds to the 'Save and Analyze' action's AI step. The ticket must
    already exist (create it first via POST /tickets). If the AI call fails,
    the ticket remains saved and usable -- this returns a 200 with
    status: "failed" rather than raising, so the frontend can show an inline
    retry rather than a hard error page.
    """
    result = await svc.analyze_ticket(ticket_id)
    return result


@router.get("", response_model=list[TicketOut])
def list_tickets(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    assigned_team_id: int | None = None,
    assigned_user_id: int | None = None,
    q: str | None = None,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    return svc.list_tickets(
        status_filter=status,
        category=category,
        priority=priority,
        assigned_team_id=assigned_team_id,
        assigned_user_id=assigned_user_id,
        q=q,
    )


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    return svc.get_ticket(ticket_id)


@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    """Human review of AI suggestions -- edited values become the active ticket values."""
    return svc.update_ticket(ticket_id, payload, edited_by=user)


@router.put("/{ticket_id}/assignment", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    payload: AssignmentUpdate,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    return svc.assign_ticket(ticket_id, payload, assigned_by=user)


@router.put("/{ticket_id}/status", response_model=TicketOut)
def update_status(
    ticket_id: int,
    payload: StatusUpdate,
    user: models.User = Depends(get_current_user),
    svc: TicketService = Depends(get_ticket_service),
):
    return svc.update_status(ticket_id, payload, updated_by=user)