"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-background px-6 py-12 text-ink">
      <section className="w-full max-w-md rounded-3xl border border-border bg-surface p-8 shadow-sm">
        <Link href="/" className="inline-flex items-baseline text-2xl font-semibold tracking-tight">
          IP-SAKTI <span className="ml-1 text-accent">360</span>
        </Link>
        <p className="mt-8 font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Secure workspace</p>
        <h1 className="mt-2 text-3xl font-semibold">Sign in to your cases</h1>
        <p className="mt-3 text-sm leading-6 text-ink-muted">Use the analyst account provided by your organisation administrator.</p>
        <form onSubmit={submit} className="mt-7 space-y-4">
          <label className="grid gap-2 text-sm font-medium">Email<input required type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none focus:border-accent" /></label>
          <label className="grid gap-2 text-sm font-medium">Password<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none focus:border-accent" /></label>
          {error && <p role="alert" className="rounded-xl bg-danger-subtle p-3 text-sm text-danger">{error}</p>}
          <button disabled={submitting} className="w-full rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">{submitting ? "Signing in…" : "Sign in →"}</button>
        </form>
        <p className="mt-6 text-xs leading-5 text-ink-muted">Access is logged. Do not upload confidential material unless your deployment has an approved retention and data-processing policy.</p>
      </section>
    </main>
  );
}
