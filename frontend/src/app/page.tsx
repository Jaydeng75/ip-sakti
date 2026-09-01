"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";

export default function Home() {
  const [description, setDescription] = useState("");
  const router = useRouter();

  function analyze() {
    if (description.trim()) {
      window.sessionStorage.setItem("ip-sakti-analysis-draft", description.trim());
    }
    router.push("/analyze");
  }

  return (
    <main className="min-h-screen bg-background text-ink">
      <Sidebar />

      {/* NAVBAR */}
      <header className="flex items-center justify-between py-6 pl-20 pr-7 md:pl-24 md:pr-20">
        <Link
          href="/"
          className="group inline-flex items-baseline tracking-[-0.04em] transition-opacity duration-200 hover:opacity-75"
          aria-label="Go to IP-SAKTI home"
        >
          <span className="text-2xl font-semibold">
            IP-SAKTI
          </span>

          <span className="ml-1 text-3xl font-bold text-accent transition-transform duration-200 group-hover:translate-x-0.5">
            360
          </span>
        </Link>

        <nav className="hidden items-center gap-10 text-sm text-ink-muted md:flex">
          <span>How it works</span>
          <span>Evidence</span>
          <span>About</span>
        </nav>

        <div className="font-mono text-xs text-ink-muted">
          INDIA · 01
        </div>
      </header>

      {/* HERO */}
      <section className="mx-auto max-w-7xl px-7 pb-24 pt-24 md:px-12 md:pt-32">
        <div className="max-w-5xl">
          <p className="mb-7 text-base font-medium uppercase tracking-[0.18em] text-accent">
            IP intelligence for Ayurvedic innovation
          </p>

          <h1 className="max-w-5xl text-6xl font-medium leading-[0.95] tracking-[-0.04em] md:text-8xl lg:text-[7rem]">
            What are you
            <br />
            actually building?
          </h1>

          <p className="mt-9 max-w-3xl text-xl leading-8 text-ink-muted md:text-2xl md:leading-9">
            Tell us about your product. We&apos;ll help you understand what&apos;s
            already known, what&apos;s new, and what you need to check before
            taking it further.
          </p>
        </div>

        {/* INNOVATION INPUT */}
        <div className="mt-16 max-w-6xl overflow-hidden rounded-3xl border border-border bg-surface shadow-sm">
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="min-h-52 w-full resize-none bg-transparent p-7 text-xl outline-none placeholder:text-ink-muted/40 md:p-9 md:text-2xl"
            placeholder="Tell us about your product..."
          />

          <div className="flex flex-col gap-5 border-t border-border p-5 md:flex-row md:items-center md:justify-between md:p-6">
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-accent-subtle px-4 py-2 text-sm text-accent">
                India
              </span>

              <span className="rounded-full border border-border px-4 py-2 text-sm text-ink-muted">
                Ayurvedic product
              </span>

              <span className="rounded-full border border-border px-4 py-2 text-sm text-ink-muted">
                English
              </span>
            </div>

            <Button
              onClick={analyze}
              className="h-12 rounded-xl bg-accent px-7 text-base text-white hover:bg-accent/90"
            >
              Explore my idea →
            </Button>
          </div>
        </div>

        {/* THREE QUESTIONS */}
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          <Question
            number="01"
            title="Has this been done before?"
            text="Find traditional knowledge, existing products and earlier inventions."
          />

          <Question
            number="02"
            title="What could be new?"
            text="See which parts of your idea may actually be different."
          />

          <Question
            number="03"
            title="What could get in the way?"
            text="Understand patents, regulations, evidence and other checks."
          />
        </div>

        {/* PREVIEW */}
        <section className="mt-32">
          <div className="mb-8">
            <p className="font-mono text-sm uppercase tracking-[0.2em] text-accent">
              A glimpse of what&apos;s possible
            </p>

            <h2 className="mt-3 max-w-3xl font-display text-5xl font-medium leading-[0.95] tracking-tight md:text-7xl">
              See your idea{" "}
              <span className="text-accent">from every angle.</span>
            </h2>
          </div>

          <div className="grid overflow-hidden rounded-3xl border border-border bg-[#16212B] text-white md:grid-cols-4">
            <Preview
              value="08"
              title="Things already known"
            />

            <Preview
              value="14"
              title="Scientific sources"
            />

            <Preview
              value="06"
              title="Possible IP routes"
            />

            <Preview
              value="Review"
              title="ABS check"
            />
          </div>
        </section>
      </section>
    </main>
  );
}

function Question({
  number,
  title,
  text,
}: {
  number: string;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-7 md:p-8">
      <div className="flex items-start justify-between">
        <span className="font-mono text-xs text-ink-muted">{number}</span>

        <span className="text-xl text-accent">↗</span>
      </div>

      <h3 className="mt-12 text-xl font-medium tracking-tight md:text-2xl">
        {title}
      </h3>

      <p className="mt-3 text-base leading-7 text-ink-muted">
        {text}
      </p>
    </div>
  );
}

function Preview({
  value,
  title,
}: {
  value: string;
  title: string;
}) {
  return (
    <div className="border-b border-white/10 p-7 last:border-b-0 md:border-b-0 md:border-r md:p-9">
      <p className="font-mono text-xs text-white/50">
        FOUND
      </p>

      <p className="mt-8 text-4xl font-medium tracking-tight md:text-5xl">
        {value}
      </p>

      <p className="mt-3 text-base text-white/70">
        {title}
      </p>
    </div>
  );
}
