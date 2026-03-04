import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { CreditCard, Check, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react'
import { api } from '../api'

interface BillingStatus {
  subscription_status: string
  subscription_ends_at: string | null
  has_active_subscription: boolean
}

export default function Billing() {
  const [status, setStatus] = useState<BillingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    loadStatus()
    if (searchParams.get('success') === '1') {
      gtag('event', 'purchase', { currency: 'EUR', value: 8.0 })
      const onboardingDone = localStorage.getItem('onboarding_complete')
      if (!onboardingDone) {
        navigate('/onboarding')
        return
      }
      setToast({ type: 'success', message: 'Subscription activated! You can now run the bot.' })
    } else if (searchParams.get('canceled') === '1') {
      setToast({ type: 'error', message: 'Checkout was canceled.' })
    }
  }, [searchParams])

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 5000)
      return () => clearTimeout(t)
    }
  }, [toast])

  async function loadStatus() {
    try {
      const data = await api.getBillingStatus()
      setStatus(data)
    } catch {
      setToast({ type: 'error', message: 'Failed to load billing status' })
    } finally {
      setLoading(false)
    }
  }

  async function handleCheckout() {
    setActionLoading(true)
    gtag('event', 'begin_checkout', { currency: 'EUR', value: 8.0 })
    try {
      const data = await api.createCheckoutSession()
      if (data.url) window.location.href = data.url
    } catch {
      setToast({ type: 'error', message: 'Failed to start checkout' })
      setActionLoading(false)
    }
  }

  async function handlePortal() {
    setActionLoading(true)
    try {
      const data = await api.createPortalSession()
      if (data.url) window.location.href = data.url
    } catch {
      setToast({ type: 'error', message: 'Failed to open billing portal' })
      setActionLoading(false)
    }
  }

  const isActive = status?.has_active_subscription
  const statusLabel =
    {
      active: 'Active',
      canceled: 'Canceled',
      past_due: 'Past Due',
      free: 'Free',
    }[status?.subscription_status || 'free'] || 'Free'

  const statusColor = isActive
    ? 'text-emerald-500 border-emerald-500/20 bg-emerald-500/10'
    : 'text-amber-500 border-amber-500/20 bg-amber-500/10'

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-3xl mx-auto">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed right-4 sm:right-6 top-[60px] md:top-6 z-50 left-4 sm:left-auto flex items-center gap-3 rounded-xl border px-5 py-3 text-sm font-medium shadow-2xl animate-[fadeIn_0.2s] ${
            toast.type === 'success'
              ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
              : 'border-red-500/20 bg-red-500/10 text-red-400'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <CreditCard className="h-5 w-5 text-amber-500" />
          <h1 className="text-2xl font-black tracking-tight">Billing</h1>
        </div>
        <p className="text-sm text-white/40">Manage your subscription and billing.</p>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-8">
          <div className="shimmer h-6 w-48 rounded-lg bg-white/5" />
          <div className="shimmer mt-4 h-4 w-32 rounded-lg bg-white/5" />
        </div>
      ) : (
        <>
          {/* Status card */}
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-5 sm:p-8 mb-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/30">
                  Subscription Status
                </span>
                <div className="mt-2 flex items-center gap-3">
                  <span
                    className={`rounded-lg border px-3 py-1 text-[10px] font-black uppercase tracking-wider ${statusColor}`}
                  >
                    {statusLabel}
                  </span>
                  {status?.subscription_ends_at && (
                    <span className="text-xs text-white/30">
                      Access until{' '}
                      {new Date(status.subscription_ends_at).toLocaleDateString('en-US', {
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {isActive ? (
              <button
                onClick={handlePortal}
                disabled={actionLoading}
                className="flex items-center gap-2 rounded-xl border border-white/10 px-6 py-3 text-xs font-bold uppercase tracking-wider text-white/60 transition-colors hover:border-white/20 hover:text-white disabled:opacity-50"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                {actionLoading ? 'Opening...' : 'Manage subscription'}
              </button>
            ) : (
              <button
                onClick={handleCheckout}
                disabled={actionLoading}
                className="group relative overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:bg-amber-400 disabled:opacity-50"
              >
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
                <span className="relative">
                  {actionLoading ? 'Redirecting...' : 'Subscribe — €8/month'}
                </span>
              </button>
            )}
          </div>

          {/* Plan details */}
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-5 sm:p-8">
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/30">
              Plan Details
            </span>
            <div className="mt-4 mb-6 flex items-baseline gap-1">
              <span className="text-3xl font-black">€8</span>
              <span className="text-sm text-white/40"> / month</span>
            </div>
            <ul className="space-y-3">
              {[
                'All platforms (StepStone, Xing, LinkedIn)',
                'Unlimited applications',
                'Real-time bot monitoring',
                'Multiple CV management',
                'Smart AI form filling',
                'Cancel anytime',
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm text-white/50">
                  <Check className="h-4 w-4 shrink-0 text-amber-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
