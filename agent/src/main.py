from __future__ import annotations

import logging
from typing import Any, TypedDict

from ag_ui.core import AssistantMessage, RunAgentInput, UserMessage
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic_ai.ag_ui import SSE_CONTENT_TYPE, run_ag_ui
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart
from pydantic_ai.ui.ag_ui._adapter import AGUIAdapter

from agent import ProverbsState, StateDeps, agent


class ThreadRecord(TypedDict):
    title: str
    messages: list[ModelMessage]
    state: dict[str, Any]
    agui_message_ids: set[str]


def _build_thread(
    *,
    title: str,
    state: dict[str, Any],
    agui_messages: list[UserMessage | AssistantMessage],
) -> ThreadRecord:
    return {
        "title": title,
        "messages": AGUIAdapter.load_messages(agui_messages),
        "state": state,
        "agui_message_ids": {message.id for message in agui_messages},
    }


THREADS: dict[str, ThreadRecord] = {
    "thread-1": _build_thread(
        title="Proverbs A",
        state={"proverbs": ["A stitch in time saves nine."]},
        agui_messages=[
            UserMessage(id="t1-user-1", content="Add a proverb about time."),
            AssistantMessage(id="t1-assistant-1", content="Added: A stitch in time saves nine."),
        ],
    ),
    "thread-2": _build_thread(
        title="Proverbs B",
        state={"proverbs": ["Measure twice, cut once."]},
        agui_messages=[
            UserMessage(id="t2-user-1", content="Give me a proverb about planning."),
            AssistantMessage(id="t2-assistant-1", content="Measure twice, cut once."),
        ],
    ),
    "thread-3": _build_thread(
        title="Proverbs C",
        state={"proverbs": []},
        agui_messages=[
            UserMessage(id="t3-user-1", content="Start a new list of proverbs."),
            AssistantMessage(id="t3-assistant-1", content="Started a new list with zero items."),
        ],
    ),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("threads")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/threads")
def list_threads() -> list[dict[str, Any]]:
    return [
        {
            "thread_id": thread_id,
            "title": record["title"],
            "message_count": len(record["messages"]),
        }
        for thread_id, record in THREADS.items()
    ]


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
    record = THREADS.get(thread_id)
    if not record:
        return {"thread_id": thread_id, "title": "New thread", "state": {"proverbs": []}}
    return {"thread_id": thread_id, "title": record["title"], "state": record["state"]}


@app.get("/threads/{thread_id}/messages")
def get_thread_messages(thread_id: str) -> list[dict[str, Any]]:
    record = THREADS.get(thread_id)
    if not record:
        return []
    chat_messages = _model_messages_to_chat(record["messages"], thread_id)
    logger.info("Thread %s history requested, returning %s messages", thread_id, len(chat_messages))
    return chat_messages


@app.post("/agent")
async def ag_ui_endpoint(request: Request) -> StreamingResponse:
    run_input = RunAgentInput.model_validate_json(await request.body())
    is_new_thread = run_input.thread_id not in THREADS
    record = THREADS.setdefault(
        run_input.thread_id,
        {
            "title": f"Thread {run_input.thread_id}",
            "messages": [],
            "state": {"proverbs": []},
            "agui_message_ids": set(),
        },
    )
    if is_new_thread:
        logger.info("Thread %s created", run_input.thread_id)

    known_ids = record["agui_message_ids"]
    new_agui_messages = [message for message in run_input.messages if message.id not in known_ids]
    if new_agui_messages:
        known_ids.update(message.id for message in new_agui_messages)
        logger.info(
            "Thread %s received %s new messages (known=%s)",
            run_input.thread_id,
            len(new_agui_messages),
            len(known_ids),
        )

    stored_messages = record["messages"]
    message_history = stored_messages
    if new_agui_messages:
        incoming_messages = AGUIAdapter.load_messages(new_agui_messages)
        message_history = [*stored_messages, *incoming_messages]

    run_input = run_input.model_copy(update={"messages": new_agui_messages})

    deps = StateDeps(ProverbsState.model_validate(record["state"]))

    def on_complete(result: Any) -> None:
        record["messages"] = result.all_messages()
        if isinstance(deps.state, ProverbsState):
            record["state"] = deps.state.model_dump()
        logger.info(
            "Thread %s stored messages=%s state_proverbs=%s",
            run_input.thread_id,
            len(record["messages"]),
            len(record["state"].get("proverbs", [])),
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
    return StreamingResponse(stream, media_type=accept)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
