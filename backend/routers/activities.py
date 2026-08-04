from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas.activity import ActivityOut
from auth.dependencies import get_current_user

router = APIRouter()


@router.get("/tickets/{ticket_id}/activities", response_model=list[ActivityOut])
def list_activities(
    ticket_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    return (
        db.query(models.Activity)
        .filter(models.Activity.ticket_id == ticket_id)
        .order_by(models.Activity.timestamp.asc())
        .all()
    )