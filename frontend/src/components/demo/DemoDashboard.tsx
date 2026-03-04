import { useState, useEffect, useRef } from 'react'
import {
  Rocket,
  Activity,
  CheckCircle2,
  MessageSquare,
  Briefcase,
  MapPin,
  Globe,
  SlidersHorizontal,
  FileText,
} from 'lucide-react'
import {
  DEMO_STATS,
  DEMO_PLATFORM_DATA,
  DEMO_STATUS_DATA,
  DEMO_AUDIT_LOG,
} from './demoData'

function useCountUp(target: number, duration = 1500) {
  const [value, setValue] = useState(0)
  const ref = useRef<number>(0)

  useEffect(() => {
    const start = performance.now()
    const animate = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(eased * target))
      if (progress < 1) {
        ref.current = requestAnimationFrame(animate)
      }
    }
    ref.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(ref.current)
  }, [target, duration])

  return value
}

export default function DemoDashboard() {
  const apps = useCountUp(DEMO_STATS.total_applications)
  const rate = useCountUp(DEMO_STATS.success_rate)
  const responses = useCountUp(DEMO_STATS.responses)
  const [visibleLogs, setVisibleLogs] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleLogs((v) => {
        if (v >= DEMO_AUDIT_LOG.length) {
          clearInterval(timer)
          return v
        }
        return v + 1
      })
    }, 300)
    return () => clearInterval(timer)
  }, [])

  const statCards = [
    {
      label: 'Live Applications',
      val: apps.toLocaleString(),
      accent: 'text-amber-500',
      icon: Activity,
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
    },
    {
      label: 'Success Rate',
      val: `${rate}%`,
      accent: 'text-emerald-400',
      icon: CheckCircle2,
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
    },
    {
      label: 'Responses',
      val: responses.toString(),
      accent: 'text-purple-400',
      icon: MessageSquare,
      bg: 'bg-purple-500/10',
      border: 'border-purple-500/20',
    },
  ]

  const platformColors: Record<string, string> = {
    stepstone: 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
    xing: 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]',
    linkedin: 'bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.5)]',
  }

  const statusColors: Record<string, string> = {
    success: 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]',
    pending: 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
    failed: 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]',
    skipped: 'bg-white/20',
  }

  return (
    <div className="space-y-6 sm:space-y-8 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Activity className="h-5 w-5 text-amber-500" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white truncate">
              Mission Control
            </h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              System Overview
            </p>
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-2 sm:px-3 py-1.5 backdrop-blur-sm">
          <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
          <span className="hidden sm:inline text-[9px] font-bold uppercase tracking-widest text-emerald-500">
            System Active
          </span>
        </div>
      </div>

      {/* Quick Launch */}
      <div className="demo-hotspot relative overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] p-4 sm:p-6 md:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 p-32 bg-amber-500/5 blur-[100px] rounded-full pointer-events-none"></div>
        <div className="relative z-10">
          <div className="mb-8 flex items-center gap-3">
            <div className="rounded-lg bg-amber-500/20 p-1.5">
              <Rocket className="h-5 w-5 text-amber-500" />
            </div>
            <span className="text-xs font-black uppercase tracking-[0.2em] text-amber-500">
              Quick Launch
            </span>
          </div>

          <div className="grid gap-6 md:grid-cols-12">
            <div className="md:col-span-5">
              <label className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <Briefcase className="h-3 w-3" /> Target Position
              </label>
              <div className="w-full rounded-xl border border-amber-500/30 bg-black/50 px-5 py-4 text-base text-white">
                Frontend Engineer
              </div>
            </div>

            <div className="md:col-span-3">
              <label className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <MapPin className="h-3 w-3" /> Location
              </label>
              <div className="w-full rounded-xl border border-white/10 bg-black/50 px-5 py-4 text-base text-white">
                Berlin
              </div>
            </div>

            <div className="md:col-span-4">
              <label className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <Globe className="h-3 w-3" /> Platform
              </label>
              <div className="flex h-[58px] gap-1.5 rounded-xl border border-white/10 bg-black/50 p-1.5">
                {(['SS', 'XI', 'IN', 'LI'] as const).map((p, i) => (
                  <div
                    key={p}
                    className={`flex flex-1 items-center justify-center rounded-lg text-[10px] font-bold uppercase tracking-wider ${
                      i === 0
                        ? 'bg-amber-500 text-black shadow-md'
                        : 'text-white/40'
                    }`}
                  >
                    {p}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-col sm:flex-row sm:flex-wrap sm:items-end sm:justify-between gap-4 sm:gap-6 border-t border-white/5 pt-6">
            <div className="flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-4 sm:gap-8">
              <div className="flex items-center gap-4 w-full sm:w-auto">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                  <SlidersHorizontal className="h-3 w-3" /> Volume
                </div>
                <div className="h-1.5 flex-1 sm:w-32 sm:flex-none rounded-full bg-white/10">
                  <div className="h-full w-1/5 rounded-full bg-amber-500" />
                </div>
                <span className="w-12 text-right text-lg font-black tabular-nums text-amber-500">
                  100
                </span>
              </div>
              <div className="flex items-center gap-4 w-full sm:w-auto">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40 shrink-0">
                  <FileText className="h-3 w-3" /> Resume
                </div>
                <span className="text-sm text-white/80">resume_max.pdf</span>
              </div>
            </div>

            <div className="group relative w-full sm:w-auto overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.3)] text-center">
              <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-12deg)_translateX(-100%)] group-hover:duration-1000 group-hover:[transform:skew(-12deg)_translateX(100%)]">
                <div className="relative h-full w-8 bg-white/20" />
              </div>
              <span className="relative flex items-center justify-center gap-2">
                Launch Sequence
                <Rocket className="h-4 w-4" />
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {statCards.map((stat, i) => (
          <div
            key={i}
            className="stat-card group relative overflow-hidden rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 fadeIn"
            style={{ animationDelay: `${i * 150}ms`, opacity: 0 }}
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                {stat.label}
              </span>
              <div className={`stat-icon-bg rounded-lg p-2 ${stat.bg} ${stat.border} border`}>
                <stat.icon className={`h-4 w-4 ${stat.accent}`} />
              </div>
            </div>
            <p className={`text-4xl font-black tracking-tighter ${stat.accent}`}>
              {stat.val}
            </p>
          </div>
        ))}
      </div>

      {/* Breakdown & Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          {/* Platform Distribution */}
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6">
            <span className="mb-6 block text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Platform Distribution
            </span>
            <div className="space-y-5">
              {DEMO_PLATFORM_DATA.map(([name, count]) => {
                const max = Math.max(...DEMO_PLATFORM_DATA.map(([, v]) => v))
                const pct = (count / max) * 100
                return (
                  <div key={name} className="space-y-2 group">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-white/60">
                        {name}
                      </span>
                      <span className="text-[11px] font-black tabular-nums text-white">
                        {count}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                      <div
                        className={`h-full rounded-full transition-all duration-[2000ms] ease-out ${platformColors[name] || 'bg-white/20'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Status Breakdown */}
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6">
            <span className="mb-6 block text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Status Breakdown
            </span>
            <div className="space-y-5">
              {DEMO_STATUS_DATA.map(([name, count]) => {
                const max = Math.max(...DEMO_STATUS_DATA.map(([, v]) => v))
                const pct = (count / max) * 100
                return (
                  <div key={name} className="space-y-2 group">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-white/60">
                        {name}
                      </span>
                      <span className="text-[11px] font-black tabular-nums text-white">
                        {count}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                      <div
                        className={`h-full rounded-full transition-all duration-[2000ms] ease-out ${statusColors[name] || 'bg-white/20'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Audit Log */}
        <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 lg:col-span-2 flex flex-col">
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-4 w-4 text-amber-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Audit Log
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-1.5 border border-amber-500/20">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"></div>
              <span className="text-[9px] font-black uppercase tracking-widest text-amber-500">
                Live Feed
              </span>
            </div>
          </div>

          <div className="flex-1 space-y-2 font-mono text-xs overflow-y-auto pr-2 custom-scrollbar">
            {DEMO_AUDIT_LOG.slice(0, visibleLogs).map((a, i) => (
              <div
                key={a.id}
                className="group flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 rounded-xl border border-white/5 bg-black/50 p-3 fadeIn"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div className="flex items-center gap-4 sm:w-32 shrink-0">
                  <span className="tabular-nums text-white/30 text-[10px]">{a.time}</span>
                  <span
                    className={`rounded-md border px-2 py-1 text-center text-[9px] font-black uppercase tracking-wider ${
                      a.status === 'success'
                        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                        : a.status === 'failed'
                          ? 'border-red-500/20 bg-red-500/10 text-red-400'
                          : 'border-amber-500/20 bg-amber-500/10 text-amber-500'
                    }`}
                  >
                    {a.status}
                  </span>
                </div>
                <div className="flex-1 min-w-0 flex flex-col">
                  <span className="truncate font-sans font-bold text-white/80">{a.title}</span>
                  <span className="truncate font-sans text-[10px] text-white/40">{a.company}</span>
                </div>
                <div className="shrink-0 self-start sm:self-center">
                  <span className="rounded-lg bg-white/5 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-white/30">
                    {a.platform}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
