import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { Activity, ArrowLeft, ChevronDown, CircleDollarSign, Filter, Globe2, Network, Pause, Play, Search, Square, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { EmptyState, ErrorState, GraphLoader, PageIntro, Panel, PanelTitle, RiskBadge, ScoreRing } from '../components/UI'
import { WS_URL, api, errorMessage } from '../lib/api'
import { useAuth } from '../store/auth'
import type { GraphResponse, Transaction } from '../types'

function money(value: number, currency = 'USD') { return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value) }
function when(value: string) { return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }

export default function Transactions() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const token = useAuth((state) => state.accessToken)
  const [connected, setConnected] = useState(false)
  const [risk, setRisk] = useState('ALL')
  const [search, setSearch] = useState('')
  const [speed, setSpeed] = useState(5)
  const { data = [], isLoading, error } = useQuery<Transaction[]>({ queryKey: ['transactions'], queryFn: () => api.get('/transactions?limit=200').then((response) => response.data) })
  useEffect(() => {
    if (!token) return
    let socket: WebSocket | null = null
    let retry: number | undefined
    let active = true
    const connect = () => {
      socket = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`)
      socket.onopen = () => setConnected(true)
      socket.onclose = () => { setConnected(false); if (active) retry = window.setTimeout(connect, 1800) }
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as { event: string; data: Transaction }
        if (message.event === 'transaction.created') client.setQueryData<Transaction[]>(['transactions'], (old = []) => [message.data, ...old].slice(0, 300))
        if (message.event === 'fraud.alert.created') client.invalidateQueries({ queryKey: ['alerts'] })
      }
    }
    connect()
    return () => { active = false; if (retry) clearTimeout(retry); socket?.close() }
  }, [client, token])
  const simulation = useMutation({ mutationFn: (action: string) => api.post(`/simulation/${action}`, action === 'start' ? { speed } : {}), onSuccess: ({data: state}) => toast.success(`Simulation ${state.state.toLowerCase()}`), onError: (err) => toast.error(errorMessage(err)) })
  const filtered = useMemo(() => data.filter((item) => (risk === 'ALL' || item.risk_level === risk) && (!search || `${item.external_id} ${item.account_id} ${item.merchant_name} ${item.device_id} ${item.location}`.toLowerCase().includes(search.toLowerCase()))), [data,risk,search])
  if (isLoading) return <GraphLoader label="Opening live transaction channel" />
  if (error) return <ErrorState message={errorMessage(error)} />
  return <>
    <PageIntro eyebrow="Real-time detection" title="Live transaction monitor" text="Simulated events are persisted, scored, graphed, and streamed without a page refresh." actions={<div className="socket-state">{connected ? <Wifi/> : <WifiOff/>}<span><b>{connected ? 'WebSocket connected' : 'Reconnecting'}</b><small>SIMULATED DATA</small></span></div>} />
    <Panel className="monitor-panel">
      <div className="monitor-toolbar"><div className="simulation-control"><button className="start-sim" onClick={() => simulation.mutate('start')}><Play/> Start simulation</button><button onClick={() => simulation.mutate('pause')}><Pause/></button><button onClick={() => simulation.mutate('stop')}><Square/></button><label>Speed<select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value={1}>1 event/sec</option><option value={5}>5 events/sec</option><option value={10}>10 events/sec</option></select><ChevronDown/></label></div><div className="feed-controls"><label className="search-field"><Search/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search feed"/></label><label className="filter-select"><Filter/><select value={risk} onChange={(event) => setRisk(event.target.value)}><option>ALL</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label></div></div>
      <div className="feed-meta"><span><i/> LIVE INGESTION</span><b>{filtered.length} events in current view</b><small>Every event on this page is simulated or user-imported.</small></div>
      {filtered.length ? <div className="table-scroll"><table className="data-table transaction-table"><thead><tr><th>Transaction</th><th>Timestamp</th><th>Account</th><th>Merchant</th><th>Amount</th><th>Device</th><th>IP address</th><th>Location</th><th>Risk</th><th>Status</th></tr></thead><tbody><AnimatePresence initial={false}>{filtered.map((item,index)=><motion.tr layout key={item.id} initial={index < 3 ? { opacity: 0, y: -12, backgroundColor: '#7d55ff2a' } : false} animate={{ opacity: 1, y: 0, backgroundColor: 'transparent' }} onClick={() => navigate(`/app/transactions/${item.id}`)}><td><b>{item.external_id}</b><small>{item.source}</small></td><td className="mono">{when(item.occurred_at)}</td><td className="mono">{item.account_id}</td><td>{item.merchant_name}</td><td><b>{money(item.amount,item.currency)}</b></td><td className="mono">{item.device_id}</td><td className="mono">{item.ip_address}</td><td>{item.location}</td><td><span className={`table-score score-${item.risk_level.toLowerCase()}`}>{Math.round(item.risk_score*100)}</span></td><td><RiskBadge level={item.risk_level}/></td></motion.tr>)}</AnimatePresence></tbody></table></div> : <EmptyState title="No events match this view" text="Change the filters or start Simulation Mode to generate a clearly labelled transaction stream."/>}
    </Panel>
  </>
}

export function TransactionDetail() {
  const { transactionId = '' } = useParams()
  const { data: transaction, isLoading, error } = useQuery<Transaction>({ queryKey: ['transaction',transactionId], queryFn: () => api.get(`/transactions/${transactionId}`).then((response) => response.data), enabled: !!transactionId })
  const { data: graph } = useQuery<GraphResponse>({ queryKey: ['transaction-graph',transactionId], queryFn: () => api.get(`/graph/transaction/${transactionId}`).then((response) => response.data), enabled: !!transactionId })
  if (isLoading) return <GraphLoader label="Resolving transaction neighborhood" />
  if (error || !transaction) return <ErrorState message={errorMessage(error)} />
  const factors = transaction.evidence?.factors ?? []
  return <>
    <Link className="back-link" to="/app/transactions"><ArrowLeft/> Live transaction monitor</Link>
    <PageIntro eyebrow={`Transaction / ${transaction.external_id}`} title="Signal anatomy" text={`Observed ${new Date(transaction.occurred_at).toLocaleString()} · ${transaction.source === 'SIMULATION' ? 'SIMULATED DATA' : transaction.source}`} actions={<div className="detail-risk"><ScoreRing value={transaction.risk_score}/><span><RiskBadge level={transaction.risk_level}/><small>{transaction.model_version}</small></span></div>} />
    <div className="detail-grid"><Panel className="metadata-panel"><PanelTitle>Transaction metadata</PanelTitle><div className="metadata-grid">{[['Account',transaction.account_id],['Customer',transaction.customer_id||'Not supplied'],['Merchant',transaction.merchant_name],['Merchant ID',transaction.merchant_id],['Amount',money(transaction.amount,transaction.currency)],['Device',transaction.device_id],['IP address',transaction.ip_address],['Location',transaction.location],['Status',transaction.status]].map(([label,value])=><div key={label}><span>{label}</span><b>{value}</b></div>)}</div></Panel><Panel className="breakdown-panel"><PanelTitle>Risk contribution</PanelTitle><div className="factor-bars">{factors.map((factor)=><div key={factor.key}><span>{factor.label}</span><i><b style={{width:`${Math.min(100,factor.contribution*320)}%`}}/></i><strong>{Math.round(factor.contribution*100)}%</strong></div>)}</div></Panel>
      <Panel className="evidence-panel"><PanelTitle>Why was this flagged?</PanelTitle><div className="reason-list">{transaction.evidence?.reasons?.map((reason,index)=><div key={reason}><span>{String(index+1).padStart(2,'0')}</span><p>{reason}</p></div>)}</div><div className="model-stamp"><Activity/><span><b>Prediction recorded</b><small>{transaction.evidence?.prediction_timestamp ? new Date(transaction.evidence.prediction_timestamp).toLocaleString() : 'Current ingestion cycle'}</small></span></div></Panel>
      <Panel className="neighborhood-panel"><PanelTitle aside={<Network/>}>Nearby graph neighborhood</PanelTitle><div className="nearby-graph"><svg viewBox="0 0 500 260"><path d="M250 130L80 50M250 130L420 50M250 130L65 220M250 130L435 215"/></svg><div className="central-node"><CircleDollarSign/><span>{transaction.external_id}</span></div>{graph?.nodes.filter((node)=>node.data.type!=='TRANSACTION').slice(0,4).map((node,index)=><div key={node.data.id} className={`neighbor-node neighbor-${index}`}><Globe2/><span>{node.data.type}</span><small>{node.data.label}</small></div>)}</div></Panel>
    </div>
  </>
}

