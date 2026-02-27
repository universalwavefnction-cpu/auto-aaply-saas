import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import Profile from './pages/Profile'
import SettingsPage from './pages/Settings'
import BotLive from './pages/BotLive'
import Login from './pages/Login'

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const location = useLocation()

  useEffect(() => {
    const t = localStorage.getItem('token')
    setToken(t)
  }, [location])

  if (!token) {
    return (
      <Login
        onLogin={(t: string) => {
          localStorage.setItem('token', t)
          setToken(t)
        }}
      />
    )
  }

  const nav = [
    { path: '/', icon: '◆', label: 'Mission Control' },
    { path: '/bot', icon: '⚡', label: 'Live Bot' },
    { path: '/jobs', icon: '⊞', label: 'Discovery' },
    { path: '/applications', icon: '↗', label: 'Applications' },
    { path: '/profile', icon: '◉', label: 'Profile' },
    { path: '/settings', icon: '⚙', label: 'Settings' },
  ]

  return (
    <div className="flex h-screen bg-[#050505] font-sans text-white">
      {/* Sidebar */}
      <nav className="flex w-52 shrink-0 flex-col border-r border-white/5 bg-[#080808]">
        <div className="border-b border-white/5 p-6">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500">
              <svg
                className="h-4 w-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <span className="text-sm font-bold tracking-tight">AutoApply</span>
              <span className="block text-[8px] font-black uppercase tracking-[0.2em] text-amber-500">
                Intelligence
              </span>
            </div>
          </div>
        </div>

        <div className="flex-1 space-y-1 py-4">
          {nav.map(({ path, icon, label }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-6 py-2.5 text-[11px] font-bold uppercase tracking-[0.15em] transition-colors ${
                location.pathname === path
                  ? 'border-r-2 border-amber-500 bg-amber-500/5 text-amber-500'
                  : 'text-white/30 hover:text-white/60'
              }`}
            >
              <span className="text-sm">{icon}</span>
              {label}
            </Link>
          ))}
        </div>

        {/* Platform status */}
        <div className="space-y-3 border-t border-white/5 px-6 py-4">
          <span className="text-[7px] font-black uppercase tracking-[0.3em] text-white/10">
            Neural Targets
          </span>
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between rounded-md border border-amber-500/20 bg-amber-500/10 px-2 py-1.5">
              <span className="text-[8px] font-bold uppercase text-amber-500">StepStone</span>
              <div className="h-1.5 w-1.5 rounded-full bg-amber-500"></div>
            </div>
            <div className="flex items-center justify-between rounded-md border border-white/5 bg-white/[0.02] px-2 py-1.5">
              <span className="text-[8px] font-bold uppercase text-white/40">Xing</span>
              <div className="h-1.5 w-1.5 rounded-full bg-white/20"></div>
            </div>
            <div className="flex items-center justify-between rounded-md border border-white/5 bg-white/[0.02] px-2 py-1.5">
              <span className="text-[8px] font-bold uppercase text-white/40">Indeed</span>
              <div className="h-1.5 w-1.5 rounded-full bg-white/20"></div>
            </div>
            <div className="flex items-center justify-between rounded-md border border-white/5 bg-white/[0.02] px-2 py-1.5">
              <span className="text-[8px] font-bold uppercase text-white/40">LinkedIn</span>
              <div className="h-1.5 w-1.5 rounded-full bg-white/20"></div>
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            localStorage.removeItem('token')
            setToken(null)
          }}
          className="flex items-center gap-3 border-t border-white/5 px-6 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-white/20 transition-colors hover:text-red-400"
        >
          ⏻ Disconnect
        </button>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-black">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/bot" element={<BotLive />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
