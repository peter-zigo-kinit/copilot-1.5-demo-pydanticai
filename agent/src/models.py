import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    thread_id: uuid.UUID = Field(foreign_key="threads.id", nullable=False)
    message_json: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    thread: "Thread" = Relationship(back_populates="messages")


class State(SQLModel, table=True):
    __tablename__ = "states"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    thread_id: uuid.UUID = Field(
        foreign_key="threads.id",
        nullable=False,
        sa_column_kwargs={"unique": True},
    )
    state_json: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    thread: "Thread" = Relationship(back_populates="state")


class ThreadMetadata(SQLModel):
    """A model for thread metadata."""

    source: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_data: Optional[Dict[str, Any]] = None


class Thread(SQLModel, table=True):
    __tablename__ = "threads"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(nullable=False)
    title: str = Field(default="New Thread", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )
    metadata_json: Optional[str] = Field(
        default=None, sa_column=JSONB, alias="thread_metadata"
    )

    @property
    def thread_metadata(self) -> Optional[ThreadMetadata]:
        if self.metadata_json:
            data = json.loads(self.metadata_json)
            return ThreadMetadata(**data)
        return None

    @thread_metadata.setter
    def thread_metadata(self, value: Optional[ThreadMetadata]):
        if value:
            self.metadata_json = json.dumps(value.model_dump())
        else:
            self.metadata_json = None

    messages: List[Message] = Relationship(back_populates="thread")
    state: Optional[State] = Relationship(
        back_populates="thread", sa_relationship_kwargs={"uselist": False}
    )
