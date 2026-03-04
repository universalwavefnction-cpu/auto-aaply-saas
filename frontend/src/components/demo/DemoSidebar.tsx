import {
  LayoutDashboard,
  UserCircle,
  Bot,
  Send,
  Sparkles,
  Activity,
  ArrowRight,
} from 'lucide-react'
import type { DemoStep } from './useDemoTour'

interface DemoSidebarProps {
  step: DemoStep
  onGoTo: (step: DemoStep) => void
  onSkip: () => void
}

const navItems: { step: DemoStep; icon: typeof LayoutDashboard; label: string }[] = [
  { step: 0, icon: LayoutDashboard, label: 'Mission Control' },
  { step: 1, icon: UserCircle, label: 'Profile' },
  { step: 2, icon: Bot, label: 'Live Bot' },
  { step: 3, icon: Send, label: 'Applications' },
]

export default function DemoSidebar({ step, onGoTo, onSkip }: DemoSidebarProps) {
  return (
    <nav className="hidden md:flex w-64 shrink-0 flex-col border-r border-white/5 bg-[#080808] z-20">
      {/* Logo */}
      <div className="border-b border-white/5 p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.15)]">
            <Sparkles className="h-4 w-4 text-amber-500" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-white">AutoApply</span>
            <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
              Intelligence
            </span>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"></div>
          <span className="text-[9px] font-bold uppercase tracking-widest text-amber-500">
            Demo Mode
          </span>
        </div>
      </div>

      {/* Nav Items */}
      <div className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive = item.step === step
          const isPast = item.step < step
          return (
            <button
              key={item.step}
              onClick={() => onGoTo(item.step)}
              className={`group relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-bold uppercase tracking-[0.1em] transition-all duration-200 ${
                isActive
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.05)]'
                  : isPast
                    ? 'text-white/50 border border-transparent hover:bg-white/5'
                    : 'text-white/25 border border-transparent hover:bg-white/5 hover:text-white/40'
              }`}
            >
              <item.icon
                className={`h-4 w-4 transition-transform duration-200 ${
                  isActive ? 'scale-110' : 'group-hover:scale-110'
                }`}
              />
              <span>{item.label}</span>
              {isPast && (
                <div className="ml-auto h-1.5 w-1.5 rounded-full bg-emerald-500"></div>
              )}
            </button>
          )
        })}
      </div>

      {/* Platform status */}
      <div className="space-y-3 border-t border-white/5 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-3 w-3 text-white/20" />
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/20">
            Neural Targets
          </span>
        </div>
        <div className="flex flex-col gap-2">
          {[
            { name: 'StepStone', active: true },
            { name: 'Xing', active: false },
            { name: 'LinkedIn', active: true },
          ].map((platform) => (
            <div
              key={platform.name}
              className={`flex items-center justify-between rounded-lg border px-3 py-2 ${
                platform.active
                  ? 'border-amber-500/20 bg-amber-500/5'
                  : 'border-white/5 bg-white/[0.02]'
              }`}
            >
              <span
                className={`text-[9px] font-bold uppercase tracking-wider ${
                  platform.active ? 'text-amber-500' : 'text-white/40'
                }`}
              >
                {platform.name}
              </span>
              <div className="relative flex h-2 w-2 items-center justify-center">
                {platform.active && (
                  <div className="absolute h-full w-full animate-ping rounded-full bg-amber-500 opacity-20"></div>
                )}
                <div
                  className={`h-1.5 w-1.5 rounded-full ${
                    platform.active ? 'bg-amber-500' : 'bg-white/20'
                  }`}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="border-t border-white/5 p-4">
        <button
          onClick={onSkip}
          className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-amber-500 py-3.5 text-xs font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:bg-amber-400"
        >
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          <span className="relative">Sign Up — €8/mo</span>
          <ArrowRight className="relative h-4 w-4" />
        </button>
      </div>
    </nav>
  )
}
