"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getCurrentUser, onAuthChanged } from "@/lib/api";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  const verify = useCallback(async () => {
    const user = await getCurrentUser().catch(() => null);
    if (!user) {
      setAuthorized(false);
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setAuthorized(true);
  }, [pathname, router]);

  useEffect(() => {
    const initialCheck = window.setTimeout(() => void verify(), 0);
    const unsubscribe = onAuthChanged(() => void verify());
    return () => {
      window.clearTimeout(initialCheck);
      unsubscribe();
    };
  }, [verify]);

  if (!authorized) {
    return (
      <main className="grid min-h-screen place-items-center bg-background px-6 text-ink">
        <div className="text-center">
          <div className="mx-auto size-9 animate-spin rounded-full border-2 border-border border-t-accent" />
          <p className="mt-4 text-sm text-ink-muted">Verifying your secure workspace…</p>
        </div>
      </main>
    );
  }

  return children;
}
