import React from 'react'
import { Sparkles, TrendingUp, Lock } from 'lucide-react'

const HIGHLIGHTS = [
  {
    icon: <TrendingUp size={16} />,
    title: 'Live service analytics',
    desc: 'Revenue, covers and prep times as they happen.',
  },
  {
    icon: <Sparkles size={16} />,
    title: 'AI recommendations',
    desc: 'Autonomous insights tuned to tonight’s service.',
  },
  {
    icon: <Lock size={16} />,
    title: 'Multi-tenant & secure',
    desc: 'Role-based access with isolated restaurant data.',
  },
]

/**
 * Shared two-column shell for the login and register pages. The left brand
 * panel is decorative and hidden below `lg` so it never affects the mobile
 * form layout; the right panel centers the form and shows a compact logo on
 * small screens.
 */
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-full w-full lg:grid lg:grid-cols-2">
      {/* Brand panel — desktop only */}
      <aside className="relative hidden overflow-hidden border-r border-line bg-surface lg:flex lg:flex-col lg:justify-between lg:p-12">
        {/* Perforated ticket rail */}
        <div className="pointer-events-none absolute inset-y-0 left-0 w-[3px] bg-[repeating-linear-gradient(to_bottom,var(--accent)_0_8px,transparent_8px_16px)] opacity-40" />
        {/* Ambient glow */}
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-accent/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 left-1/3 h-72 w-72 rounded-full bg-accent/5 blur-3xl" />

        <div className="relative">
          <span className="font-display text-2xl font-bold tracking-wide text-foreground">
            Ops<span className="text-accent">Mind</span>
          </span>
          <p className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-cream-dim">
            Kitchen Intelligence
          </p>
        </div>

        <div className="relative max-w-sm">
          <h2 className="font-display text-4xl font-bold leading-tight text-foreground">
            Run tonight’s service from a single pass.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-cream-dim">
            Real-time operations intelligence for modern restaurants — sales,
            menu and staffing signals in one calm view.
          </p>
          <ul className="mt-8 space-y-4">
            {HIGHLIGHTS.map((h) => (
              <li key={h.title} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-[3px] border border-accent/25 bg-accent/10 text-accent">
                  {h.icon}
                </span>
                <div>
                  <p className="font-display text-sm font-semibold tracking-wide text-foreground">
                    {h.title}
                  </p>
                  <p className="text-xs leading-relaxed text-cream-dim">{h.desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-cream-dim/70">
          OpsMind AI © 2026 · Restaurant Operations Intelligence
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex min-h-full flex-col items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:hidden">
            <span className="font-display text-2xl font-bold tracking-wide text-foreground">
              Ops<span className="text-accent">Mind</span>
            </span>
            <p className="mt-1 text-[11px] font-medium uppercase tracking-[0.18em] text-cream-dim">
              Kitchen Intelligence
            </p>
          </div>
          {children}
        </div>
      </main>
    </div>
  )
}
