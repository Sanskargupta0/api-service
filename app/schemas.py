"""Pydantic models for the PioAgent customer API."""

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """A user account in a PioAgent workspace."""

    id: str = Field(description="Stable identifier for the user, e.g. `usr_001`.")
    email: EmailStr = Field(description="The user's email address.")
    name: str = Field(description="The user's display name.")
    is_active: bool = Field(description="Whether the user can currently sign in.")


class Task(BaseModel):
    """A unit of work created and executed by an agent."""

    id: str = Field(description="Stable identifier for the task, e.g. `task_001`.")
    title: str = Field(description="Human-readable summary of the task.")
    status: str = Field(
        description="Current lifecycle state of the task.",
        pattern="^(pending|in_progress|completed)$",
    )
    assignee_id: str | None = Field(
        default=None,
        description="ID of the user assigned to this task, if any.",
    )
