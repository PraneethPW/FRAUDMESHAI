import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, Boxes, BrainCircuit, BriefcaseBusiness, CircleGauge, Network, Pause, Play, Radar, ScanSearch, ShieldAlert, Square, Users } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { toast } from 'sonner'
import { api, errorMessage } from '../lib/api'
import type { DashboardData } from '../types'
import { ErrorState, GraphLoader, PageIntro, Panel, PanelTitle } from '../components/UI'

const metricConfig = [
  ['transactions_processed','Transactions processed',Activity],['high_risk_transactions','High-risk transactions',ShieldAlert],['active_investigations','Active investigations',BriefcaseBusiness],['suspicious_entities','Suspicious entities',Users],['fraud_clusters','Fraud clusters',Boxes],['alerts_today','Alerts today',AlertTriangle],['average_risk_score','Average risk',CircleGauge],['false_positive_reviews','FP reviews',ScanSearch],
] as const
const colors = ['#65e6c4','#ffba69','#ff7893','#ff315d']

export default function Dashboard() {
  const client = useQueryClient()
  const { data, isLoading, error } = useQuery<DashboardData>({ queryKey: ['dashboard'], queryFn: () => api.get('/dashboard/overview').then((response) => response.data), refetchInterval: 5000 })
  const simulation = useMutation({ mutationFn: ({ action, speed = 5 }: { action: string; speed?: number }) => api.post(`/simulation/${action}`, action === 'start' ? { speed } : {}), onSuccess: ({ data: state }) => { toast.success(`Simulation ${state.state.toLowerCase()}`); client.invalidateQueries({ queryKey: ['dashboard'] }) }, onError: (err) => toast.error(errorMessage(err)) })
  if (isLoading) return <GraphLoader label="Calibrating operational graph" />
  if (error || !data) return <ErrorState message={errorMessage(error)} />
  const metricValue = (key: string, value: number | string) => key === 'average_risk_score' ? `${Math.round(Number(value)*100)}%` : typeof value === 'number' ? value.toLocaleString() : value
  return <>
    <PageIntro eyebrow="Operational intelligence" title="Network overview" text="A live view of workspace-scoped transaction, graph, alert, and investigation signals." actions={<div className="simulation-actions"><span>SIMULATION MODE</span><button className="button-primary" onClick={() => simulation.mutate({action:'start'})}><Play/> Start</button><button onClick={() => simulation.mutate({action:'pause'})}><Pause/></button><button onClick={() => simulation.mutate({action:'stop'})}><Square/></button></div>} />
    <div className="metric-grid">{metricConfig.map(([key,label,Icon])=><article key={key} className={key.includes('risk')||key.includes('alerts')?'hot-card':''}><div><Icon/><span>{label}</span></div><b>{metricValue(key,data.metrics[key] ?? 0)}</b><small>{key==='transactions_processed'?'+ live ingestion':key==='average_risk_score'?'across current window':'workspace total'}</small></article>)}</div>
    <div className="dashboard-grid">
      <Panel className="trend-panel"><PanelTitle aside={<span className="live-label"><i/> LIVE DATA</span>}>Fraud signal trend</PanelTitle><ResponsiveContainer width="100%" height={280}><AreaChart data={data.trend}><defs><linearGradient id="fraudFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#9a73ff" stopOpacity={.45}/><stop offset="1" stopColor="#9a73ff" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#ffffff0a" vertical={false}/><XAxis dataKey="date" tick={{fill:'#716b7b',fontSize:10}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'#716b7b',fontSize:10}} tickLine={false} axisLine={false}/><Tooltip contentStyle={{background:'#100e18',border:'1px solid #ffffff17',borderRadius:12}}/><Area type="monotone" dataKey="transactions" stroke="#9474ee" fill="url(#fraudFill)" strokeWidth={2}/><Area type="monotone" dataKey="alerts" stroke="#ff5578" fill="none" strokeWidth={2}/></AreaChart></ResponsiveContainer>
      </Panel>
      <Panel className="network-panel"><PanelTitle aside={<button className="text-button">Open graph →</button>}>Live fraud topology</PanelTitle><div className="dashboard-network"><div className="scan-line"/><svg viewBox="0 0 430 280"><path d="M45 60L170 115L300 45M170 115L365 140M170 115L80 225M170 115L275 230M80 225L275 230M365 140L275 230"/></svg>{[0,1,2,3,4,5,6].map((node)=><i key={node} className={`dash-node dash-node-${node}`}/>)}</div><div className="network-meta"><span><b>Graph online</b><small>Temporal edges updating</small></span><strong><Network/> {data.metrics.suspicious_entities} entities</strong></div></Panel>
      <Panel><PanelTitle>Risk distribution</PanelTitle><div className="pie-wrap"><ResponsiveContainer width="100%" height={225}><PieChart><Pie data={data.risk_distribution} dataKey="value" innerRadius={62} outerRadius={88} paddingAngle={3}>{data.risk_distribution.map((entry,index)=><Cell key={entry.name} fill={colors[index]}/>)}</Pie><Tooltip contentStyle={{background:'#100e18',border:'1px solid #ffffff17',borderRadius:12}}/></PieChart></ResponsiveContainer><div className="pie-center"><b>{data.metrics.transactions_processed}</b><span>signals</span></div></div><div className="chart-legend">{data.risk_distribution.map((entry,index)=><span key={entry.name}><i style={{background:colors[index]}}/>{entry.name}<b>{entry.value}</b></span>)}</div></Panel>
      <Panel><PanelTitle>Fraud by hour</PanelTitle><ResponsiveContainer width="100%" height={250}><BarChart data={data.fraud_by_hour}><CartesianGrid stroke="#ffffff08" vertical={false}/><XAxis dataKey="hour" tick={{fill:'#716b7b',fontSize:9}} interval={3} axisLine={false} tickLine={false}/><YAxis hide/><Tooltip contentStyle={{background:'#100e18',border:'1px solid #ffffff17',borderRadius:12}}/><Bar dataKey="count" fill="#7456ce" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></Panel>
      <Panel><PanelTitle>Risky merchants</PanelTitle><div className="rank-list">{data.top_merchants.map((item,index)=><div key={item.name}><span><i>{index+1}</i><b>{item.name}</b><small>{item.volume} transactions</small></span><em>{Math.round(item.risk*100)}</em></div>)}</div></Panel>
      <Panel><PanelTitle aside={<BrainCircuit/>}>Model state</PanelTitle><div className="model-card"><div className="model-orbit"><Radar/><i/></div><h3>Temporal Graph Ensemble</h3><p>Time-aware graph features + rolling temporal aggregation</p><div><span><i/> Inference online</span><b>v1.0.0-demo</b></div></div></Panel>
    </div>
  </>
}

