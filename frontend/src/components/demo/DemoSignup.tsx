import { useNavigate } from 'react-router-dom'
import { ArrowRight, Check, Sparkles, Bot, FileText, Send, BarChart3 } from 'lucide-react'

export default function DemoSignup() {
  const navigate = useNavigate()

  const features = [
    { icon: Bot, text: 'Bot applies to hundreds of jobs while you sleep' },
    { icon: FileText, text: 'AI fills every form field from your profile' },
    { icon: Send, text: 'Works on StepStone, Xing, and LinkedIn' },
    { icon: BarChart3, text: 'Track every application in real-time' },
  ]

  return (
    <div className="flex h-full items-center justify-center p-4 sm:p-8">
      <div className="relative max-w-lg w-full text-center">
        {/* Glow background */}
        <div className="absolute inset-0 -z-10 blur-[120px] opacity-30">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-amber-500" />
        </div>

        {/* Icon */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 border border-amber-500/20 shadow-[0_0_30px_rgba(245,158,11,0.2)] fadeIn">
          <Sparkles className="h-8 w-8 text-amber-500" />
        </div>

        {/* Headline */}
        <h1
          className="text-3xl sm:text-4xl font-black tracking-tight text-white mb-3 fadeIn"
          style={{ animationDelay: '100ms', opacity: 0 }}
        >
          Ready to automate
          <br />
          <span className="bg-gradient-to-r from-amber-400 to-amber-600 bg-clip-text text-transparent">
            your job search?
          </span>
        </h1>

        <p
          className="text-white/40 text-sm sm:text-base mb-8 fadeIn"
          style={{ animationDelay: '200ms', opacity: 0 }}
        >
          Join job seekers across Germany who let AI handle their applications.
        </p>

        {/* Feature checklist */}
        <div className="mb-8 space-y-3 text-left max-w-sm mx-auto">
          {features.map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-3 fadeIn"
              style={{ animationDelay: `${300 + i * 100}ms`, opacity: 0 }}
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
                <f.icon className="h-4 w-4 text-amber-500" />
              </div>
              <span className="text-sm text-white/70">{f.text}</span>
              <Check className="h-4 w-4 text-emerald-400 shrink-0 ml-auto" />
            </div>
          ))}
        </div>

        {/* Price */}
        <div
          className="mb-6 fadeIn"
          style={{ animationDelay: '700ms', opacity: 0 }}
        >
          <span className="text-4xl font-black text-white">€8</span>
          <span className="text-lg text-white/40"> / month</span>
        </div>

        {/* CTA */}
        <button
          onClick={() => navigate('/login?register=1')}
          className="group relative w-full sm:w-auto overflow-hidden rounded-xl bg-amber-500 px-10 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_30px_rgba(245,158,11,0.4)] transition-all hover:bg-amber-400 hover:shadow-[0_0_50px_rgba(245,158,11,0.5)] hover:scale-[1.02] active:scale-[0.98] fadeIn"
          style={{ animationDelay: '800ms', opacity: 0 }}
        >
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          <span className="relative flex items-center justify-center gap-2">
            Create Account
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </button>

        <p
          className="mt-4 text-xs text-white/30 fadeIn"
          style={{ animationDelay: '900ms', opacity: 0 }}
        >
          Already have an account?{' '}
          <button
            onClick={() => navigate('/login')}
            className="text-amber-500 hover:text-amber-400 transition-colors"
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  )
}
