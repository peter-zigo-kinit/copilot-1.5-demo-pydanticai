# Project Instructions

## Primary Focus
- Implement CopilotKit v1.50 + Pydantic AI integrations with AG-UI.
- Prefer thread-based chat history and full snapshot state persistence.
- Use database-backed storage for messages and state in production designs.

## Frontend Guidance
- Use `CopilotChat` from `@copilotkit/react-core/v2`.
- Wire thread switching via `useThreads().setThreadId(...)`.
- Load history from backend and update the chat via `useCopilotChatInternal().setMessages(...)`.
- Use `@copilotkit/react-ui/v2/styles.css` for chat styling.

## Backend Guidance
- Expose `POST /agent` for AG-UI streaming requests.
- Expose `GET /threads/{id}/messages` to preload UI history.
- Persist Pydantic AI `ModelMessage` lists using `ModelMessagesTypeAdapter`.
- Persist full state snapshots per thread; avoid state deltas for storage.

## Conventions
- Keep endpoints and message formats consistent with AG-UI specs.
- Log thread IDs and message counts when debugging history issues.
