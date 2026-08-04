from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401 -- must be imported so Base knows about all tables
from routers import auth, tickets, comments, activities

# Creates tables that don't exist yet. Safe to call on every startup --
# it will not touch tables that already exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ticket Triage API")

# Allow the local Next.js dev server to call this API.
# Tighten this list before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(comments.router, tags=["comments"])
app.include_router(activities.router, tags=["activities"])


@app.get("/health")
def health_check():
    return {"status": "ok"}