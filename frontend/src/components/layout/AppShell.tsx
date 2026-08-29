import Link from "next/link";
import CaseHeader from "@/components/layout/CaseHeader";
import Sidebar from "@/components/layout/Sidebar";

export default function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background text-ink">
      <Sidebar />

      {/* PERSISTENT APP HEADER */}
      <header className="fixed left-0 right-0 top-0 z-30 h-20 border-b border-border/70 bg-[#F7F8F6]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-6 md:px-10">
          {/* HOME / BRAND */}
          <Link
            href="/"
            className="group ml-16 inline-flex items-baseline tracking-[-0.04em] transition-opacity duration-200 hover:opacity-75 md:ml-14"
            aria-label="Go to IP-SAKTI home"
          >
            <span className="text-xl font-semibold md:text-2xl">
              IP-SAKTI
            </span>

            <span className="ml-1 text-2xl font-bold text-accent transition-transform duration-200 group-hover:translate-x-0.5 md:text-3xl">
              360
            </span>
          </Link>

          {/* LOCATION */}
          <div className="font-mono text-[10px] tracking-[0.12em] text-ink-muted md:text-xs">
            INDIA <span className="mx-1">·</span> 01
          </div>
        </div>
      </header>

      {/* PAGE */}
      <main className="min-w-0 pt-24">
        <div className="mx-auto max-w-7xl px-6 pb-10 md:px-10 md:pt-4">
          <CaseHeader />
          {children}
        </div>
      </main>
    </div>
  );
}