import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  UserCircle,
  FileText,
  KeyRound,
  Rocket,
} from 'lucide-react'
import { useOnboardingTour } from './useOnboardingTour'
import type { OnboardingStep } from './useOnboardingTour'
import { ONBOARDING_STEPS } from './onboardingData'
import OnboardingSidebar from './OnboardingSidebar'
import StepWelcome from './steps/StepWelcome'
import StepProfile from './steps/StepProfile'
import StepCvUpload from './steps/StepCvUpload'
import StepCredentials from './steps/StepCredentials'
import StepLaunch from './steps/StepLaunch'

const stepIcons = [Sparkles, UserCircle, FileText, KeyRound, Rocket]

function TourOverlay({
  step,
  total,
  onNext,
  onBack,
  onSkip,
  isFirst,
  canProceed,
}: {
  step: OnboardingStep
  total: number
  onNext: () => void
  onBack: () => void
  onSkip: () => void
  isFirst: boolean
  canProceed: boolean
}) {
  const info = ONBOARDING_STEPS[step]
  if (step === 4) return null // Launch step has its own CTA

  const Icon = stepIcons[step]

  return (
    <>
      {/* Mobile: compact card at top, below header */}
      <div className="fixed top-[53px] left-0 right-0 z-50 md:hidden px-3 pt-2">
        <div className="rounded-xl border border-white/10 bg-[#0A0A0A]/95 backdrop-blur-xl px-3.5 py-3 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
              <Icon className="h-3.5 w-3.5 text-amber-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[8px] font-black uppercase tracking-[0.2em] text-amber-500">
                {step + 1}/{total}
              </p>
              <p className="text-xs font-bold text-white truncate">{info.title}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {!isFirst && (
                <button
                  onClick={onBack}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-white/40"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                onClick={onNext}
                disabled={!canProceed}
                className="flex items-center gap-1 rounded-lg bg-amber-500 px-3.5 py-1.5 text-[9px] font-black uppercase tracking-wider text-black disabled:opacity-30"
              >
                Next
                <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <p className="flex-1 text-[10px] leading-snug text-white/40 line-clamp-2">
              {info.description}
            </p>
            <div className="flex items-center gap-1.5 shrink-0">
              {Array.from({ length: total }).map((_, i) => (
                <div
                  key={i}
                  className={`rounded-full transition-all duration-300 ${
                    i === step
                      ? 'h-2 w-2 bg-amber-500'
                      : i < step
                        ? 'h-1.5 w-1.5 bg-amber-500/50'
                        : 'h-1.5 w-1.5 bg-white/15'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Desktop: full card at bottom center */}
      <div className="hidden md:block fixed bottom-8 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4">
        <div className="rounded-2xl border border-white/10 bg-[#0A0A0A]/95 backdrop-blur-xl p-6 shadow-[0_0_40px_rgba(0,0,0,0.5)]">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
              <Icon className="h-4 w-4 text-amber-500" />
            </div>
            <div>
              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
                Step {step + 1} of {total}
              </p>
              <p className="text-sm font-bold text-white">{info.title}</p>
            </div>
          </div>

          <p className="text-xs leading-relaxed text-white/50 mb-5">{info.description}</p>

          <div className="flex items-center justify-between">
            <button
              onClick={onBack}
              disabled={isFirst}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-[10px] font-bold uppercase tracking-wider transition-all ${
                isFirst
                  ? 'text-white/10 cursor-not-allowed'
                  : 'text-white/50 hover:text-white hover:bg-white/5'
              }`}
            >
              <ArrowLeft className="h-3 w-3" />
              Back
            </button>

            <div className="flex items-center gap-2">
              {Array.from({ length: total }).map((_, i) => (
                <div
                  key={i}
                  className={`rounded-full transition-all duration-300 ${
                    i === step
                      ? 'h-2.5 w-2.5 bg-amber-500 ring-4 ring-amber-500/20'
                      : i < step
                        ? 'h-2 w-2 bg-amber-500/60'
                        : 'h-2 w-2 bg-white/20'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={onNext}
              disabled={!canProceed}
              className="group flex items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-2 text-[10px] font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
              <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>

          <div className="mt-3 text-center">
            <button
              onClick={onSkip}
              className="text-[10px] font-bold uppercase tracking-wider text-white/25 transition-colors hover:text-amber-500"
            >
              Skip setup — go to Dashboard
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

export default function OnboardingTour() {
  const navigate = useNavigate()
  const { step, direction, next, back, goTo, isFirst, total, completed, markCompleted } = useOnboardingTour()

  const handleSkip = () => {
    localStorage.setItem('onboarding_complete', '1')
    navigate('/dashboard')
  }

  const handleNext = () => {
    if (step === 4) {
      // Launch step handles its own navigation
      return
    }
    next()
  }

  // Can proceed: step 0 always, steps 1-3 need completion, step 4 handled internally
  const canProceed = step === 0 || completed.has(step)

  const stepComponents = [
    <StepWelcome key="welcome" onNext={next} />,
    <StepProfile key="profile" onComplete={() => markCompleted(1)} />,
    <StepCvUpload key="cv" onComplete={() => markCompleted(2)} />,
    <StepCredentials key="credentials" onComplete={() => markCompleted(3)} />,
    <StepLaunch key="launch" />,
  ]

  return (
    <div className="flex h-screen bg-[#050505] font-sans text-white overflow-hidden selection:bg-amber-500/30">
      {/* Desktop Sidebar */}
      <OnboardingSidebar step={step} completed={completed} onGoTo={goTo} onSkip={handleSkip} />

      {/* Mobile Header */}
      <div className="fixed top-0 left-0 right-0 z-40 flex md:hidden items-center justify-between border-b border-white/5 bg-[#080808]/95 backdrop-blur-xl px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          </div>
          <span className="text-sm font-bold tracking-tight">AutoApply</span>
          <span className="rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-0.5 text-[8px] font-bold uppercase tracking-widest text-emerald-400">
            Setup
          </span>
        </div>
        <button
          onClick={handleSkip}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-[10px] font-black uppercase tracking-wider text-white/40"
        >
          Skip
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>

      {/* Main content */}
      <main className={`flex-1 overflow-auto bg-[#050505] relative custom-scrollbar md:pt-0 pb-[68px] md:pb-[120px] ${step === 4 ? 'pt-[53px]' : 'pt-[140px]'}`}>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-500/5 via-[#050505] to-[#050505] pointer-events-none"></div>

        <div
          key={step}
          className={`relative z-10 h-full ${direction === 'forward' ? 'demo-slide-right' : 'demo-slide-left'}`}
        >
          {stepComponents[step]}
        </div>
      </main>

      {/* Tour Overlay */}
      <TourOverlay
        step={step}
        total={total}
        onNext={handleNext}
        onBack={back}
        onSkip={handleSkip}
        isFirst={isFirst}
        canProceed={canProceed}
      />

      {/* Mobile Bottom Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-30 flex md:hidden border-t border-white/5 bg-[#080808]/95 backdrop-blur-xl">
        {([
          { s: 0 as OnboardingStep, icon: Sparkles, label: 'Welcome' },
          { s: 1 as OnboardingStep, icon: UserCircle, label: 'Profile' },
          { s: 2 as OnboardingStep, icon: FileText, label: 'CV' },
          { s: 3 as OnboardingStep, icon: KeyRound, label: 'Creds' },
          { s: 4 as OnboardingStep, icon: Rocket, label: 'Launch' },
        ]).map(({ s, icon: Icon, label }) => {
          const isActive = s === step
          return (
            <button
              key={s}
              onClick={() => goTo(s)}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 transition-colors ${
                isActive ? 'text-amber-500' : 'text-white/30'
              }`}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'scale-110' : ''} transition-transform`} />
              <span className="text-[9px] font-bold uppercase tracking-wider">{label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
