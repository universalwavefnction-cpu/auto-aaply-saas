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
    return <Login onLogin={(t: string) => { localStorage.setItem('token', t); setToken(t) }} />
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
    <div className="flex h-screen bg-[#050505] text-white font-sans">
      {/* Sidebar */}
      <nav className="w-52 border-r border-white/5 flex flex-col bg-[#080808] shrink-0">
        <div className="p-6 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-amber-500 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <span className="font-bold text-sm tracking-tight">AutoApply</span>
              <span className="block text-[8px] text-amber-500 font-black uppercase tracking-[0.2em]">Intelligence</span>
            </div>
          </div>
        </div>

        <div className="flex-1 py-4 space-y-1">
          {nav.map(({ path, icon, label }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-6 py-2.5 text-[11px] font-bold uppercase tracking-[0.15em] transition-colors ${
                location.pathname === path
                  ? 'text-amber-500 bg-amber-500/5 border-r-2 border-amber-500'
                  : 'text-white/30 hover:text-white/60'
              }`}
            >
              <span className="text-sm">{icon}</span>
              {label}
            </Link>
          ))}
        </div>

        {/* Platform status */}
        <div className="px-6 py-4 border-t border-white/5 space-y-3">
          <span className="text-[7px] font-black text-white/10 uppercase tracking-[0.3em]">Neural Targets</span>
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between px-2 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-md">
              <span className="text-amber-500 font-bold text-[8px] uppercase">StepStone</span>
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
            </div>
            <div className="flex items-center justify-between px-2 py-1.5 bg-white/[0.02] border border-white/5 rounded-md">
              <span className="text-white/40 font-bold text-[8px] uppercase">Xing</span>
              <div className="w-1.5 h-1.5 rounded-full bg-white/20"></div>
            </div>
            <div className="flex items-center justify-between px-2 py-1.5 bg-white/[0.02] border border-white/5 rounded-md opacity-40">
              <span className="text-white/20 font-bold text-[8px] uppercase">LinkedIn</span>
              <span className="text-[5px] text-white/10 uppercase font-black">Soon</span>
            </div>
          </div>
        </div>

        <button
          onClick={() => { localStorage.removeItem('token'); setToken(null) }}
          className="flex items-center gap-3 px-6 py-4 text-[10px] font-bold uppercase tracking-[0.15em] text-white/20 hover:text-red-400 border-t border-white/5 transition-colors"
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
