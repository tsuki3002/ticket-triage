"""
Seeds the database with a demo login user and a small set of teams,
so login and ticket assignment have something real to work with.

Run this once, after models.py has created the tables:
    python seed.py
"""
import bcrypt

from database import Base, SessionLocal, engine
import models

Base.metadata.create_all(bind=engine)

DEMO_EMAIL = "demo@4sightai.com"
DEMO_PASSWORD = "demo1234"  # plaintext only exists here, for the README to document

TEAMS = [
    "Platform Engineering",
    "Application Engineering",
    "Security",
    "DevOps",
    "Database Team",
    "Billing Team",
    "Customer Support",
    "Product Team",
]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed():
    db = SessionLocal()
    try:
        # Seed demo user if it doesn't already exist
        existing_user = db.query(models.User).filter_by(email=DEMO_EMAIL).first()
        if not existing_user:
            demo_user = models.User(
                name="Demo Agent",
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                role="agent",
                is_active=True,
            )
            db.add(demo_user)
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print("Demo user already exists, skipping.")

        # Seed teams if they don't already exist
        existing_team_names = {t.name for t in db.query(models.Team).all()}
        new_teams = [models.Team(name=name) for name in TEAMS if name not in existing_team_names]
        if new_teams:
            db.add_all(new_teams)
            print(f"Created {len(new_teams)} teams.")
        else:
            print("Teams already exist, skipping.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()