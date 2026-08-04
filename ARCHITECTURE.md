# Architecture

## 1. High-Level Design (HLD)

Browser
|
v
Frontend (Next.js / React)
| REST + JWT
v
Backend API (FastAPI)
|
v v
SQLite database Groq AI provider
(tickets, users, (Llama 3.3 via API)
comments, etc.)
**Components:**

- **Browser** — the user's client, no logic beyond rendering and calling the frontend.
- **Frontend (Next.js)** — renders the dashboard, ticket creation form, ticket details page. Talks to the backend only over REST with a JWT in the `Authorization` header. Never talks to Groq directly — this keeps the AI API key server-side only.
- **Backend API (FastAPI)** — the single source of truth for business logic. All validation, ticket lifecycle rules, and AI orchestration happen here.
- **SQLite database** — persists all ticket-management data (see Data Model below).
- **Groq AI provider** — external LLM API called only by the backend, only during the "Save and Analyze" flow.

**Why this shape:** a thin frontend and a backend that owns all business rules means the frontend can be swapped (e.g. for a mobile client later) without touching ticket logic, and the AI provider can be swapped without touching the frontend at all.

---

## 2. Low-Level Design (LLD) — Backend internals

Routers (auth, tickets, comments, activities)
|
v
Ticket service (validation, lifecycle, retry/failure handling)
|
v v
SQLAlchemy models AI provider interface
| |
v v
SQLite tables GroqProvider -> Groq API
(users, teams, tickets,
comments, ai_suggestions,
activities)
**Layer responsibilities:**

- **Routers** — parse/validate the HTTP request shape (via Pydantic schemas), call the service layer, return responses. No business logic, no direct DB access, no AI calls.
- **Ticket service** — the only layer that makes decisions: is this a valid status transition, should this be logged as an activity, what happens if the AI call fails. This is where the try/except around the AI call lives, so a Groq failure never crashes the request — it degrades to "ticket saved, AI failed, user can retry."
- **AI provider interface (`AIProvider` abstract class)** — defines `analyze_ticket(subject, description, product_module) -> TicketAnalysis`. `GroqProvider` is the current implementation. Swapping to OpenAI/Claude/local model later means writing one new class — nothing in the service layer or routers changes.
- **SQLAlchemy models / repository functions** — the only layer that talks to SQLite. Keeps queries out of the service layer's business logic.

**Note:** `comments` and `activities` routers use direct DB access rather than a dedicated service layer, since they are simple CRUD with no business logic — unlike tickets, which has AI orchestration and lifecycle rules that justify a service layer.

---

## 3. Data model

| Table            | Purpose                                                                                                                                            | Key relationships                                                                    |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `users`          | Login + assignment targets                                                                                                                         | referenced by `tickets.assigned_user_id`, `comments.author_id`, `activities.user_id` |
| `teams`          | Assignment targets                                                                                                                                 | referenced by `tickets.assigned_team_id`                                             |
| `tickets`        | Core ticket record — customer info, **immutable original description**, current confirmed category/priority/status                                 | central table, referenced by comments, activities, ai_suggestions                    |
| `ai_suggestions` | Immutable snapshot of what the AI actually returned (summary, category, priority, priority_reason, recommended_team, suggested_response, raw JSON) | `ticket_id` FK                                                                       |
| `comments`       | Internal notes, not customer-facing                                                                                                                | `ticket_id`, `author_id` FK                                                          |
| `activities`     | Audit log: created, AI analysis completed/failed/retried, category changed, status changed, etc.                                                   | `ticket_id`, `user_id` FK                                                            |

**Key design decision — AI suggestions vs. confirmed values:**
`tickets` stores the _live, currently-confirmed_ values (category, priority, recommended_team, etc.). `ai_suggestions` stores what the AI originally returned, untouched, forever. When a user edits an AI suggestion, only the `tickets` row changes — the `ai_suggestions` row stays as the historical record, and an `activities` row logs the edit. This means:

- The original customer description is never touched by AI (stored once in `tickets.description`, never overwritten).
- You can always answer "what did the AI actually say vs. what did the human decide" — required by the assignment spec.
- Categories and priorities are stored as plain strings in the database, not native enum types (SQLite has no enum type) — validation is enforced at the API boundary via Pydantic enums (`Category`, `Priority`), not at the database layer.

---

## 4. Failure handling strategy

| Failure                                       | Behavior                                                                                                                                                                                                                                                             |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Missing/invalid required fields               | Ticket not created; field-level 422 errors; AI never called                                                                                                                                                                                                          |
| Groq API error/timeout                        | Ticket already saved (it's saved _before_ the AI call); on malformed JSON/schema-validation failure, the system retries the AI call once automatically; if both attempts fail, `activities` logs `ai_analysis_failed` and the user sees a clear error + retry button |
| Malformed AI JSON / fails Pydantic validation | Same retry-once strategy as above. Not repaired via string manipulation — guessing where to insert missing quotes around AI-generated free text risks silently corrupting the actual content, so a clean retry is safer than a repair attempt                        |
| DB write failure                              | Generic user-facing error, no stack trace exposed; no partial ticket records                                                                                                                                                                                         |
| Unauthenticated request to protected route    | 401, no ticket data returned                                                                                                                                                                                                                                         |

The core invariant: **the ticket record is always created before the AI is ever called**, and nothing about AI success/failure can roll back or block the ticket's existence.

---

## 5. Trade-offs

- Single user role for all authenticated users — the schema supports adding roles later (`users.role` column already exists) but role-based permissions aren't enforced in this 48-hour build.
- Retry-once (rather than repair or infinite retry) on malformed AI output — chosen because smaller/faster hosted models occasionally return invalid JSON on a single call but rarely twice in a row, and because repairing broken JSON via regex/string editing risks corrupting the AI's actual wording.
- No strict status-transition state machine — transitions are suggested behavior, not enforced, per the assignment's stated optionality; documented here instead of hardcoded.
- SQLite instead of Postgres — zero setup cost, acceptable per the assignment spec; would move to Postgres for any real concurrent-user load.
- Frontend team-assignment dropdown is hardcoded to match `seed.py`'s team list, since a dedicated `GET /teams` endpoint wasn't built in the time available.
