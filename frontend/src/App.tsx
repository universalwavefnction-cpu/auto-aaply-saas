import { Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  LayoutDashboard,
  Bot,
  Search,
  Send,
  UserCircle,
  Settings,
  LogOut,
  Sparkles,
  Activity,
  Sun,
  Moon,
  CreditCard,
  Bug,
  Menu,
  X,
  MessageSquare,
} from 'lucide-react'

import { api } from './api'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Applications from './pages/Applications'
import Profile from './pages/Profile'
import SettingsPage from './pages/Settings'
import BotLive from './pages/BotLive'
import Billing from './pages/Billing'
import Login from './pages/Login'
import LandingPage from './pages/LandingPage'
import Contact from './pages/Contact'
import Debug from './pages/Debug'
import Support from './pages/Support'

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [subStatus, setSubStatus] = useState<string | null>(null)
  const [subLoading, setSubLoading] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>(
    (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
  )
  const location = useLocation()
  const navigate = useNavigate()

  // Close mobile menu on navigation
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  // Check subscription status when token changes
  useEffect(() => {
    const t = localStorage.getItem('token')
    setToken(t)
    if (t) {
      setSubLoading(true)
      api
        .me()
        .then((data: { subscription_status?: string; email?: string }) => {
          setSubStatus(data.subscription_status || 'free')
          setUserEmail(data.email || null)
          setSubLoading(false)
        })
        .catch(() => {
          setSubStatus('free')
          setSubLoading(false)
        })
    } else {
      setSubStatus(null)
    }
  }, [location])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const handleLogin = (t: string) => {
    localStorage.setItem('token', t)
    setToken(t)
    navigate('/billing')
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    setToken(null)
    navigate('/')
  }

  // Public routes: landing page and login
  const PUBLIC_PATHS = ['/', '/login', '/contact']
  const isPublicPath = PUBLIC_PATHS.includes(location.pathname)

  if (isPublicPath) {
    return (
      <Routes location={location}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/contact" element={<Contact />} />
        <Route
          path="/login"
          element={
            token ? <Navigate to="/dashboard" replace /> : <Login onLogin={handleLogin} />
          }
        />
      </Routes>
    )
  }

  // Protected routes: require auth
  if (!token) {
    return <Navigate to="/login" replace />
  }

  const isPaid = subStatus === 'active'
  const isAdmin = userEmail === 'dimitri.perepelkin@gmail.com'

  const nav = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Mission Control', mobileLabel: 'Home' },
    { path: '/bot', icon: Bot, label: 'Live Bot', mobileLabel: 'Bot' },
    { path: '/jobs', icon: Search, label: 'Discovery', mobileLabel: 'Jobs' },
    { path: '/applications', icon: Send, label: 'Applications', mobileLabel: 'Apps' },
    { path: '/profile', icon: UserCircle, label: 'Profile', mobileLabel: 'Profile' },
    { path: '/settings', icon: Settings, label: 'Settings', mobileLabel: 'Settings' },
    { path: '/billing', icon: CreditCard, label: 'Billing', mobileLabel: 'Billing' },
    { path: '/support', icon: MessageSquare, label: 'Support', mobileLabel: 'Support' },
    ...(isAdmin ? [{ path: '/debug', icon: Bug, label: 'Debug', mobileLabel: 'Debug' }] : []),
  ]

  // Bottom tab bar: show 5 main items
  const bottomNav = nav.filter((n) =>
    ['/dashboard', '/bot', '/jobs', '/applications', '/profile'].includes(n.path)
  )

  return (
    <div className="flex h-screen bg-[#050505] font-sans text-white overflow-hidden selection:bg-amber-500/30">
      {/* Desktop Sidebar — hidden on mobile */}
      <nav className="hidden md:flex w-64 shrink-0 flex-col border-r border-white/5 bg-[#080808] z-20">
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
        </div>

        <div className="flex-1 space-y-1 p-4">
          {nav.map(({ path, icon: Icon, label }) => {
            const isActive = location.pathname === path
            return (
              <Link
                key={path}
                to={path}
                className={`group relative flex items-center gap-3 rounded-xl px-4 py-3 text-xs font-bold uppercase tracking-[0.1em] transition-all duration-200 ${
                  isActive
                    ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.05)]'
                    : 'text-white/40 border border-transparent hover:bg-white/5 hover:text-white/80'
                }`}
              >
                <Icon
                  className={`h-4 w-4 relative z-10 transition-transform duration-200 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`}
                />
                <span className="relative z-10">{label}</span>
              </Link>
            )
          })}
        </div>

        {/* Platform status */}
        <div className="space-y-3 border-t border-white/5 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-3 w-3 text-white/20" />
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/20">
              Neural Targets
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {[
              { name: 'StepStone', active: true },
              { name: 'Xing', active: false },
              { name: 'Indeed', active: false },
              { name: 'LinkedIn', active: true },
            ].map((platform) => (
              <div
                key={platform.name}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 transition-colors ${platform.active ? 'border-amber-500/20 bg-amber-500/5' : 'border-white/5 bg-white/[0.02]'}`}
              >
                <span
                  className={`text-[9px] font-bold uppercase tracking-wider ${platform.active ? 'text-amber-500' : 'text-white/40'}`}
                >
                  {platform.name}
                </span>
                <div className="relative flex h-2 w-2 items-center justify-center">
                  {platform.active && (
                    <div className="absolute h-full w-full animate-ping rounded-full bg-amber-500 opacity-20"></div>
                  )}
                  <div
                    className={`h-1.5 w-1.5 rounded-full ${platform.active ? 'bg-amber-500' : 'bg-white/20'}`}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex border-t border-white/5">
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="group flex flex-1 items-center justify-center gap-2 p-6 text-[10px] font-bold uppercase tracking-[0.15em] text-white/30 transition-colors hover:text-amber-500 hover:bg-amber-500/5 theme-toggle-btn"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4 transition-transform group-hover:rotate-90" />
            ) : (
              <Moon className="h-4 w-4 transition-transform group-hover:-rotate-12" />
            )}
          </button>
          <button
            onClick={handleLogout}
            className="group flex flex-1 items-center justify-center gap-2 border-l border-white/5 p-6 text-[10px] font-bold uppercase tracking-[0.15em] text-white/30 transition-colors hover:text-red-400 hover:bg-red-500/5"
          >
            <LogOut className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
          </button>
        </div>
      </nav>

      {/* Mobile Header — visible on mobile only */}
      <div className="fixed top-0 left-0 right-0 z-40 flex md:hidden items-center justify-between border-b border-white/5 bg-[#080808]/95 backdrop-blur-xl px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          </div>
          <span className="text-sm font-bold tracking-tight">AutoApply</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-white/50"
        >
          {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </div>

      {/* Mobile slide-down menu */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-30 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileMenuOpen(false)} />
          <div className="absolute top-[53px] left-0 right-0 border-b border-white/10 bg-[#0A0A0A] p-4 space-y-1 max-h-[70vh] overflow-auto">
            {nav.map(({ path, icon: Icon, label }) => {
              const isActive = location.pathname === path
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-xs font-bold uppercase tracking-wider transition-all ${
                    isActive
                      ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      : 'text-white/40 border border-transparent'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              )
            })}
            <div className="flex items-center gap-2 pt-3 border-t border-white/5 mt-3">
              <button
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-[10px] font-bold uppercase tracking-wider text-white/30"
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                {theme === 'dark' ? 'Light' : 'Dark'}
              </button>
              <button
                onClick={handleLogout}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-[10px] font-bold uppercase tracking-wider text-red-400/60"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-[#050505] relative custom-scrollbar pt-[53px] md:pt-0 pb-[68px] md:pb-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-500/5 via-[#050505] to-[#050505] pointer-events-none"></div>

        {/* Paywall banner for unpaid users */}
        {!subLoading && !isPaid && (
          <div className="sticky top-0 z-20 border-b border-amber-500/20 bg-amber-500/10 backdrop-blur-xl">
            <div className="mx-auto flex max-w-4xl items-center justify-between px-4 md:px-6 py-2.5 md:py-3">
              <div className="flex items-center gap-2 md:gap-3">
                <CreditCard className="h-4 w-4 shrink-0 text-amber-500" />
                <span className="text-xs md:text-sm font-bold text-amber-200">
                  Subscribe to unlock — €8/mo
                </span>
              </div>
              <Link
                to="/billing"
                className="shrink-0 rounded-lg bg-amber-500 px-3 md:px-4 py-1.5 text-[10px] md:text-xs font-black uppercase tracking-wider text-black transition-colors hover:bg-amber-400"
              >
                Subscribe
              </Link>
            </div>
          </div>
        )}

        <div key={location.pathname} className="relative z-10 h-full page-transition">
          <Routes location={location}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/bot" element={<BotLive />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/applications" element={<Applications />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/support" element={<Support />} />
            {isAdmin && <Route path="/debug" element={<Debug />} />}
            <Route path="*" element={<Navigate to="/dashboard" />} />
          </Routes>
        </div>
      </main>

      {/* Mobile Bottom Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-40 flex md:hidden border-t border-white/5 bg-[#080808]/95 backdrop-blur-xl">
        {bottomNav.map(({ path, icon: Icon, mobileLabel }) => {
          const isActive = location.pathname === path
          return (
            <Link
              key={path}
              to={path}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 transition-colors ${
                isActive ? 'text-amber-500' : 'text-white/30'
              }`}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'scale-110' : ''} transition-transform`} />
              <span className="text-[9px] font-bold uppercase tracking-wider">{mobileLabel}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

export default App
