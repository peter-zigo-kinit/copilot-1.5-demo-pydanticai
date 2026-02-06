"use client";

import { useCopilotChatInternal, useThreads } from "@copilotkit/react-core";
import type { Message as AGUIMessage } from "@ag-ui/core";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { useEffect, useState } from "react";

type ThreadSummary = {
  thread_id: string;
  title: string;
  message_count: number;
};

export default function CopilotKitPage() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const { setThreadId } = useThreads();
  const { setMessages } = useCopilotChatInternal();

  useEffect(() => {
    const loadThreads = async () => {
      try {
        const response = await fetch("http://localhost:8000/threads");
        if (!response.ok) {
          return;
        }
        const data = (await response.json()) as ThreadSummary[];
        setThreads(data);
        if (data.length > 0 && !activeThreadId) {
          setActiveThreadId(data[0].thread_id);
        }
      } catch (error) {
        console.error("Failed to load threads", error);
      }
    };
    loadThreads();
  }, []);

  useEffect(() => {
    if (!activeThreadId) {
      return;
    }
    setThreadId(activeThreadId);
  }, [activeThreadId, setThreadId]);

  useEffect(() => {
    if (!activeThreadId) {
      return;
    }
    const loadHistory = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/threads/${activeThreadId}/messages`,
        );
        if (!response.ok) {
          return;
        }
        const data = (await response.json()) as AGUIMessage[];
        setMessages(data);
      } catch (error) {
        console.error("Failed to load thread messages", error);
      }
    };
    loadHistory();
  }, [activeThreadId, setMessages]);

  return (
    <main className="h-screen grid grid-cols-[1fr_260px]">
      <section className="bg-white p-4">
        {activeThreadId ? (
          <CopilotChat key={activeThreadId} threadId={activeThreadId} />
        ) : (
          <div className="text-sm text-slate-500">
            Select a conversation to start chatting.
          </div>
        )}
      </section>
      <aside className="border-l border-slate-200 bg-slate-50 p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-600">
          Conversations
        </h2>
        <div className="space-y-2">
          {threads.map((thread) => (
            <button
              key={thread.thread_id}
              onClick={() => setActiveThreadId(thread.thread_id)}
              className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                thread.thread_id === activeThreadId
                  ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                  : "border-slate-200 bg-white text-slate-700 hover:border-indigo-200"
              }`}
            >
              <div className="font-medium">{thread.title}</div>
              <div className="text-xs text-slate-500">
                {thread.message_count} messages
              </div>
            </button>
          ))}
          {threads.length === 0 && (
            <div className="text-sm text-slate-500">No threads loaded.</div>
          )}
        </div>
      </aside>
    </main>
  );
}
