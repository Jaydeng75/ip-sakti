"use client";

import Link from "next/link";
import { useState } from "react";
import { AskResponse, Citation, caseApi } from "@/lib/api";
import { useCurrentCase } from "@/lib/use-current-case";

type Message = { role: "user" | "assistant"; text: string; response?: AskResponse };

const quickQuestions = [
  "What is the strongest patent opportunity in India?",
  "Which evidence gaps matter before making claims?",
  "What biological-resource and ABS facts must I document?",
];

const languages = [
  "English", "Assamese", "Bengali", "Bodo", "Dogri", "Gujarati", "Hindi", "Kannada", "Kashmiri", "Konkani",
  "Maithili", "Malayalam", "Manipuri", "Marathi", "Nepali", "Odia", "Punjabi", "Sanskrit", "Santali", "Sindhi",
  "Tamil", "Telugu", "Urdu",
];

export default function AskPage() {
  const currentCase = useCurrentCase();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", text: "Ask about this innovation case. I will answer only from the curated source registry and clearly mark interpretation, confidence and limitations." },
  ]);
  const [activeResponse, setActiveResponse] = useState<AskResponse | null>(null);
  const [selectedSource, setSelectedSource] = useState<Citation | null>(null);
  const [asking, setAsking] = useState(false);
  const [inputLanguage, setInputLanguage] = useState("English");
  const [responseLanguage, setResponseLanguage] = useState("English");
  const [error, setError] = useState<string | null>(null);

  async function ask(prompt = question, questionLanguage = inputLanguage) {
    const trimmed = prompt.trim();
    if (!trimmed || asking || !currentCase.backendId) return;
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setQuestion("");
    setAsking(true);
    setError(null);
    try {
      const response = await caseApi.ask(currentCase.backendId, trimmed, questionLanguage, responseLanguage);
      setMessages((current) => [...current, { role: "assistant", text: response.answer, response }]);
      setActiveResponse(response);
      setSelectedSource(response.citations[0] ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The assistant could not answer.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="py-8 md:py-10">
      <header className="border-b border-border pb-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">IP-SAKTI 360 / Ask IP-SAKTI</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight md:text-5xl">Ask with the evidence visible.</h1>
        <p className="mt-3 max-w-3xl text-base leading-7 text-ink-muted">Every substantive answer is labelled as fact, interpretation, inference or unsupported, with source authority, jurisdiction, date and support status.</p>
      </header>

      {!currentCase.backendId ? (
        <div className="mt-8 rounded-3xl border border-border bg-surface p-8"><h2 className="text-2xl font-semibold">Create an analysis case first.</h2><p className="mt-2 text-sm text-ink-muted">The assistant preserves case context and will not answer without a linked, source-grounded analysis.</p><Link href="/analyze" className="mt-5 inline-flex rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white">Analyze an innovation →</Link></div>
      ) : (
        <>
          <div className="mt-6 flex flex-wrap items-center gap-2"><span className="max-w-full truncate rounded-full bg-accent-subtle px-3 py-1.5 text-xs font-medium text-accent">{currentCase.title}</span><span className="rounded-full border border-border px-3 py-1.5 font-mono text-[10px] text-ink-muted">CASE-{String(currentCase.backendId).padStart(5, "0")}</span></div>
          <div className="mt-4 flex flex-wrap gap-2">{quickQuestions.map((prompt) => <button key={prompt} type="button" onClick={() => void ask(prompt, "English")} className="rounded-full border border-border bg-surface px-3 py-2 text-xs text-ink-muted transition hover:border-accent hover:text-accent">{prompt}</button>)}</div>

          <section className="mt-6 grid min-h-[680px] gap-6 lg:grid-cols-[1fr_410px]">
            <div className="flex min-h-[680px] flex-col overflow-hidden rounded-3xl border border-border bg-surface">
              <div className="border-b border-border px-6 py-5"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Case conversation</p><p className="mt-1 text-sm text-ink-muted">Grounded retrieval · safe abstention enabled</p></div>
              <div className="flex-1 space-y-5 overflow-y-auto p-6">
                {messages.map((message, index) => (
                  <button key={`${message.role}-${index}`} type="button" onClick={() => { if (message.response) { setActiveResponse(message.response); setSelectedSource(message.response.citations[0] ?? null); } }} className={`block text-left ${message.role === "user" ? "ml-auto max-w-[82%] rounded-2xl bg-accent px-5 py-4 text-white" : "max-w-[90%] rounded-2xl bg-background px-5 py-4 text-ink"}`}>
                    <span className="font-mono text-[9px] uppercase tracking-[0.16em] opacity-60">{message.role === "user" ? "You" : "IP-SAKTI"}</span>
                    <span className="mt-2 block text-sm leading-7">{message.text}</span>
                    {message.response && <span className="mt-3 flex flex-wrap gap-2"><Badge>{message.response.claim_type.replaceAll("_", " ")}</Badge><Badge>{Math.round(message.response.confidence * 100)}% confidence</Badge><Badge>{message.response.citations.length} sources</Badge>{message.response.output_translation.machine_translated && <Badge>IndicTrans2 translation</Badge>}</span>}
                  </button>
                ))}
                {asking && <div className="max-w-[90%] animate-pulse rounded-2xl bg-background px-5 py-4 text-sm text-ink-muted">Retrieving relevant primary sources…</div>}
                {error && <div role="alert" className="rounded-xl bg-danger-subtle p-4 text-sm text-danger">{error}</div>}
              </div>
              <div className="border-t border-border p-4"><div className="rounded-2xl border border-border bg-background p-3 focus-within:border-accent"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void ask(); } }} placeholder="Ask a legal, evidence, patent, ABS or market question…" className="min-h-24 w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 outline-none" /><div className="flex flex-wrap items-end justify-between gap-3 border-t border-border px-2 pt-3"><div className="flex flex-wrap gap-3"><LanguageSelect label="Question language" value={inputLanguage} onChange={setInputLanguage} /><LanguageSelect label="Answer language" value={responseLanguage} onChange={setResponseLanguage} /></div><button type="button" onClick={() => void ask()} disabled={!question.trim() || asking} className="rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40">Ask →</button></div></div><p className="px-2 pt-2 text-[10px] leading-4 text-ink-muted">Non-English text is machine translated by IndicTrans2. Citations and the authoritative answer remain tied to the English source analysis.</p></div>
            </div>

            <aside className="flex min-h-[680px] flex-col overflow-hidden rounded-3xl border border-border bg-surface">
              <div className="border-b border-border px-6 py-5"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Live evidence panel</p><h2 className="mt-1 text-xl font-semibold">Sources behind the answer</h2></div>
              <div className="flex-1 overflow-y-auto p-4">
                {!activeResponse ? <p className="rounded-2xl border border-dashed border-border p-5 text-sm leading-6 text-ink-muted">Ask a question to retrieve relevant primary law, official guidance and treaty material.</p> : activeResponse.citations.length ? <div className="space-y-2">{activeResponse.citations.map((citation) => <button key={citation.id} type="button" onClick={() => setSelectedSource(citation)} className={`w-full rounded-2xl border p-4 text-left transition ${selectedSource?.id === citation.id ? "border-accent bg-accent-subtle" : "border-border hover:bg-background"}`}><div className="flex items-start justify-between gap-3"><p className="text-sm font-semibold leading-5">{citation.title}</p><span className="font-mono text-[9px] text-ink-muted">{citation.jurisdiction}</span></div><p className="mt-2 text-xs text-ink-muted">{citation.authority}</p><div className="mt-3 flex flex-wrap gap-2"><Badge>{citation.support_status}</Badge><Badge>{citation.effective_date}</Badge></div></button>)}</div> : <p className="rounded-2xl border border-warm/30 bg-warm-subtle p-5 text-sm leading-6 text-warm">Safe abstention: no relevant source supported this answer.</p>}
              </div>
              {selectedSource && <div className="border-t border-border bg-background p-5"><p className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink-muted">Selected source</p><p className="mt-2 text-sm font-semibold">{selectedSource.title}</p><p className="mt-2 text-xs leading-5 text-ink-muted">{selectedSource.excerpt}</p><a href={selectedSource.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex text-xs font-semibold text-accent hover:underline">Open official source ↗</a></div>}
              {activeResponse && <div className="border-t border-border p-5"><div className="flex flex-wrap gap-2"><Badge>{activeResponse.output_translation.machine_translated ? "Machine translated · IndicTrans2" : `Output · ${activeResponse.output_translation.status}`}</Badge><Badge>{activeResponse.response_language}</Badge></div>{activeResponse.output_translation.machine_translated && activeResponse.authoritative_answer !== activeResponse.answer && <details className="mt-4 rounded-xl border border-border bg-surface p-3"><summary className="cursor-pointer text-xs font-semibold text-accent">View authoritative English answer</summary><p className="mt-3 text-xs leading-5 text-ink-muted">{activeResponse.authoritative_answer}</p></details>}<p className="mt-4 text-xs leading-5 text-ink-muted">{activeResponse.limitations[0]}</p></div>}
            </aside>
          </section>
        </>
      )}
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full border border-border bg-surface px-2.5 py-1 font-mono text-[9px] uppercase text-ink-muted">{children}</span>;
}

function LanguageSelect({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="grid gap-1 text-[10px] font-medium uppercase tracking-[0.08em] text-ink-muted">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="min-w-32 rounded-lg border border-border bg-surface px-2 py-1.5 text-xs font-normal normal-case tracking-normal text-ink">{languages.map((language) => <option key={language}>{language}</option>)}</select></label>;
}
