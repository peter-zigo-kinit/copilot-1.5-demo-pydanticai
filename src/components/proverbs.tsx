import { AgentState } from "@/lib/types";

export interface ProverbsCardProps {
  state: AgentState;
  setState: (state: AgentState) => void;
}

export function ProverbsCard({ state, setState }: ProverbsCardProps) {
  return (
    <div className="bg-white/20 backdrop-blur-md p-8 rounded-2xl shadow-xl max-w-2xl w-full">
      <h1 className="text-4xl font-bold text-white mb-2 text-center">ML Workbench</h1>
      <p className="text-gray-200 text-center italic mb-6">
        Track tasks and datasets with the assistant.
      </p>
      <hr className="border-white/20 my-6" />
      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-white">Tasks</h2>
          {state.tasks?.map((task, index) => (
            <div
              key={index}
              className="bg-white/15 p-4 rounded-xl text-white relative group hover:bg-white/20 transition-all"
            >
              <p className="pr-8 font-medium">{task.name}</p>
              <p className="text-xs uppercase tracking-wide text-white/70">{task.status}</p>
              <button
                onClick={() =>
                  setState({
                    ...state,
                    tasks: state.tasks?.filter((_, i) => i !== index),
                  })
                }
                className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity 
                bg-red-500 hover:bg-red-600 text-white rounded-full h-6 w-6 flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ))}
          {state.tasks?.length === 0 && (
            <p className="text-center text-white/80 italic my-4">
              No tasks yet. Ask the assistant to add one!
            </p>
          )}
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-white">Datasets</h2>
          {state.datasets?.map((dataset, index) => (
            <div
              key={index}
              className="bg-white/15 p-4 rounded-xl text-white relative group hover:bg-white/20 transition-all"
            >
              <p className="pr-8 font-medium">{dataset.name}</p>
              <p className="text-xs uppercase tracking-wide text-white/70">{dataset.status}</p>
              <button
                onClick={() =>
                  setState({
                    ...state,
                    datasets: state.datasets?.filter((_, i) => i !== index),
                  })
                }
                className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity 
                bg-red-500 hover:bg-red-600 text-white rounded-full h-6 w-6 flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ))}
          {state.datasets?.length === 0 && (
            <p className="text-center text-white/80 italic my-4">
              No datasets yet. Ask the assistant to add one!
            </p>
          )}
        </section>
      </div>
    </div>
  );
}