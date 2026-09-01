"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getCurrentUser, login } from "@/lib/api";

function destination() {
  const value = new URLSearchParams(window.location.search).get("next");
  return value?.startsWith("/") && !value.startsWith("//") ? value : "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    void getCurrentUser().then((user) => {
      if (user) router.replace(destination());
    });
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim().toLowerCase(), password);
      router.replace(destination());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-6 py-10 text-ink md:py-16">
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border bg-surface shadow-sm lg:grid-cols-[0.9fr_1.1fr]">
        <section className="hidden bg-[#16212B] p-10 text-white lg:flex lg:flex-col">
          <Link href="/" className="inline-flex items-baseline text-2xl font-semibold tracking-tight">
            IP-SAKTI <span className="ml-1 text-[#9BD0C0]">360</span>
          </Link>
          <div className="my-auto py-16">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#9BD0C0]">Controlled workspace</p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">Return to your innovation intelligence.</h2>
            <p className="mt-5 text-sm leading-7 text-white/60">Your cases, evidence lineage and advisory outputs remain separated by authenticated analyst account.</p>
          </div>
          <p className="text-xs leading-5 text-white/45">Legal, scientific and regulatory decision support—not a substitute for qualified professional review.</p>
        </section>

        <section className="p-7 md:p-12">
          <div className="flex items-center justify-between gap-4 lg:hidden">
            <Link href="/" className="inline-flex items-baseline text-xl font-semibold tracking-tight">IP-SAKTI <span className="ml-1 text-accent">360</span></Link>
            <Link href="/" className="text-xs font-semibold text-accent">Home</Link>
          </div>
          <p className="mt-10 font-mono text-[10px] uppercase tracking-[0.18em] text-accent lg:mt-0">Secure sign in</p>
          <h1 className="mt-2 text-3xl font-semibold">Sign in to your cases</h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">Enter the account details used when your workspace was created.</p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            <label className="grid gap-2 text-sm font-medium">Email address<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10" /></label>
            <label className="grid gap-2 text-sm font-medium">Password<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10" /></label>
            {error && <p role="alert" className="rounded-xl bg-danger-subtle p-3 text-sm text-danger">{error}</p>}
            <button disabled={submitting} className="w-full rounded-xl bg-accent px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50">{submitting ? "Signing in…" : "Sign in →"}</button>
          </form>

          <p className="mt-7 text-center text-sm text-ink-muted">New to IP-SAKTI? <Link href="/signup" className="font-semibold text-accent hover:underline">Create an account</Link></p>
          <p className="mt-8 border-t border-border pt-5 text-xs leading-5 text-ink-muted">Access is logged. Do not upload confidential material unless your deployment has an approved retention and data-processing policy.</p>
        </section>
      </div>
    </main>
  );
}
