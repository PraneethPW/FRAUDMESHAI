import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { Activity, ArrowLeft, ChevronDown, CircleDollarSign, Filter, Globe2, Network, Pause, Play, Search, Square, Wifi, WifiOff } from 'lucide-react'
import { useState, useRef } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { EmptyState, ErrorState, GraphLoader, PageIntro, Panel, PanelTitle, RiskBadge, ScoreRing } from '../components/UI'
import { api, errorMessage, downloadFile } from '../lib/api'
import { useLive } from '../lib/realtime'
import type { GraphResponse, Transaction } from '../types'

function money(value: number, currency = 'USD') { try { return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value) } catch { return `${currency} ${value.toFixed(2)}` } }
function when(value: string) { return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }

export default function Transactions() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const connected = useLive((state) => state.connected)
  const [page, setPage] = useState(0)
  const [showForm, setShowForm] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const [importReport, setImportReport] = useState<{ imported:number; duplicates:number; failed_count:number; failed:Array<{row:number;error:string}> } | null>(null)
  const [risk, setRisk] = useState('ALL')
  const [search, setSearch] = useState('')
  const [speed, setSpeed] = useState(5)
  const { data = [], isLoading, error } = useQuery<Transaction[]>({ placeholderData:(previous)=>previous, queryKey: ['transactions',risk,search,page], queryFn: () => api.get('/transactions',{params:{limit:50,offset:page*50,risk:risk==='ALL'?undefined:risk,search:search||undefined}}).then((response) => response.data) })
  const { data: sim } = useQuery<{state:string;sequence:number;error?:string}>({queryKey:['simulation'],queryFn:()=>api.get('/simulation/status').then((r)=>r.data),refetchInterval:10000})
  const upload = useMutation({mutationFn:(file:File)=>{const body=new FormData();body.append('file',file);return api.post('/datasets/upload',body,{timeout:180000})},onSuccess:({data})=>{setImportReport(data);void client.invalidateQueries();toast.success(`${data.imported} imported; ${data.duplicates} duplicates; ${data.failed_count} rejected`)},onError:(err)=>toast.error(errorMessage(err))})
  const create = useMutation({mutationFn:(form:HTMLFormElement)=>{const values=Object.fromEntries(new FormData(form));return api.post('/transactions',{...values,amount:Number(values.amount),external_id:values.external_id||undefined,occurred_at:values.occurred_at?new Date(String(values.occurred_at)).toISOString():undefined})},onSuccess:()=>{toast.success('Transaction scored and saved');setShowForm(false);void client.invalidateQueries()},onError:(err)=>toast.error(errorMessage(err))})
  const simulation = useMutation({ mutationFn: (action: string) => api.post(`/simulation/${action}`, action === 'start' ? { speed } : {}), onSuccess: ({data: state}) => {toast.success(`Simulation ${state.state.toLowerCase()}`);void client.invalidateQueries({queryKey:['simulation']})}, onError: (err) => toast.error(errorMessage(err)) })
  const filtered = data
  if (isLoading) return <GraphLoader label="Opening live transaction channel" />
  if (error) return <ErrorState message={errorMessage(error)} />
  return <>
    <PageIntro eyebrow="Real-time detection" title="Live transaction monitor" text="API, CSV and simulated events are scored, persisted and streamed across the investigation workspace." actions={<div className="socket-state">{connected ? <Wifi/> : <WifiOff/>}<span><b>{connected ? 'WebSocket connected' : 'Reconnecting'}</b><small>{sim?.state ?? 'STOPPED'} · simulation</small></span></div>} />
    <div className="list-toolbar"><button className="button-primary" onClick={()=>setShowForm(!showForm)}>Submit transaction</button><button onClick={()=>input.current?.click()} disabled={upload.isPending}>{upload.isPending?'Importing…':'Import CSV'}</button><button onClick={()=>void downloadFile('/datasets/template','fraudmesh_template.csv').catch((e)=>toast.error(errorMessage(e)))}>CSV template</button><button onClick={()=>void downloadFile(`/transactions/export?offset=${page*50}${risk==='ALL'?'':`&risk=${risk}`}&search=${encodeURIComponent(search)}`,'fraudmesh_transactions.csv').catch((e)=>toast.error(errorMessage(e)))}>Export up to 500 matches</button><input ref={input} hidden type="file" accept=".csv" onChange={(e)=>{const file=e.target.files?.[0];if(file)upload.mutate(file);e.target.value=''}}/></div>
    {showForm&&<Panel className="metadata-panel"><PanelTitle>Submit and score a transaction</PanelTitle><form onSubmit={(e)=>{e.preventDefault();create.mutate(e.currentTarget)}}><div className="metadata-grid">{[['external_id','External ID (optional)'],['account_id','Account'],['merchant_id','Merchant ID'],['merchant_name','Merchant name'],['device_id','Device'],['ip_address','IP address'],['location','Location']].map(([key,label])=><label key={key}>{label}<input name={key} required={key!=='external_id'} maxLength={key==='merchant_name'?120:80}/></label>)}<label>Amount<input name="amount" type="number" min="0.01" max="10000000" step="0.01" required/></label><label>Currency<input name="currency" defaultValue="USD" required pattern="[A-Za-z]{3}" maxLength={3}/></label><label>Occurred at (optional)<input name="occurred_at" type="datetime-local"/></label></div><button className="button-primary" disabled={create.isPending}>{create.isPending?'Scoring…':'Score transaction'}</button></form></Panel>}
    {importReport&&<Panel><PanelTitle>Import results</PanelTitle><p>{importReport.imported} saved · {importReport.duplicates} already present · {importReport.failed_count} rejected</p>{importReport.failed.map((row)=><p key={row.row}>Row {row.row}: {row.error}</p>)}</Panel>}
    {sim?.error&&<ErrorState message={sim.error}/>}
    <Panel className="monitor-panel">
      <div className="monitor-toolbar"><div className="simulation-control"><button className="start-sim" disabled={simulation.isPending||sim?.state==='RUNNING'} onClick={() => simulation.mutate('start')}><Play/> Start simulation</button><button aria-label="Pause simulation" disabled={simulation.isPending||sim?.state!=='RUNNING'} onClick={() => simulation.mutate('pause')}><Pause/></button><button aria-label="Stop simulation" disabled={simulation.isPending||sim?.state==='STOPPED'} onClick={() => simulation.mutate('stop')}><Square/></button><label>Speed<select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value={1}>1 event/sec</option><option value={5}>5 events/sec</option><option value={10}>10 events/sec</option></select><ChevronDown/></label></div><div className="feed-controls"><label className="search-field"><Search/><input value={search} onChange={(event) => {setSearch(event.target.value);setPage(0)}} placeholder="Search feed"/></label><label className="filter-select"><Filter/><select value={risk} onChange={(event) => {setRisk(event.target.value);setPage(0)}}><option>ALL</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label></div></div>
      <div className="feed-meta"><span><i/> LIVE INGESTION</span><b>{filtered.length} events in current view</b><small>Source is shown per event. Simulation stops automatically after 500 events.</small></div>
      {filtered.length ? <div className="table-scroll"><table className="data-table transaction-table"><thead><tr><th>Transaction</th><th>Timestamp</th><th>Account</th><th>Merchant</th><th>Amount</th><th>Device</th><th>IP address</th><th>Location</th><th>Risk</th><th>Status</th></tr></thead><tbody><AnimatePresence initial={false}>{filtered.map((item,index)=><motion.tr layout key={item.id} initial={index < 3 ? { opacity: 0, y: -12, backgroundColor: '#7d55ff2a' } : false} animate={{ opacity: 1, y: 0, backgroundColor: 'transparent' }} onClick={() => navigate(`/app/transactions/${item.id}`)}><td><b>{item.external_id}</b><small>{item.source}</small></td><td className="mono">{when(item.occurred_at)}</td><td className="mono">{item.account_id}</td><td>{item.merchant_name}</td><td><b>{money(item.amount,item.currency)}</b></td><td className="mono">{item.device_id}</td><td className="mono">{item.ip_address}</td><td>{item.location}</td><td><span className={`table-score score-${item.risk_level.toLowerCase()}`}>{Math.round(item.risk_score*100)}</span></td><td><RiskBadge level={item.risk_level}/></td></motion.tr>)}</AnimatePresence></tbody></table></div> : <EmptyState title="No events match this view" text="Change the filters or start Simulation Mode to generate a clearly labelled transaction stream."/>}
    </Panel>
    <div className="list-toolbar"><button disabled={page===0} onClick={()=>setPage(page-1)}>Previous</button><span>Page {page+1}</span><button disabled={data.length<50} onClick={()=>setPage(page+1)}>Next</button></div>
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
    <div className="detail-grid"><Panel className="metadata-panel"><PanelTitle>Transaction metadata</PanelTitle><div className="metadata-grid">{[['Account',transaction.account_id],['Customer',transaction.customer_id||'Not supplied'],['Merchant',transaction.merchant_name],['Merchant ID',transaction.merchant_id],['Amount',money(transaction.amount,transaction.currency)],['Device',transaction.device_id],['IP address',transaction.ip_address],['Location',transaction.location],['Status',transaction.status]].map(([label,value])=><div key={label}><span>{label}</span><b>{value}</b></div>)}</div></Panel><Panel className="breakdown-panel"><PanelTitle>Risk contribution</PanelTitle><p>{transaction.evidence?.explanation_method}</p><div className="factor-bars">{factors.map((factor)=><div key={factor.key}><span>{factor.label}</span><i><b style={{width:`${Math.min(100,Math.abs(factor.contribution)*320)}%`}}/></i><strong>{Math.round(factor.contribution*100)}%</strong></div>)}</div></Panel>
      <Panel className="evidence-panel"><PanelTitle>Why was this flagged?</PanelTitle><div className="reason-list">{transaction.evidence?.reasons?.map((reason,index)=><div key={reason}><span>{String(index+1).padStart(2,'0')}</span><p>{reason}</p></div>)}</div><div className="model-stamp"><Activity/><span><b>Prediction recorded</b><small>{transaction.evidence?.prediction_timestamp ? new Date(transaction.evidence.prediction_timestamp).toLocaleString() : 'Current ingestion cycle'}</small></span></div></Panel>
      <Panel className="neighborhood-panel"><PanelTitle aside={<Network/>}>Nearby graph neighborhood</PanelTitle><div className="nearby-graph"><svg viewBox="0 0 500 260"><path d="M250 130L80 50M250 130L420 50M250 130L65 220M250 130L435 215"/></svg><div className="central-node"><CircleDollarSign/><span>{transaction.external_id}</span></div>{graph?.nodes.filter((node)=>node.data.type!=='TRANSACTION').slice(0,4).map((node,index)=><div key={node.data.id} className={`neighbor-node neighbor-${index}`}><Globe2/><span>{node.data.type}</span><small>{node.data.label}</small></div>)}</div></Panel>
    </div>
  </>
}

