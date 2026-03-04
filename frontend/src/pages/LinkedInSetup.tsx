import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Shield,
  ExternalLink,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react'

export default function LinkedInSetup() {
  return (
    <div className="space-y-6 sm:space-y-8 p-4 sm:p-6 md:p-8 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">LinkedIn Setup</h1>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
            Required for LinkedIn applications
          </p>
        </div>
      </div>

      {/* Why this is needed */}
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-red-400" />
          <div>
            <p className="text-sm font-bold text-red-400">Without this setup, LinkedIn will not work</p>
            <p className="mt-2 text-sm leading-relaxed text-white/50">
              LinkedIn sends a <span className="font-bold text-white/80">verification code</span> via email every time the bot logs in from a new session. The bot needs access to your Gmail to read this code automatically. If not configured, all LinkedIn applications will be skipped.
            </p>
          </div>
        </div>
      </div>

      {/* Step by step */}
      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl space-y-6">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-amber-500" />
          <h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">Step-by-step guide</h2>
        </div>

        <div className="space-y-4">
          <Step n={1} title="Enable 2-Step Verification on Google">
            <p>Go to your Google Account security settings and make sure 2-Step Verification is turned on.</p>
            <a href="https://myaccount.google.com/security" target="_blank" rel="noopener" className="mt-2 inline-flex items-center gap-1.5 text-sm font-bold text-amber-500 underline underline-offset-2 hover:text-amber-400">
              Open Google Security <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Step>

          <Step n={2} title="Create an App Password">
            <p>Go to App Passwords in your Google Account. Create a new one and name it <span className="font-mono font-bold text-amber-500/80">"AutoApply"</span>.</p>
            <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" className="mt-2 inline-flex items-center gap-1.5 text-sm font-bold text-amber-500 underline underline-offset-2 hover:text-amber-400">
              Open App Passwords <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Step>

          <Step n={3} title="Copy the 16-character code">
            <p>Google will show you a 16-character password like <span className="font-mono font-bold text-white/70">abcd efgh ijkl mnop</span>. Copy it — you'll only see it once.</p>
          </Step>

          <Step n={4} title="Add LinkedIn credential in your Profile">
            <p>Go to your Profile page, scroll to <span className="font-bold text-white/70">Platform Access</span>, select <span className="font-bold text-white/70">LinkedIn</span>, and fill in:</p>
            <ul className="mt-2 space-y-1 text-sm text-white/50">
              <li>&bull; Your <span className="text-white/70">LinkedIn email</span> and <span className="text-white/70">password</span></li>
              <li>&bull; Your <span className="text-white/70">Gmail address</span></li>
              <li>&bull; The <span className="text-white/70">16-character App Password</span> from step 3</li>
            </ul>
            <Link to="/profile" className="mt-3 inline-flex items-center gap-2 rounded-xl bg-amber-500 px-5 py-2.5 text-[10px] font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400">
              Go to Profile <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Step>
        </div>

        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5 text-emerald-400" />
            <div>
              <p className="text-sm font-bold text-emerald-400">That's it!</p>
              <p className="mt-1 text-sm text-white/50">
                Once configured, the bot will automatically read LinkedIn verification codes and log in on your behalf. You only need to do this once.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Help */}
      <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 text-center">
        <p className="text-sm text-white/40">
          Need help? <Link to="/support" className="font-bold text-amber-500 underline underline-offset-2 hover:text-amber-400">Contact Support</Link> — we'll walk you through it.
        </p>
      </div>
    </div>
  )
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20 text-sm font-black text-amber-500">
        {n}
      </div>
      <div className="flex-1">
        <h3 className="text-sm font-bold text-white/80">{title}</h3>
        <div className="mt-1 text-sm leading-relaxed text-white/40">{children}</div>
      </div>
    </div>
  )
}
