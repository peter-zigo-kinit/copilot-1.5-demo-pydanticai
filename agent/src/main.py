from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func
from sqlmodel import SQLModel, Session, select

from pydantic_ai.ag_ui import SSE_CONTENT_TYPE, run_ag_ui
from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart
from pydantic_ai.ui.ag_ui._adapter import AGUIAdapter

from agent import MLState, StateDeps, agent
from db import engine
from models import Message, State, Thread, ThreadMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("threads")

ModelMessageAdapter = TypeAdapter(ModelMessage)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/threads")
def list_threads() -> list[dict[str, Any]]:
    with Session(engine) as session:
        threads = session.exec(select(Thread).order_by(Thread.updated_at.desc())).all()
        response: list[dict[str, Any]] = []
        for thread in threads:
            message_count = session.exec(
                select(func.count(Message.id)).where(Message.thread_id == thread.id)
            ).one()
            response.append(
                {
                    "thread_id": str(thread.id),
                    "title": thread.title,
                    "message_count": message_count,
                }
            )
        return response


def _model_messages_to_chat(messages: list[ModelMessage], thread_id: str) -> list[dict[str, Any]]:
    chat_messages: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        message_id = f"{thread_id}-history-{index}"
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    chat_messages.append(
                        {
                            "id": message_id,
                            "role": "user",
                            "content": part.content,
                        }
                    )
                    break
        elif isinstance(message, ModelResponse):
            text = message.text
            if text:
                chat_messages.append(
                    {
                        "id": message_id,
                        "role": "assistant",
                        "content": text,
                    }
                )
    return chat_messages


@app.get("/threads/{thread_id}")
def get_thread(thread_id: str) -> dict[str, Any]:
    with Session(engine) as session:
        thread_uuid = _parse_thread_id(thread_id)
        if not thread_uuid:
            return {
                "thread_id": thread_id,
                "title": "New thread",
                "state": MLState().model_dump(),
            }
        thread = session.get(Thread, thread_uuid)
        if not thread:
            return {
                "thread_id": thread_id,
                "title": "New thread",
                "state": MLState().model_dump(),
            }
        state = session.exec(select(State).where(State.thread_id == thread.id)).first()
        return {
            "thread_id": str(thread.id),
            "title": thread.title,
            "state": state.state_json if state else MLState().model_dump(),
        }


@app.get("/threads/{thread_id}/messages")
def get_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    with Session(engine) as session:
        thread_uuid = _parse_thread_id(thread_id)
        if not thread_uuid:
            return []
        thread = session.get(Thread, thread_uuid)
        if not thread:
            return []
        stored_messages = session.exec(
            select(Message).where(Message.thread_id == thread.id).order_by(Message.created_at)
        ).all()
        model_messages = [
            ModelMessageAdapter.validate_python(message.message_json)
            for message in stored_messages
        ]
        chat_messages = _model_messages_to_chat(model_messages, thread_id)
        logger.info("Thread %s history requested, returning %s messages", thread_id, len(chat_messages))
        return chat_messages


@app.post("/agent")
async def ag_ui_endpoint(request: Request) -> StreamingResponse:
    run_input = RunAgentInput.model_validate_json(await request.body())
    session = Session(engine)
    thread_uuid = _parse_thread_id(run_input.thread_id)
    if not thread_uuid:
        thread_uuid = uuid.uuid5(uuid.NAMESPACE_URL, run_input.thread_id)
    thread = session.get(Thread, thread_uuid)
    if not thread:
        thread = Thread(id=thread_uuid, user_id="demo-user", title=f"Thread {run_input.thread_id}")
        session.add(thread)
        session.add(State(thread_id=thread.id, state_json=MLState().model_dump()))
        session.commit()
        logger.info("Thread %s created", run_input.thread_id)

    state_row = session.exec(select(State).where(State.thread_id == thread.id)).first()
    stored_state = state_row.state_json if state_row else MLState().model_dump()

    metadata = thread.thread_metadata or ThreadMetadata()
    known_ids = set((metadata.custom_data or {}).get("known_message_ids", []))
    new_agui_messages = [message for message in run_input.messages if message.id not in known_ids]
    if new_agui_messages:
        known_ids.update(message.id for message in new_agui_messages)
        metadata.custom_data = {
            **(metadata.custom_data or {}),
            "known_message_ids": list(known_ids),
        }
        thread.thread_metadata = metadata
        session.add(thread)
        session.commit()
        logger.info(
            "Thread %s received %s new messages (known=%s)",
            run_input.thread_id,
            len(new_agui_messages),
            len(known_ids),
        )

    stored_messages = session.exec(
        select(Message).where(Message.thread_id == thread.id).order_by(Message.created_at)
    ).all()
    model_messages = [
        ModelMessageAdapter.validate_python(message.message_json)
        for message in stored_messages
    ]
    message_history = model_messages
    if new_agui_messages:
        incoming_messages = AGUIAdapter.load_messages(new_agui_messages)
        message_history = [*model_messages, *incoming_messages]

    run_input = run_input.model_copy(update={"messages": new_agui_messages})

    deps = StateDeps(MLState.model_validate(stored_state))

    def on_complete(result: Any) -> None:
        session.exec(delete(Message).where(Message.thread_id == thread.id))
        for message in result.all_messages():
            session.add(
                Message(
                    thread_id=thread.id,
                    message_json=ModelMessageAdapter.dump_python(message, mode="json"),
                )
            )
        if state_row:
            state_row.state_json = deps.state.model_dump()
            session.add(state_row)
        else:
            session.add(State(thread_id=thread.id, state_json=deps.state.model_dump()))
        session.commit()
        logger.info(
            "Thread %s stored messages=%s state_tasks=%s datasets=%s",
            run_input.thread_id,
            len(result.all_messages()),
            len(deps.state.tasks),
            len(deps.state.datasets),
        )

    accept = request.headers.get("accept", SSE_CONTENT_TYPE)
    stream = run_ag_ui(
        agent,
        run_input,
        accept=accept,
        message_history=message_history,
        deps=deps,
        on_complete=on_complete,
    )

    async def stream_with_session():
        try:
            async for event in stream:
                yield event
        finally:
            session.close()

    return StreamingResponse(stream_with_session(), media_type=accept)


def _parse_thread_id(thread_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(thread_id)
    except ValueError:
        return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
