import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { Activity, Bell, Bot, Boxes, BrainCircuit, BriefcaseBusiness, ChevronRight, CircleGauge, Command, FileSearch, LogOut, Menu, Network, Radar, Search, Settings2, ShieldAlert, Users, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../store/auth'

const nav = [
  { to: '/app', label: 'Overview', icon: CircleGauge, end: true },
  { to: '/app/transactions', label: 'Live monitor', icon: Activity },
  { to: '/app/graph', label: 'Graph explorer', icon: Network },
  { to: '/app/rings', label: 'Fraud rings', icon: Boxes },
  { to: '/app/alerts', label: 'Alert center', icon: ShieldAlert },
  { to: '/app/cases', label: 'Cases', icon: BriefcaseBusiness },
  { to: '/app/assistant', label: 'AI assistant', icon: Bot },
  { to: '/app/models', label: 'Model lab', icon: BrainCircuit },
  { to: '/app/admin', label: 'Administration', icon: Settings2 },
]

interface NotificationItem { id: string; title: string; message: string; kind: string; read: boolean; created_at: string }

export default function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [palette, setPalette] = useState(false)
  const [notices, setNotices] = useState(false)
  const [query, setQuery] = useState('')
  const location = useLocation()
  const navigate = useNavigate()
  const { user, refreshToken, clearSession } = useAuth()
  const { data: notifications = [] } = useQuery<NotificationItem[]>({ queryKey: ['notifications'], queryFn: () => api.get('/users/notifications').then((r) => r.data), refetchInterval: 15_000 })
  const current = nav.find((item) => item.end ? location.pathname === item.to : location.pathname.startsWith(item.to))
  const results = useMemo(() => nav.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())), [query])
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setPalette(true) }
      if (event.key === 'Escape') setPalette(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  const logout = async () => {
    if (refreshToken) await api.post('/auth/logout', { refresh_token: refreshToken }).catch(() => undefined)
    clearSession(); navigate('/login')
  }
  return <div className={`app-layout ${collapsed ? 'is-collapsed' : ''}`}>
    <aside className="sidebar">
      <div className="side-brand"><span><Network /></span><b>FraudMesh <em>XAI</em></b><button aria-label="Toggle sidebar" onClick={() => setCollapsed(!collapsed)}><Menu /></button></div>
      <div className="side-mode"><i /> <span>Simulation environment</span></div>
      <nav>
        {nav.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} title={label}><Icon /><span>{label}</span></NavLink>)}
      </nav>
      <div className="side-foot">
        <div className="model-signal"><Radar /><span><b>Temporal ensemble</b><small>Operational · v1.0</small></span></div>
        <button onClick={logout}><LogOut /><span>Sign out</span></button>
      </div>
    </aside>
    <div className="app-main">
      <header className="topbar">
        <div className="crumb"><FileSearch /><span>Investigation console</span><ChevronRight /><b>{current?.label ?? 'Intelligence'}</b></div>
        <button className="global-search" onClick={() => setPalette(true)}><Search /><span>Search entities, alerts, cases…</span><kbd>Ctrl K</kbd></button>
        <div className="top-actions">
          <div className="live-indicator"><i /> Live</div>
          <button className="icon-button" aria-label="Notifications" onClick={() => setNotices(!notices)}><Bell />{notifications.length > 0 && <span>{Math.min(notifications.length, 9)}</span>}</button>
          <button className="profile-button"><div>{user?.full_name.split(' ').map((word) => word[0]).slice(0,2).join('')}</div><span><b>{user?.full_name}</b><small>{user?.role}</small></span></button>
        </div>
        {notices && <div className="notification-popover"><div className="popover-head"><b>Signal center</b><button onClick={() => setNotices(false)}><X /></button></div>{notifications.slice(0,6).map((item) => <div className="notice" key={item.id}><i /><span><b>{item.title}</b><small>{item.message}</small></span></div>)}{notifications.length === 0 && <p>No new system signals.</p>}</div>}
      </header>
      <div className="content"><AnimatePresence mode="wait"><motion.div key={location.pathname} initial={{ opacity: 0, y: 12, filter: 'blur(6px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0)' }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .28 }}><Outlet /></motion.div></AnimatePresence></div>
    </div>
    <AnimatePresence>{palette && <motion.div className="palette-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={() => setPalette(false)}><motion.div className="command-palette" initial={{ y: -20, scale: .97 }} animate={{ y: 0, scale: 1 }} exit={{ y: -10, scale: .98 }} onMouseDown={(event) => event.stopPropagation()}><div className="command-input"><Command /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Jump to a FraudMesh surface…"/><kbd>ESC</kbd></div><div className="command-results"><span>Navigation</span>{results.map(({ to, label, icon: Icon }) => <button key={to} onClick={() => { navigate(to); setPalette(false); setQuery('') }}><Icon />{label}<ChevronRight /></button>)}</div><div className="command-tip"><Users /> Search across workspace-scoped intelligence</div></motion.div></motion.div>}</AnimatePresence>
  </div>
}

