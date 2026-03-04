import { Sparkles, UserCircle, FileText, KeyRound, Rocket, ArrowRight } from 'lucide-react'

const features = [
  { icon: UserCircle, title: 'Profile', desc: 'Tell us about yourself so the bot can fill forms' },
  { icon: FileText, title: 'Upload CV', desc: 'Your resume, attached to every application' },
  { icon: KeyRound, title: 'Credentials', desc: 'Connect your job platform account' },
  { icon: Rocket, title: 'Launch', desc: 'Start your first automated bot run' },
]

export default function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <div className="flex items-center justify-center min-h-full p-4 sm:p-6 md:p-8">
      <div className="max-w-lg w-full text-center">
        {/* Icon */}
        <div
          className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 border border-amber-500/20 shadow-[0_0_30px_rgba(245,158,11,0.2)] fadeIn"
          style={{ animationDelay: '0ms', opacity: 0 }}
        >
          <Sparkles className="h-8 w-8 text-amber-500" />
        </div>

        {/* Headline */}
        <h1
          className="mb-3 text-3xl sm:text-4xl font-black tracking-tight bg-gradient-to-r from-white via-white to-amber-200 bg-clip-text text-transparent fadeIn"
          style={{ animationDelay: '100ms', opacity: 0 }}
        >
          Welcome to AutoApply
        </h1>

        <p
          className="mb-8 text-sm text-white/40 fadeIn"
          style={{ animationDelay: '200ms', opacity: 0 }}
        >
          Let's set up your account in ~3 minutes
        </p>

        {/* Feature bullets */}
        <div className="space-y-3 mb-10 text-left">
          {features.map((f, i) => (
            <div
              key={f.title}
              className="flex items-center gap-4 rounded-xl border border-white/5 bg-[#0A0A0A] p-4 transition-all hover:border-white/10 fadeIn"
              style={{ animationDelay: `${300 + i * 100}ms`, opacity: 0 }}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20">
                <f.icon className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">{f.title}</p>
                <p className="text-xs text-white/40">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <button
          onClick={onNext}
          className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_30px_rgba(245,158,11,0.3)] transition-all hover:bg-amber-400 active:scale-95 fadeIn"
          style={{ animationDelay: '700ms', opacity: 0 }}
        >
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          <span className="relative">Let's Go</span>
          <ArrowRight className="relative h-4 w-4 transition-transform group-hover:translate-x-1" />
        </button>
      </div>
    </div>
  )
}
