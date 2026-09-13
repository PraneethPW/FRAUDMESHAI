import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, Boxes, BrainCircuit, BriefcaseBusiness, CircleGauge, Network, Pause, Play, Radar, ScanSearch, ShieldAlert, Square, Users } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api, errorMessage } from '../lib/api'
import type { DashboardData, GraphResponse } from '../types'
import { ErrorState, GraphLoader, PageIntro, Panel, PanelTitle } from '../components/UI'

const metricConfig = [
  ['transactions_processed','Transactions processed',Activity],['high_risk_transactions','High-risk transactions',ShieldAlert],['active_investigations','Active investigations',BriefcaseBusiness],['suspicious_entities','Suspicious entities',Users],['fraud_clusters','Fraud clusters',Boxes],['alerts_today','Alerts today',AlertTriangle],['average_risk_score','Average risk',CircleGauge],['false_positive_reviews','FP reviews',ScanSearch],
] as const
const colors = ['#65e6c4','#ffba69','#ff7893','#ff315d']

export default function Dashboard() {
  const navigate = useNavigate()
  const client = useQueryClient()
  const { data, isLoading, error } = useQuery<DashboardData>({ queryKey: ['dashboard'], queryFn: () => api.get('/dashboard/overview').then((response) => response.data), refetchInterval: 30000 })
  const {data:graph}=useQuery<GraphResponse>({queryKey:['dashboard-graph'],queryFn:()=>api.get('/graph?limit=20').then((r)=>r.data)})
  const simulation = useMutation({ mutationFn: ({ action, speed = 5 }: { action: string; speed?: number }) => api.post(`/simulation/${action}`, action === 'start' ? { speed } : {}), onSuccess: ({ data: state }) => { toast.success(`Simulation ${state.state.toLowerCase()}`); client.invalidateQueries({ queryKey: ['dashboard'] }) }, onError: (err) => toast.error(errorMessage(err)) })
  if (isLoading) return <GraphLoader label="Calibrating operational graph" />
  if (error || !data) return <ErrorState message={errorMessage(error)} />
  const ids=Array.from(new Set(graph?.edges.flatMap((e)=>[e.data.source,e.data.target])??[])).slice(0,7)
  const nodes=ids.map((id)=>graph?.nodes.find((n)=>n.data.id===id)).filter((n)=>!!n)
  const points=[[45,60],[170,115],[300,45],[365,140],[80,225],[275,230],[210,40]]
  const metricValue = (key: string, value: number | string) => key === 'average_risk_score' ? `${Math.round(Number(value)*100)}%` : typeof value === 'number' ? value.toLocaleString() : value
  return <>
    <PageIntro eyebrow="Operational intelligence" title="Network overview" text="A live view of workspace-scoped transaction, graph, alert, and investigation signals." actions={<div className="simulation-actions"><span>SIMULATION MODE</span><button className="button-primary" onClick={() => simulation.mutate({action:'start'})}><Play/> Start</button><button onClick={() => simulation.mutate({action:'pause'})}><Pause/></button><button onClick={() => simulation.mutate({action:'stop'})}><Square/></button></div>} />
    <div className="metric-grid">{metricConfig.map(([key,label,Icon])=><article key={key} className={key.includes('risk')||key.includes('alerts')?'hot-card':''}><div><Icon/><span>{label}</span></div><b>{metricValue(key,data.metrics[key] ?? 0)}</b><small>{key==='transactions_processed'?'+ live ingestion':key==='average_risk_score'?'across current window':'workspace total'}</small></article>)}</div>
    <div className="dashboard-grid">
      <Panel className="trend-panel"><PanelTitle aside={<span className="live-label"><i/> {data.mode}</span>}>Fraud signal trend</PanelTitle><ResponsiveContainer width="100%" height={280}><AreaChart data={data.trend}><defs><linearGradient id="fraudFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#9a73ff" stopOpacity={.45}/><stop offset="1" stopColor="#9a73ff" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#ffffff0a" vertical={false}/><XAxis dataKey="date" tick={{fill:'#716b7b',fontSize:10}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'#716b7b',fontSize:10}} tickLine={false} axisLine={false}/><Tooltip contentStyle={{background:'#100e18',border:'1px solid #ffffff17',borderRadius:12}}/><Area type="monotone" dataKey="transactions" stroke="#9474ee" fill="url(#fraudFill)" strokeWidth={2}/><Area type="monotone" dataKey="alerts" stroke="#ff5578" fill="none" strokeWidth={2}/></AreaChart></ResponsiveContainer>
      </Panel>
      <Panel className="network-panel"><PanelTitle aside={<button className="text-button" onClick={()=>navigate('/app/graph')}>Open graph →</button>}>Live fraud topology</PanelTitle><div className="dashboard-network"><div className="scan-line"/><svg viewBox="0 0 430 280">{graph?.edges.filter((e)=>ids.includes(e.data.source)&&ids.includes(e.data.target)).map((e)=>{const a=points[ids.indexOf(e.data.source)],b=points[ids.indexOf(e.data.target)];return <path key={e.data.id} d={`M${a[0]} ${a[1]}L${b[0]} ${b[1]}`}/>})}</svg>{nodes.map((node,index)=><i key={node.data.id} className={`dash-node dash-node-${index}`} style={{left:`${points[index][0]/430*100}%`,top:`${points[index][1]/280*100}%`}} title={`${node.data.type}: ${node.data.label}`}/>)}</div><div className="network-meta"><span><b>Graph online</b><small>Temporal edges updating</small></span><strong><Network/> {data.metrics.suspicious_entities} entities</strong></div></Panel>
      <Panel><PanelTitle>Risk distribution</PanelTitle><div className="pie-wrap"><ResponsiveContainer width="100%" height={225}><PieChart><Pie data={data.risk_distribution} dataKey="value" innerRadius={62} outerRadius={88} paddingAngle={3}>{data.risk_distribution.map((entry,index)=><Cell key={entry.name} fill={colors[index]}/>)}</Pie><Tooltip contentStyle={{background:'#100e18',border:'1px solid #ffffff17',borderRadius:12}}/></PieChart></ResponsiveContainer><div className="pie-center"><b>{data.metrics.transactions_processed}</b><span>signals</span></div></div><div className="chart-legend">{data.risk_distribution.map((entry,index)=><span key={entry.name}><i style={{background:colors[index]}}/>{entry.name}<b>{entry.value}</b></span>)}</div></Panel>
      <Panel><PanelTitle>Fraud by hour</PanelTitle><ResponsiveContainer width="100%" height={250}><BarChart data={data.fraud_by_hour}><CartesianGrid stroke="#ffffff08" vertical={false}/><XAxis dataKey="hour" tick={{fill:'#716b7b',fontSize:9}} interval={3} axisLine={false} tickLine={false}/><YAxis hide/><Tooltip contentStyle={{background:'#100e18',border:'1px solid #ffffff17',borderRadius:12}}/><Bar dataKey="count" fill="#7456ce" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></Panel>
      <Panel><PanelTitle>Risky merchants</PanelTitle><div className="rank-list">{data.top_merchants.map((item,index)=><div key={item.name}><span><i>{index+1}</i><b>{item.name}</b><small>{item.volume} transactions</small></span><em>{Math.round(item.risk*100)}</em></div>)}</div></Panel>
      <Panel><PanelTitle aside={<BrainCircuit/>}>Model state</PanelTitle><div className="model-card"><div className="model-orbit"><Radar/><i/></div><h3>{String(data.metrics.model_state).replaceAll('_',' ')}</h3><p>{data.active_model?`${data.active_model.dataset} training · saved model weights`:'Transparent heuristic scoring until a trained model is activated'}</p><div><span><i/> Inference online</span><b>{data.active_model?.run_id.slice(0,8)??'v2.0'}</b></div></div></Panel>
    </div>
  </>
}

