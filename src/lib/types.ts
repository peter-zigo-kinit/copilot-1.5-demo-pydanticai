// State of the agent, make sure this aligns with your agent's state.
export type AgentState = {
  tasks: { name: string; status: string }[];
  datasets: { name: string; status: string }[];
}