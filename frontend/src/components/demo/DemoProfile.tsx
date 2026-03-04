import {
  UserCircle,
  FileText,
  Shield,
  MessageSquare,
  CheckCircle2,
  Upload,
  Key,
} from 'lucide-react'
import { DEMO_PROFILE, DEMO_QA_PAIRS, DEMO_CREDENTIALS } from './demoData'

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="mb-1.5 block text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
        {label}
      </label>
      <div className="rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white">
        {value}
      </div>
    </div>
  )
}

export default function DemoProfile() {
  return (
    <div className="space-y-6 sm:space-y-8 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="shrink-0 rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
          <UserCircle className="h-5 w-5 text-amber-500" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Operator Profile
          </h1>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
            Identity & Credentials
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column — Personal Data */}
        <div className="space-y-6 lg:col-span-7">
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 sm:p-8">
            <div className="mb-6 flex items-center gap-3">
              <UserCircle className="h-4 w-4 text-amber-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Personal Data
              </span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="First Name" value={DEMO_PROFILE.first_name} />
              <Field label="Last Name" value={DEMO_PROFILE.last_name} />
              <Field label="Phone" value={DEMO_PROFILE.phone} />
              <Field label="City" value={DEMO_PROFILE.city} />
              <Field label="ZIP Code" value={DEMO_PROFILE.zip_code} />
              <Field label="Expected Salary" value={`€${DEMO_PROFILE.salary}`} />
            </div>
            <div className="mt-4">
              <label className="mb-1.5 block text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Professional Summary
              </label>
              <div className="rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white/80 leading-relaxed">
                {DEMO_PROFILE.summary}
              </div>
            </div>
          </div>

          {/* Q&A Vault */}
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 sm:p-8">
            <div className="mb-6 flex items-center gap-3">
              <MessageSquare className="h-4 w-4 text-amber-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Q&A Vault
              </span>
              <span className="ml-auto rounded-lg bg-white/5 px-2.5 py-1 text-[9px] font-bold text-white/30">
                {DEMO_QA_PAIRS.length} pairs
              </span>
            </div>
            <div className="space-y-3">
              {DEMO_QA_PAIRS.map((pair, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/5 bg-black/30 p-4 fadeIn"
                  style={{ animationDelay: `${i * 100}ms`, opacity: 0 }}
                >
                  <p className="text-xs font-bold text-white/60 mb-1">{pair.q}</p>
                  <p className="text-sm text-amber-500">{pair.a}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column — CV & Credentials */}
        <div className="space-y-6 lg:col-span-5">
          {/* CV Library */}
          <div className="demo-hotspot rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 sm:p-8">
            <div className="mb-6 flex items-center gap-3">
              <FileText className="h-4 w-4 text-amber-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                CV Library
              </span>
            </div>

            {/* Uploaded CV */}
            <div className="mb-4 flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <FileText className="h-5 w-5 text-emerald-400" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-white truncate">resume_max_mustermann.pdf</p>
                <p className="text-[10px] text-white/40">Main Resume</p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
            </div>

            {/* Upload zone */}
            <div className="rounded-xl border-2 border-dashed border-white/10 bg-white/[0.02] p-6 text-center">
              <Upload className="mx-auto h-8 w-8 text-white/20 mb-2" />
              <p className="text-xs font-bold text-white/40">Drop your CV here</p>
              <p className="text-[10px] text-white/20 mt-1">PDF, DOC, DOCX</p>
            </div>
          </div>

          {/* Platform Credentials */}
          <div className="demo-hotspot rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 sm:p-8">
            <div className="mb-6 flex items-center gap-3">
              <Key className="h-4 w-4 text-amber-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Platform Access
              </span>
            </div>

            <div className="space-y-3">
              {DEMO_CREDENTIALS.map((cred, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-xl border border-white/5 bg-black/30 p-4 fadeIn"
                  style={{ animationDelay: `${i * 150}ms`, opacity: 0 }}
                >
                  <Shield className="h-5 w-5 text-amber-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-white">{cred.platform}</p>
                    <p className="text-[10px] text-white/40 truncate">{cred.email}</p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <div className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]"></div>
                    <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-400">
                      Connected
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-xl border border-dashed border-amber-500/20 bg-amber-500/5 p-4 text-center">
              <p className="text-xs font-bold text-amber-500">+ Add platform credentials</p>
              <p className="text-[10px] text-white/30 mt-1">
                The bot logs in on your behalf
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
