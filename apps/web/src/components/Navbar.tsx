"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search" },
  { href: "/stats", label: "Dashboard" },
];

const ADMIN_ITEMS = [
  { href: "/admin/channels", label: "Channels" },
  { href: "/admin/agents", label: "Agents" },
  { href: "/admin/discover", label: "Discover" },
  { href: "/admin/pipeline", label: "Pipeline" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [adminOpen, setAdminOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-sand-200 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-aqar-500 text-white font-bold text-lg">
            ع
          </div>
          <span className="text-xl font-semibold tracking-tight text-sand-900">
            Aqar<span className="text-aqar-500">.ai</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href}
                className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${isActive ? "bg-aqar-50 text-aqar-700" : "text-sand-500 hover:bg-sand-50 hover:text-sand-800"}`}>
                {item.label}
              </Link>
            );
          })}

          {/* Admin dropdown */}
          <div className="relative">
            <button onClick={() => setAdminOpen(!adminOpen)}
              className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${pathname.startsWith("/admin") ? "bg-aqar-50 text-aqar-700" : "text-sand-500 hover:bg-sand-50 hover:text-sand-800"}`}>
              Admin ▾
            </button>
            {adminOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setAdminOpen(false)} />
                <div className="absolute right-0 z-50 mt-1 w-44 rounded-xl border border-sand-200 bg-white py-1 shadow-lg">
                  {ADMIN_ITEMS.map((item) => (
                    <Link key={item.href} href={item.href} onClick={() => setAdminOpen(false)}
                      className="block px-4 py-2 text-sm text-sand-700 hover:bg-sand-50">
                      {item.label}
                    </Link>
                  ))}
                </div>
              </>
            )}
          </div>

          <Link href="/agent/register"
            className="ml-2 rounded-lg bg-aqar-500 px-3.5 py-2 text-sm font-medium text-white hover:bg-aqar-600 transition-colors">
            List Property
          </Link>
        </div>
      </div>
    </nav>
  );
}
