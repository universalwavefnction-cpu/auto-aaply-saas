import {
  Sparkles,
  UserCircle,
  FileText,
  KeyRound,
  Rocket,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react'
import type { OnboardingStep } from './useOnboardingTour'

interface OnboardingSidebarProps {
  step: OnboardingStep
  completed: Set<OnboardingStep>
  onGoTo: (step: OnboardingStep) => void
  onSkip: () => void
}

const navItems: { step: OnboardingStep; icon: typeof Sparkles; label: string }[] = [
  { step: 0, icon: Sparkles, label: 'Welcome' },
  { step: 1, icon: UserCircle, label: 'Profile' },
  { step: 2, icon: FileText, label: 'Upload CV' },
  { step: 3, icon: KeyRound, label: 'Credentials' },
  { step: 4, icon: Rocket, label: 'Launch' },
]

export default function OnboardingSidebar({ step, completed, onGoTo, onSkip }: OnboardingSidebarProps) {
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
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500"></div>
          <span className="text-[9px] font-bold uppercase tracking-widest text-emerald-400">
            Account Setup
          </span>
        </div>
      </div>

      {/* Nav Items */}
      <div className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive = item.step === step
          const isComplete = completed.has(item.step)
          return (
            <button
              key={item.step}
              onClick={() => onGoTo(item.step)}
              className={`group relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-bold uppercase tracking-[0.1em] transition-all duration-200 ${
                isActive
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.05)]'
                  : isComplete
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
              {isComplete && !isActive && (
                <CheckCircle2 className="ml-auto h-3.5 w-3.5 text-emerald-500" />
              )}
            </button>
          )
        })}
      </div>

      {/* Progress */}
      <div className="border-t border-white/5 p-6">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/20">Progress</span>
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
            {completed.size}/4
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
          <div
            className="h-full rounded-full bg-amber-500 transition-all duration-500 ease-out"
            style={{ width: `${(completed.size / 4) * 100}%` }}
          />
        </div>
      </div>

      {/* Skip CTA */}
      <div className="border-t border-white/5 p-4">
        <button
          onClick={onSkip}
          className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl border border-white/10 py-3.5 text-xs font-black uppercase tracking-wider text-white/40 transition-all hover:border-white/20 hover:text-white/60"
        >
          <span className="relative">Skip to Dashboard</span>
          <ArrowRight className="relative h-4 w-4" />
        </button>
      </div>
    </nav>
  )
}
