import { LoaderCircle, Network, Radar, SearchX } from 'lucide-react'
import type { ReactNode } from 'react'

export function RiskBadge({ level }: { level: string }) {
  return <span className={`risk-badge risk-${level.toLowerCase().replace('_', '-')}`}><i />{level.replace('_', ' ')}</span>
}

export function ScoreRing({ value, size = 82 }: { value: number; size?: number }) {
  const percentage = Math.round(value * 100)
  return <div className="score-ring" style={{ width: size, height: size, background: `conic-gradient(${value >= .72 ? '#ff5578' : value >= .45 ? '#ffba69' : '#65e6c4'} ${percentage}%, #ffffff0d 0)` }} aria-label={`Risk score ${percentage} percent`}><div><strong>{percentage}</strong><span>risk</span></div></div>
}

export function PageIntro({ eyebrow, title, text, actions }: { eyebrow: string; title: string; text?: string; actions?: ReactNode }) {
  return <header className="page-intro"><div><span className="page-eyebrow">{eyebrow}</span><h1>{title}</h1>{text && <p>{text}</p>}</div>{actions && <div className="page-actions">{actions}</div>}</header>
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>
}

export function PanelTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return <div className="panel-title"><h2>{children}</h2>{aside}</div>
}

export function GraphLoader({ label = 'Mapping transaction topology' }: { label?: string }) {
  return <div className="graph-loader" role="status"><div className="loader-mesh"><Network /><i /><i /><i /></div><span>{label}</span></div>
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><div><SearchX /></div><h3>{title}</h3><p>{text}</p>{action}</div>
}

export function ErrorState({ message }: { message: string }) {
  return <div className="error-state"><Radar /><div><strong>Signal unavailable</strong><span>{message}</span></div></div>
}

export function LoadingLine() { return <LoaderCircle className="spin" aria-label="Loading" /> }
