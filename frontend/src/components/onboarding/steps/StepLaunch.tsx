import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Briefcase, MapPin, AlertCircle } from 'lucide-react'
import { api } from '../../../api'

const platformOptions = [
  { value: 'xing', label: 'Xing', short: 'XI' },
  { value: 'stepstone', label: 'StepStone', short: 'SS' },
  { value: 'indeed', label: 'Indeed', short: 'IN' },
  { value: 'linkedin', label: 'LinkedIn', short: 'LI' },
]

export default function StepLaunch() {
  const navigate = useNavigate()
  const [jobTitle, setJobTitle] = useState('')
  const [location, setLocation] = useState('')
  const [platform, setPlatform] = useState('xing')
  const [maxApps, setMaxApps] = useState(10)
  const [selectedCv, setSelectedCv] = useState<number | null>(null)
  const [cvs, setCvs] = useState<any[]>([])
  const [launching, setLaunching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    Promise.all([
      api.listCVs().then((res: any) => {
        const list = Array.isArray(res) ? res : []
        setCvs(list)
        if (list.length > 0) setSelectedCv(list[0].id)
      }),
      api.getFilters().then((res: any) => {
        if (res.job_titles?.length) setJobTitle(res.job_titles[0])
        if (res.locations?.length) setLocation(res.locations[0])
        if (res.platform) setPlatform(res.platform)
      }),
    ]).finally(() => setLoaded(true))
  }, [])

  const handleLaunch = async () => {
    if (!jobTitle.trim()) return
    setLaunching(true)
    setError(null)
    try {
      await api.updateFilters({
        job_titles: [jobTitle.trim()],
        locations: location.trim() ? [location.trim()] : ['deutschland'],
        platform,
        max_applications: maxApps,
        selected_cv_id: selectedCv,
      })
      await api.startBot('scrape_and_apply')
      localStorage.setItem('onboarding_complete', '1')
      navigate('/bot')
    } catch (e: any) {
      setError(e.message || 'Failed to launch bot')
      setLaunching(false)
    }
  }

  if (!loaded) return (
    <div className="flex items-center justify-center min-h-full">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
    </div>
  )

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-xl mx-auto">
      <div className="fadeIn" style={{ animationDelay: '0ms', opacity: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.15)]">
            <Rocket className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Launch Your First Run</h2>
            <p className="text-xs text-white/40">Pick a target and let the bot do the rest</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 sm:p-8 shadow-2xl demo-hotspot fadeIn" style={{ animationDelay: '100ms', opacity: 0 }}>
        {/* Job Title */}
        <div className="mb-5">
          <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
            Target Position <span className="text-amber-500">*</span>
          </label>
          <div className="relative">
            <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-white/20" />
            <input
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="e.g. Frontend Engineer"
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
        </div>

        {/* Location */}
        <div className="mb-5">
          <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Location</label>
          <div className="relative">
            <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-white/20" />
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Berlin, Remote (defaults to Deutschland)"
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-11 pr-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
        </div>

        {/* Platform */}
        <div className="mb-5">
          <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Platform</label>
          <div className="flex gap-2">
            {platformOptions.map((p) => (
              <button
                key={p.value}
                onClick={() => setPlatform(p.value)}
                className={`flex-1 rounded-xl border px-3 py-3 text-xs font-black uppercase tracking-wider transition-all ${
                  platform === p.value
                    ? 'border-amber-500/50 bg-amber-500/10 text-amber-500'
                    : 'border-white/10 bg-black/30 text-white/40 hover:border-white/20'
                }`}
              >
                {p.short}
              </button>
            ))}
          </div>
        </div>

        {/* Volume */}
        <div className="mb-5">
          <label className="mb-2 flex items-center justify-between text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
            <span>Volume</span>
            <span className="text-amber-500">{maxApps} applications</span>
          </label>
          <input
            type="range"
            min={1}
            max={500}
            value={maxApps}
            onChange={(e) => setMaxApps(parseInt(e.target.value))}
            className="w-full accent-amber-500"
          />
        </div>

        {/* Resume */}
        {cvs.length > 0 && (
          <div className="mb-6">
            <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Resume</label>
            <select
              value={selectedCv || ''}
              onChange={(e) => setSelectedCv(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full cursor-pointer appearance-none rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white focus:border-amber-500/50 focus:bg-black focus:outline-none"
            >
              <option value="">Default Platform CV</option>
              {cvs.map((cv) => (
                <option key={cv.id} value={cv.id}>{cv.label}</option>
              ))}
            </select>
          </div>
        )}

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Launch button */}
        <button
          onClick={handleLaunch}
          disabled={!jobTitle.trim() || launching}
          className="group relative flex w-full items-center justify-center gap-3 overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_30px_rgba(245,158,11,0.3)] transition-all hover:bg-amber-400 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          {launching ? (
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-black border-t-transparent" />
          ) : (
            <>
              <Rocket className="relative h-5 w-5" />
              <span className="relative">Launch Bot</span>
            </>
          )}
        </button>

        <p className="mt-3 text-center text-[10px] text-white/30">
          The bot will scrape jobs and apply automatically
        </p>
      </div>
    </div>
  )
}
