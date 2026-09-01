"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getCurrentUser, signup } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    void getCurrentUser().then((user) => {
      if (user) router.replace("/dashboard");
    });
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      await signup(displayName.trim(), email.trim().toLowerCase(), password);
      router.replace("/analyze");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Account creation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-6 py-10 text-ink md:py-16">
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border bg-surface shadow-sm lg:grid-cols-[0.9fr_1.1fr]">
        <section className="hidden bg-[#16212B] p-10 text-white lg:flex lg:flex-col">
          <Link href="/" className="inline-flex items-baseline text-2xl font-semibold tracking-tight">IP-SAKTI <span className="ml-1 text-[#9BD0C0]">360</span></Link>
          <div className="my-auto py-16">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#9BD0C0]">Create a workspace</p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">Take an innovation from idea to evidence.</h2>
            <div className="mt-7 space-y-4 text-sm text-white/65"><p>✓ Private, account-separated innovation cases</p><p>✓ Evidence-grounded scientific and IP analysis</p><p>✓ Explainable recommendations and human-review flags</p></div>
          </div>
          <p className="text-xs leading-5 text-white/45">Use a strong, unique password. Uploaded information may be sensitive.</p>
        </section>

        <section className="p-7 md:p-12">
          <div className="flex items-center justify-between gap-4 lg:hidden">
            <Link href="/" className="inline-flex items-baseline text-xl font-semibold tracking-tight">IP-SAKTI <span className="ml-1 text-accent">360</span></Link>
            <Link href="/" className="text-xs font-semibold text-accent">Home</Link>
          </div>
          <p className="mt-10 font-mono text-[10px] uppercase tracking-[0.18em] text-accent lg:mt-0">Analyst registration</p>
          <h1 className="mt-2 text-3xl font-semibold">Create your account</h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">Start a separate workspace for your innovation cases and evidence.</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <label className="grid gap-2 text-sm font-medium">Full name<input required minLength={2} maxLength={120} autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10" /></label>
            <label className="grid gap-2 text-sm font-medium">Email address<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10" /></label>
            <label className="grid gap-2 text-sm font-medium">Password<input required minLength={10} maxLength={128} type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10" /><span className="text-xs font-normal text-ink-muted">Use at least 10 characters and avoid a password used elsewhere.</span></label>
            <label className="grid gap-2 text-sm font-medium">Confirm password<input required minLength={10} maxLength={128} type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="rounded-xl border border-border bg-background px-4 py-3 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/10" /></label>
            {error && <p role="alert" className="rounded-xl bg-danger-subtle p-3 text-sm text-danger">{error}</p>}
            <button disabled={submitting} className="w-full rounded-xl bg-accent px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50">{submitting ? "Creating account…" : "Create account →"}</button>
          </form>

          <p className="mt-7 text-center text-sm text-ink-muted">Already have an account? <Link href="/login" className="font-semibold text-accent hover:underline">Sign in</Link></p>
          <p className="mt-8 border-t border-border pt-5 text-xs leading-5 text-ink-muted">By continuing, you acknowledge that IP-SAKTI provides decision support and does not replace professional legal, regulatory or clinical advice.</p>
        </section>
      </div>
    </main>
  );
}
