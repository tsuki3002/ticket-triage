from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas.comment import CommentCreate, CommentOut
from auth.dependencies import get_current_user

router = APIRouter()


@router.get("/tickets/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(
    ticket_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    return (
        db.query(models.Comment)
        .filter(models.Comment.ticket_id == ticket_id)
        .order_by(models.Comment.created_at.asc())
        .all()
    )


@router.post("/tickets/{ticket_id}/comments", response_model=CommentOut)
def create_comment(
    ticket_id: int,
    payload: CommentCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    comment = models.Comment(ticket_id=ticket_id, author_id=user.id, text=payload.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    activity = models.Activity(
        ticket_id=ticket_id,
        user_id=user.id,
        activity_type="comment_added",
        description="Internal comment added",
    )
    db.add(activity)
    db.commit()

    return comment