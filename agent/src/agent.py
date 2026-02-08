from textwrap import dedent
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.ag_ui import StateDeps
from ag_ui.core import EventType, StateSnapshotEvent
from pydantic_ai.models.openai import OpenAIResponsesModel

# load environment variables
from dotenv import load_dotenv
load_dotenv()

# =====
# State
# =====
class TaskItem(BaseModel):
  name: str
  status: str = Field(default="pending")


class DatasetItem(BaseModel):
  name: str
  status: str = Field(default="pending")


class MLState(BaseModel):
  """Tracks ML tasks and datasets with statuses."""
  tasks: list[TaskItem] = Field(default_factory=list)
  datasets: list[DatasetItem] = Field(default_factory=list)

# =====
# Agent
# =====
agent = Agent(
  model = OpenAIResponsesModel('gpt-4.1-mini'),
  deps_type=StateDeps[MLState],
  system_prompt=dedent("""
    You are a helpful assistant that helps manage machine learning tasks and datasets.
    
    The user tracks tasks and datasets with statuses. Use the tools to list or update
    tasks and datasets before referencing them in your response.
  """).strip()
)

# =====
# Tools
# =====
@agent.tool
def get_tasks(ctx: RunContext[StateDeps[MLState]]) -> list[TaskItem]:
  """Get the current list of ML tasks."""
  print(f"🧠 Getting tasks: {ctx.deps.state.tasks}")
  return ctx.deps.state.tasks

@agent.tool
async def add_tasks(ctx: RunContext[StateDeps[MLState]], tasks: list[TaskItem]) -> StateSnapshotEvent:
  ctx.deps.state.tasks.extend(tasks)
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=ctx.deps.state,
  )

@agent.tool
async def set_tasks(ctx: RunContext[StateDeps[MLState]], tasks: list[TaskItem]) -> StateSnapshotEvent:
  ctx.deps.state.tasks = tasks
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=ctx.deps.state,
  )


@agent.tool
def get_datasets(ctx: RunContext[StateDeps[MLState]]) -> list[DatasetItem]:
  """Get the current list of datasets."""
  print(f"📊 Getting datasets: {ctx.deps.state.datasets}")
  return ctx.deps.state.datasets


@agent.tool
async def add_datasets(ctx: RunContext[StateDeps[MLState]], datasets: list[DatasetItem]) -> StateSnapshotEvent:
  ctx.deps.state.datasets.extend(datasets)
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=ctx.deps.state,
  )


@agent.tool
async def set_datasets(ctx: RunContext[StateDeps[MLState]], datasets: list[DatasetItem]) -> StateSnapshotEvent:
  ctx.deps.state.datasets = datasets
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=ctx.deps.state,
  )


@agent.tool
def get_weather(_: RunContext[StateDeps[MLState]], location: str) -> str:
  """Get the weather for a given location. Ensure location is fully spelled out."""
  return f"The weather in {location} is sunny."
