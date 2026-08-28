"use client";

import { useState } from "react";
import Link from "next/link";

const links = [
  ["Dashboard", "/dashboard"],
  ["Analyze Innovation", "/analyze"],
  ["Ask IP-SAKTI", "/ask"],
  ["Scientific Evidence", "/evidence"],
  ["Traditional Knowledge", "/traditional-knowledge"],
  ["IP Strategy", "/ip-strategy"],
  ["Regulatory & ABS", "/regulatory"],
  ["Jurisdiction Compare", "/jurisdiction"],
  ["Saved Cases", "/saved-cases"],
  ["Reports", "/reports"],
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* MENU */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="fixed left-5 top-5 z-50 flex h-12 w-12 items-center justify-center rounded-full border border-white/60 bg-white/60 shadow-lg backdrop-blur-xl transition-all duration-300 hover:scale-105"
      >
        <div className="relative h-5 w-5">
          <span
            className={`absolute left-0 top-1/2 h-[2px] w-5 bg-[#0F6B5C] transition-all duration-300 ${
              open ? "rotate-45" : "-translate-y-2"
            }`}
          />
          <span
            className={`absolute left-0 top-1/2 h-[2px] w-5 bg-[#0F6B5C] transition-all duration-200 ${
              open ? "opacity-0" : ""
            }`}
          />
          <span
            className={`absolute left-0 top-1/2 h-[2px] w-5 bg-[#0F6B5C] transition-all duration-300 ${
              open ? "-rotate-45" : "translate-y-2"
            }`}
          />
        </div>
      </button>

      {/* BACKDROP */}
      <div
        onClick={() => setOpen(false)}
        className={`fixed inset-0 z-30 bg-[#16212B]/15 backdrop-blur-sm transition-opacity duration-500 ${
          open
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0"
        }`}
      />

      {/* SIDEBAR */}
      <aside
        className={`fixed left-0 top-0 z-40 flex h-screen w-[310px] flex-col overflow-hidden border-r border-white/70 bg-[#F3F6F2]/80 shadow-[20px_0_60px_rgba(22,33,43,0.12)] backdrop-blur-2xl transition-transform duration-500 ease-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* subtle texture */}
        <div className="pointer-events-none absolute inset-0 opacity-[0.035] [background-image:radial-gradient(#16212B_0.7px,transparent_0.7px)] [background-size:7px_7px]" />

        {/* BRAND */}
        <div className="relative px-8 pb-8 pt-24">
          <div className="text-[27px] font-semibold tracking-[-0.055em] text-[#16212B]">
            IP-SAKTI{" "}
            <span className="text-[32px] font-bold text-[#0F6B5C]">
              360
            </span>
          </div>

          <p className="mt-2 text-[11px] font-medium uppercase tracking-[0.18em] text-[#718079]">
            Ayurvedic IP Intelligence
          </p>
        </div>

        {/* NAV */}
        <nav className="relative flex-1 px-4">
          {links.map(([label, href], index) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className="group mb-1 flex items-center gap-4 rounded-2xl border border-transparent px-4 py-4 text-[15px] font-medium tracking-[-0.01em] text-[#34413B] transition-all duration-200 hover:border-white/80 hover:bg-white/55 hover:shadow-sm hover:backdrop-blur-xl"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#D5DDD7] bg-white/50 font-mono text-[11px] font-semibold text-[#46534D] transition-all duration-200 group-hover:border-[#0F6B5C]/20 group-hover:bg-[#E4F2EE] group-hover:text-[#0F6B5C]">
                {String(index + 1).padStart(2, "0")}
              </span>

              <span className="transition-transform duration-200 group-hover:translate-x-1">
                {label}
              </span>

              <span className="ml-auto text-[#A4AEA9] opacity-0 transition-all duration-200 group-hover:translate-x-0.5 group-hover:opacity-100">
                →
              </span>
            </Link>
          ))}
        </nav>

        {/* FOOTER */}
        <div className="relative border-t border-white/70 px-8 py-6">
          <p className="text-sm font-semibold tracking-tight text-[#16212B]">
            IP-SAKTI <span className="text-[#0F6B5C]">360</span>
          </p>

          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-[#7A847F]">
            Development
          </p>
        </div>
      </aside>
    </>
  );
}