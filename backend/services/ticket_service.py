import json

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

import models
from ai.base import AIProvider
from schemas.ticket import TicketCreate, TicketUpdate, AssignmentUpdate, StatusUpdate


class TicketService:
    def __init__(self, db: Session, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider

    # ---------- internal helpers ----------

    def _get_ticket_or_404(self, ticket_id: int) -> models.Ticket:
        ticket = self.db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        return ticket

    def _log_activity(self, ticket_id: int, activity_type: str, description: str, user_id: int | None = None):
        activity = models.Activity(
            ticket_id=ticket_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description,
        )
        self.db.add(activity)
        self.db.commit()

    # ---------- create ----------

    def create_ticket(self, payload: TicketCreate, created_by: models.User) -> models.Ticket:
        ticket = models.Ticket(
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            subject=payload.subject,
            description=payload.description,
            product_module=payload.product_module,
            attachment_link=payload.attachment_link,
            status="Open",
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        self._log_activity(ticket.id, "ticket_created", "Ticket created", user_id=created_by.id)
        return ticket

    # ---------- AI analysis ----------

    async def analyze_ticket(self, ticket_id: int) -> dict:
        """
        Failure-handling strategy (documented per assignment section 19.3):
        on a malformed/invalid AI response, retry the call once. Smaller,
        faster hosted models occasionally return invalid JSON (missing
        quotes, stray text) on a single call, but rarely twice in a row.
        We do not attempt to repair broken JSON with regex/string surgery --
        guessing where to insert quotes around free-text content risks
        silently corrupting the AI's actual wording. If both attempts fail,
        the ticket remains saved and usable, and the user can retry manually.
        """
        ticket = self._get_ticket_or_404(ticket_id)

        last_error: Exception | None = None
        for attempt in range(1, 3):  # try twice total
            try:
                analysis = await self.ai_provider.analyze_ticket(
                    subject=ticket.subject,
                    description=ticket.description,
                    product_module=ticket.product_module,
                )
                break
            except (json.JSONDecodeError, ValidationError, Exception) as e:
                last_error = e
                if attempt == 1:
                    self._log_activity(
                        ticket_id,
                        "ai_analysis_retry",
                        f"AI response invalid on attempt 1, retrying: {e}",
                    )
        else:
            self._log_activity(ticket_id, "ai_analysis_failed", f"AI analysis failed after retry: {last_error}")
            return {"status": "failed", "ticket": ticket, "error": str(last_error)}

        # Save the immutable AI suggestion record
        suggestion = models.AISuggestion(
            ticket_id=ticket.id,
            summary=analysis.summary,
            category=analysis.category.value,
            priority=analysis.priority.value,
            priority_reason=analysis.priority_reason,
            recommended_team=analysis.recommended_team,
            suggested_response=analysis.suggested_response,
            raw_response=analysis.model_dump_json(),
        )
        self.db.add(suggestion)

        # Apply as the ticket's current (still-editable) values
        ticket.summary = analysis.summary
        ticket.category = analysis.category.value
        ticket.priority = analysis.priority.value
        ticket.priority_reason = analysis.priority_reason
        ticket.recommended_team = analysis.recommended_team
        ticket.suggested_response = analysis.suggested_response

        self.db.commit()
        self.db.refresh(ticket)

        self._log_activity(ticket_id, "ai_analysis_completed", "AI suggestions generated")
        return {"status": "success", "ticket": ticket}

    # ---------- read ----------

    def get_ticket(self, ticket_id: int) -> models.Ticket:
        return self._get_ticket_or_404(ticket_id)

    def list_tickets(
        self,
        status_filter: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        assigned_team_id: int | None = None,
        assigned_user_id: int | None = None,
        q: str | None = None,
    ) -> list[models.Ticket]:
        query = self.db.query(models.Ticket)

        if status_filter:
            query = query.filter(models.Ticket.status == status_filter)
        if category:
            query = query.filter(models.Ticket.category == category)
        if priority:
            query = query.filter(models.Ticket.priority == priority)
        if assigned_team_id:
            query = query.filter(models.Ticket.assigned_team_id == assigned_team_id)
        if assigned_user_id:
            query = query.filter(models.Ticket.assigned_user_id == assigned_user_id)
        if q:
            like = f"%{q}%"
            query = query.filter(
                (models.Ticket.subject.ilike(like))
                | (models.Ticket.customer_name.ilike(like))
                | (models.Ticket.customer_email.ilike(like))
                | (models.Ticket.description.ilike(like))
            )

        return query.order_by(models.Ticket.created_at.desc()).all()

    # ---------- update (human review of AI suggestions) ----------

    def update_ticket(self, ticket_id: int, payload: TicketUpdate, edited_by: models.User) -> models.Ticket:
        ticket = self._get_ticket_or_404(ticket_id)
        changes = payload.model_dump(exclude_unset=True)

        for field, new_value in changes.items():
            old_value = getattr(ticket, field)
            # enum fields arrive as enum instances from Pydantic; store as string
            if hasattr(new_value, "value"):
                new_value = new_value.value
            if old_value != new_value:
                setattr(ticket, field, new_value)
                self._log_activity(
                    ticket_id,
                    f"{field}_changed",
                    f"{field} changed from '{old_value}' to '{new_value}'",
                    user_id=edited_by.id,
                )

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    # ---------- assignment ----------

    def assign_ticket(self, ticket_id: int, payload: AssignmentUpdate, assigned_by: models.User) -> models.Ticket:
        ticket = self._get_ticket_or_404(ticket_id)

        if payload.team_id is not None:
            team = self.db.query(models.Team).filter(models.Team.id == payload.team_id).first()
            if team is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team does not exist")
            ticket.assigned_team_id = team.id

        if payload.user_id is not None:
            user = self.db.query(models.User).filter(models.User.id == payload.user_id).first()
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned user does not exist or is inactive",
                )
            ticket.assigned_user_id = user.id

        if (payload.team_id or payload.user_id) and ticket.status == "Open":
            ticket.status = "Assigned"

        self.db.commit()
        self.db.refresh(ticket)

        self._log_activity(
            ticket_id,
            "team_assigned" if payload.team_id else "user_assigned",
            "Ticket assignment updated",
            user_id=assigned_by.id,
        )
        return ticket

    # ---------- status ----------

    def update_status(self, ticket_id: int, payload: StatusUpdate, updated_by: models.User) -> models.Ticket:
        ticket = self._get_ticket_or_404(ticket_id)
        old_status = ticket.status
        new_status = payload.status.value

        if old_status == new_status:
            # No-op: nothing changed, don't clutter the activity timeline.
            return ticket

        ticket.status = new_status
        self.db.commit()
        self.db.refresh(ticket)

        self._log_activity(
            ticket_id,
            "status_changed",
            f"Status changed from '{old_status}' to '{ticket.status}'",
            user_id=updated_by.id,
        )
        return ticket