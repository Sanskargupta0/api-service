"""PioAgent customer API service.

This FastAPI application is the source of truth for the PioAgent API.
Its generated OpenAPI specification is filtered down to customer-facing
endpoints and synchronized into the documentation repository by GitHub
Actions (see .github/workflows/sync-docs.yml).
"""

from fastapi import FastAPI, HTTPException, Query

from .schemas import Task, User

app = FastAPI(
    title="PioAgent Service",
    version="1.0.0",
    description=(
        "Internal PioAgent service. This OpenAPI document contains **all** "
        "endpoints, including internal ones. Only endpoints under "
        "`/api/v1` are published to the customer documentation portal; "
        "the `/internal/*` endpoints are filtered out by "
        "`scripts/export_openapi.py`."
    ),
    openapi_tags=[
        {
            "name": "Users",
            "description": "Manage and look up user accounts in your workspace.",
        },
        {
            "name": "Tasks",
            "description": "Read tasks created and executed by your agents.",
        },
        {"name": "Internal", "description": "Internal endpoints (never published)."},
    ],
)

# --- Fake data ---------------------------------------------------------------

USERS: list[User] = [
    User(id="usr_001", email="ada@example.com", name="Ada Lovelace", is_active=True),
    User(id="usr_002", email="grace@example.com", name="Grace Hopper", is_active=False),
    User(id="usr_003", email="alan@example.com", name="Alan Turing", is_active=True),
]

TASKS: list[Task] = [
    Task(
        id="task_001",
        title="Summarize weekly report",
        status="completed",
        assignee_id="usr_001",
    ),
    Task(
        id="task_002",
        title="Draft release notes",
        status="in_progress",
        assignee_id="usr_002",
    ),
    Task(
        id="task_003",
        title="Review open pull requests",
        status="pending",
        assignee_id=None,
    ),
]


# --- Customer-facing API (/api/v1) --------------------------------------------


@app.get(
    "/api/v1/users",
    tags=["Users"],
    operation_id="listUsers",
    summary="Get all users",
    description=(
        "Get all users. Returns every user account in the calling workspace, "
        "including inactive users. Requires a valid API key."
    ),
    response_model=list[User],
    responses={401: {"description": "Missing or invalid API key."}},
)
def list_users() -> list[User]:
    """List all users in the workspace."""
    return USERS


@app.get(
    "/api/v1/users/{user_id}",
    tags=["Users"],
    operation_id="getUser",
    summary="Get a user by ID",
    description=(
        "Retrieve a single user account by its stable identifier. Returns 404 "
        "if no user with the given ID exists in the workspace."
    ),
    response_model=User,
    responses={
        404: {"description": "No user with this ID exists."},
    },
)
def get_user(user_id: str) -> User:
    """Retrieve a single user by ID."""
    for user in USERS:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


@app.get(
    "/api/v1/tasks",
    tags=["Tasks"],
    operation_id="listTasks",
    summary="Get all tasks",
    description=(
        "Get all tasks. Returns every task created by your agents, newest "
        "first. Use the `status` query parameter to filter by task status."
    ),
    response_model=list[Task],
    responses={401: {"description": "Missing or invalid API key."}},
)
def list_tasks(
    status: str | None = Query(
        default=None,
        description=(
            "Only return tasks with this status. One of `pending`, "
            "`in_progress`, or `completed`. Omit to return all tasks."
        ),
        pattern="^(pending|in_progress|completed)$",
    ),
) -> list[Task]:
    """List all tasks, optionally filtered by status."""
    if status is None:
        return TASKS
    return [task for task in TASKS if task.status == status]


# --- Internal API (/internal) — never published to customer docs --------------


@app.get(
    "/internal/health",
    tags=["Internal"],
    operation_id="getHealth",
    summary="Service health check",
    description="Internal liveness probe used by load balancers and uptime monitors.",
)
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


@app.get(
    "/internal/admin/users",
    tags=["Internal"],
    operation_id="adminListUsers",
    summary="Admin view of all users (internal)",
    description=(
        "Internal admin endpoint. Exposes internal fields (audit metadata, "
        "last login IP) that must never appear in customer documentation."
    ),
)
def admin_list_users() -> list[dict]:
    """Admin-only user listing with internal metadata."""
    return [
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "internal_audit_note": "created via internal migration",
        }
        for user in USERS
    ]
