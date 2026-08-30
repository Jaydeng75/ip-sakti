"use client";

import { useEffect, useState } from "react";
import { MOCK_CASE, MOCK_EVIDENCE } from "@/lib/mock-data";
import { getCurrentCase } from "@/lib/case-store";

type Message = {
  role: "user" | "assistant";
  text: string;
};

type CurrentCase = typeof MOCK_CASE;

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [currentCase, setCurrentCase] = useState<CurrentCase>(MOCK_CASE);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Ask me about your innovation, evidence, IP strategy, or regulatory position.",
    },
  ]);
  const [selectedSource, setSelectedSource] = useState(0);

  useEffect(() => {
    setCurrentCase(getCurrentCase());
  }, []);

  function askQuestion() {
    const trimmed = question.trim();

    if (!trimmed) return;

    setMessages((current) => [
      ...current,
      {
        role: "user",
        text: trimmed,
      },
      {
        role: "assistant",
        text: "Based on the current case evidence, the strongest next step is to separate what is traditionally known from what may be technically distinctive. The available evidence also shows areas that still need confirmation.",
      },
    ]);

    setQuestion("");
  }

  return (
    <main className="min-h-screen bg-background text-ink">
      <div className="mx-auto max-w-7xl px-6 py-10 md:px-10 md:py-14">
        {/* HEADER */}
        <header className="border-b border-border pb-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
            IP-SAKTI 360 / Ask IP-SAKTI
          </p>

          <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">
            Ask about your case.
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted">
            Get answers alongside the evidence behind them. Important
            conclusions should remain traceable to their source.
          </p>
        </header>

        {/* CASE BAR */}
        <div className="mt-6 flex flex-wrap items-center gap-2">
          <span className="max-w-full rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">
            {currentCase.productDescription}
          </span>

          <span className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-muted">
            {currentCase.jurisdiction}
          </span>
        </div>

        {/* WORKSPACE */}
        <section className="mt-6 grid min-h-[680px] gap-6 lg:grid-cols-[1fr_380px]">
          {/* CHAT */}
          <div className="flex min-h-[680px] flex-col rounded-3xl border border-border bg-surface">
            <div className="border-b border-border px-6 py-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                Conversation
              </p>

              <p className="mt-1 text-sm text-ink-muted">
                Evidence-aware answers for the current case
              </p>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto p-6">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={
                    message.role === "user"
                      ? "ml-auto max-w-[80%] rounded-2xl bg-accent px-5 py-4 text-sm leading-6 text-white"
                      : "max-w-[85%] rounded-2xl bg-background px-5 py-4 text-sm leading-7 text-ink"
                  }
                >
                  <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.16em] opacity-60">
                    {message.role === "user" ? "You" : "IP-SAKTI"}
                  </p>

                  {message.text}
                </div>
              ))}
            </div>

            {/* INPUT */}
            <div className="border-t border-border p-4">
              <div className="rounded-2xl border border-border bg-background p-3 focus-within:border-accent">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      askQuestion();
                    }
                  }}
                  placeholder="Ask a question about your innovation..."
                  className="min-h-24 w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 outline-none placeholder:text-ink-muted/50"
                />

                <div className="flex items-center justify-between border-t border-border px-2 pt-3">
                  <span className="text-[11px] text-ink-muted">
                    Shift + Enter for a new line
                  </span>

                  <button
                    type="button"
                    onClick={askQuestion}
                    disabled={!question.trim()}
                    className="rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Ask →
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* EVIDENCE PANEL */}
          <aside className="flex min-h-[680px] flex-col rounded-3xl border border-border bg-surface">
            <div className="border-b border-border px-6 py-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                Evidence panel
              </p>

              <h2 className="mt-1 text-xl font-semibold tracking-tight">
                Sources behind the answer
              </h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-2">
                {MOCK_EVIDENCE.map((item, index) => {
                  const selected = selectedSource === index;

                  return (
                    <button
                      key={`${item.source}-${index}`}
                      type="button"
                      onClick={() => setSelectedSource(index)}
                      className={`w-full rounded-2xl border p-4 text-left transition ${
                        selected
                          ? "border-accent bg-accent-subtle"
                          : "border-border hover:bg-background"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-medium leading-5">
                          {item.source}
                        </p>

                        <span className="shrink-0 font-mono text-[9px] text-ink-muted">
                          SRC-{String(index + 1).padStart(2, "0")}
                        </span>
                      </div>

                      <p className="mt-2 text-xs text-ink-muted">
                        {item.authority}
                      </p>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="rounded-full bg-surface px-2.5 py-1 text-[10px] text-ink-muted">
                          {item.status}
                        </span>

                        <span className="rounded-full bg-surface px-2.5 py-1 text-[10px] text-ink-muted">
                          {item.confidence} confidence
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* SELECTED SOURCE */}
            <div className="border-t border-border bg-background p-5">
              <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink-muted">
                Selected source
              </p>

              <h3 className="mt-2 text-sm font-semibold leading-5">
                {MOCK_EVIDENCE[selectedSource].source}
              </h3>

              <div className="mt-4 space-y-2 text-xs leading-5 text-ink-muted">
                <p>
                  <span className="font-medium text-ink">Authority:</span>{" "}
                  {MOCK_EVIDENCE[selectedSource].authority}
                </p>

                <p>
                  <span className="font-medium text-ink">Section:</span>{" "}
                  {MOCK_EVIDENCE[selectedSource].section}
                </p>

                <p>
                  <span className="font-medium text-ink">Support:</span>{" "}
                  {MOCK_EVIDENCE[selectedSource].status}
                </p>

                <p>
                  <span className="font-medium text-ink">Confidence:</span>{" "}
                  {MOCK_EVIDENCE[selectedSource].confidence}
                </p>
              </div>
            </div>
          </aside>
        </section>

        {/* EVIDENCE RULE */}
        <div className="mt-6 rounded-2xl border border-warm/20 bg-warm-subtle p-5">
          <p className="text-sm font-semibold text-warm">
            Evidence boundary
          </p>

          <p className="mt-2 text-sm leading-6 text-ink-muted">
            Answers should distinguish direct facts from interpretation,
            inference, and unsupported claims.
          </p>
        </div>
      </div>
    </main>
  );
}