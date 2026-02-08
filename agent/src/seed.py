from __future__ import annotations

from datetime import datetime
import argparse

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from sqlmodel import SQLModel, Session, select

from db import engine
import uuid

from models import Message, State, Thread

ModelMessageAdapter = TypeAdapter(ModelMessage)


def _user_message(content: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=content, timestamp=datetime.utcnow())])


def _assistant_message(content: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=content)], timestamp=datetime.utcnow())


def _seed_threads():
    return [
        {
            "thread_id": "c7155bf0-0eea-4392-a071-3cce1cc51db4",
            "title": "ML Basics",
            "messages": [
                ("user", "What is overfitting?"),
                (
                    "assistant",
                    "Overfitting is when a model fits training data too closely and fails to generalize.",
                ),
                ("user", "How do I reduce it?"),
                (
                    "assistant",
                    "Use regularization, early stopping, more data, or simpler models.",
                ),
            ],
            "state": {
                "tasks": [
                    {"name": "Train baseline model", "status": "done"},
                    {"name": "Tune regularization", "status": "in_progress"},
                ],
                "datasets": [
                    {"name": "MNIST", "status": "ready"},
                    {"name": "CIFAR-10", "status": "pending"},
                ],
            },
        },
        {
            "thread_id": "c5e6cf63-8205-4300-9aab-10e79f19025a",
            "title": "Feature Engineering",
            "messages": [
                ("user", "How do I scale features?"),
                (
                    "assistant",
                    "Standardization and min-max scaling are common, depending on your model.",
                ),
                ("user", "When should I use one-hot encoding?"),
                (
                    "assistant",
                    "Use one-hot encoding for categorical variables without ordinal relationships.",
                ),
            ],
            "state": {
                "tasks": [
                    {"name": "Audit feature distributions", "status": "done"},
                    {"name": "Build preprocessing pipeline", "status": "in_progress"},
                ],
                "datasets": [
                    {"name": "House Prices", "status": "ready"},
                    {"name": "Customer Churn", "status": "ready"},
                ],
            },
        },
        {
            "thread_id": "aa5e6b5a-f602-414f-abbd-4e8108d0b3fd",
            "title": "Model Evaluation",
            "messages": [
                ("user", "Explain ROC-AUC."),
                (
                    "assistant",
                    "ROC-AUC measures how well a model ranks positives above negatives across thresholds.",
                ),
                ("user", "What about precision vs recall?"),
                (
                    "assistant",
                    "Precision is correctness of positive predictions; recall is coverage of actual positives.",
                ),
            ],
            "state": {
                "tasks": [
                    {"name": "Run cross-validation", "status": "pending"},
                    {"name": "Compare metrics", "status": "pending"},
                ],
                "datasets": [
                    {"name": "Fraud Detection", "status": "ready"},
                    {"name": "Click Through Rate", "status": "pending"},
                ],
            },
        },
    ]


def seed(drop_all: bool = False) -> None:
    if drop_all:
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing = {
            thread.id for thread in session.exec(select(Thread.id)).all()
        }
        for thread_data in _seed_threads():
            if thread_data["thread_id"] in existing:
                continue

            thread = Thread(
                id=uuid.UUID(thread_data["thread_id"]),
                user_id="seed-user",
                title=thread_data["title"],
            )
            session.add(thread)
            session.add(State(thread_id=thread.id, state_json=thread_data["state"]))

            for index, (role, content) in enumerate(thread_data["messages"]):
                if role == "user":
                    message = _user_message(content)
                else:
                    message = _assistant_message(content)

                session.add(
                    Message(
                        thread_id=thread.id,
                        message_json=ModelMessageAdapter.dump_python(message, mode="json"),
                    )
                )

        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Postgres with demo ML threads.")
    parser.add_argument(
        "--drop-all",
        action="store_true",
        help="Drop all tables before seeding.",
    )
    args = parser.parse_args()
    seed(drop_all=args.drop_all)
